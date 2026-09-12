"""
managers.py
───────────
Data Access Layer (DAL) — all database operations live here.

Classes:
  BaseManager         → shared DB access, inherited by all managers
  DepartmentManager   → CRUD for departments
  EmployeeManager     → CRUD for employees + SCD Type 2 trigger
  ProjectManager      → CRUD for projects + assignments
  ReviewManager       → submit and fetch performance reviews
  AnalyticsManager    → read-only OLAP queries for dashboards

Pattern:
  Streamlit page  →  Manager method  →  db_manager query  →  MySQL
"""

from datetime import date, datetime
from backend.db_manager import DatabaseConnection
from backend.models import (
    Department, Employee, Project,
    Review, ProjectAssignment
)


# ══════════════════════════════════════════════════════════════
# BASE MANAGER — shared by all managers
# ══════════════════════════════════════════════════════════════
class BaseManager:
    """
    All Manager classes inherit from this.
    Provides self.db (the singleton connection) and
    self.use_oltp() / self.use_olap() to switch schemas.
    """

    def __init__(self):
        self.db = DatabaseConnection()
        if not self.db.is_alive():
            self.db.connect("hr_oltp")   # default to OLTP

    def use_oltp(self):
        self.db.use_database("hr_oltp")

    def use_olap(self):
        self.db.use_database("hr_olap")


# ══════════════════════════════════════════════════════════════
# DEPARTMENT MANAGER
# ══════════════════════════════════════════════════════════════
class DepartmentManager(BaseManager):

    def get_all(self) -> list[dict]:
        """Fetch all departments."""
        self.use_oltp()
        return self.db.fetch_all(
            "SELECT department_id, department_name, location FROM Departments ORDER BY department_name"
        )

    def get_by_id(self, dept_id: int) -> dict | None:
        self.use_oltp()
        return self.db.fetch_one(
            "SELECT * FROM Departments WHERE department_id = %s", (dept_id,)
        )

    def add(self, dept: Department) -> int:
        """Insert a new department. Returns new department_id."""
        errors = dept.validate()
        if errors:
            raise ValueError(f"Validation failed: {errors}")

        self.use_oltp()
        return self.db.execute(
            "INSERT INTO Departments (department_name, location) VALUES (%s, %s)",
            (dept.department_name, dept.location)
        )


# ══════════════════════════════════════════════════════════════
# EMPLOYEE MANAGER
# ══════════════════════════════════════════════════════════════
class EmployeeManager(BaseManager):

    # ── Read ──────────────────────────────────────────────────
    def get_all(self, active_only: bool = True) -> list[dict]:
        self.use_oltp()
        query = """
            SELECT
                e.employee_id, e.first_name, e.last_name,
                CONCAT(e.first_name, ' ', e.last_name) AS full_name,
                e.email, e.gender, e.age,
                d.department_name, e.job_role, e.job_level,
                e.monthly_income, e.attrition,
                e.over_time, e.years_at_company, e.hire_date,
                e.is_active
            FROM Employees e
            JOIN Departments d ON e.department_id = d.department_id
        """
        if active_only:
            query += " WHERE e.is_active = TRUE"
        query += " ORDER BY e.last_name, e.first_name"
        return self.db.fetch_all(query)

    def get_by_id(self, emp_id: int) -> dict | None:
        self.use_oltp()
        return self.db.fetch_one("""
            SELECT
                e.*, d.department_name
            FROM Employees e
            JOIN Departments d ON e.department_id = d.department_id
            WHERE e.employee_id = %s
        """, (emp_id,))

    def search(self, keyword: str) -> list[dict]:
        """Search by name, email, or job role."""
        self.use_oltp()
        like = f"%{keyword}%"
        return self.db.fetch_all("""
            SELECT
                e.employee_id,
                CONCAT(e.first_name, ' ', e.last_name) AS full_name,
                e.email, e.job_role, d.department_name,
                e.monthly_income, e.attrition
            FROM Employees e
            JOIN Departments d ON e.department_id = d.department_id
            WHERE e.first_name  LIKE %s
               OR e.last_name   LIKE %s
               OR e.email       LIKE %s
               OR e.job_role    LIKE %s
        """, (like, like, like, like))

    # ── Create ────────────────────────────────────────────────
    def add(self, emp: Employee) -> int:
        """
        Insert a new employee into OLTP.
        Also inserts the first SCD Type 2 record in OLAP.
        Returns new employee_id.
        """
        errors = emp.validate()
        if errors:
            raise ValueError(f"Validation failed: {errors}")

        self.use_oltp()

        # Check for duplicate email
        existing = self.db.fetch_one(
            "SELECT employee_id FROM Employees WHERE email = %s", (emp.email,)
        )
        if existing:
            raise ValueError(f"Email '{emp.email}' already exists.")

        emp_id = self.db.execute("""
            INSERT INTO Employees (
                first_name, last_name, email, phone, gender, age,
                hire_date, department_id, job_role, job_level,
                monthly_income, education, education_field,
                marital_status, business_travel, distance_from_home,
                attrition, over_time, stock_option_level,
                total_working_years, num_companies_worked,
                percent_salary_hike, training_times_last_year,
                years_at_company, years_in_current_role,
                years_since_last_promo, years_with_curr_manager
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s
            )
        """, (
            emp.first_name, emp.last_name, emp.email, emp.phone,
            emp.gender, emp.age, emp.hire_date, emp.department_id,
            emp.job_role, emp.job_level, emp.monthly_income,
            emp.education, emp.education_field, emp.marital_status,
            emp.business_travel, emp.distance_from_home, emp.attrition,
            emp.over_time, emp.stock_option_level, emp.total_working_years,
            emp.num_companies_worked, emp.percent_salary_hike,
            emp.training_times_last_year, emp.years_at_company,
            emp.years_in_current_role, emp.years_since_last_promo,
            emp.years_with_curr_manager
        ))

        # ── Trigger SCD Type 2: first version in OLAP ─────────
        self._scd2_insert(emp_id, emp)
        return emp_id

    # ── Update Department (triggers SCD Type 2) ───────────────
    def update_department(self, emp_id: int, new_dept_id: int, reason: str = "") -> bool:
        """
        Changes an employee's department.
        ① Updates OLTP record.
        ② Closes old Dim_Employee row in OLAP (end_date = today, is_current = 0).
        ③ Opens new Dim_Employee row in OLAP (is_current = 1).
        """
        self.use_oltp()

        # Get current state before updating
        old = self.get_by_id(emp_id)
        if not old:
            raise ValueError(f"Employee {emp_id} not found.")

        # Update OLTP
        self.db.execute(
            "UPDATE Employees SET department_id = %s, updated_at = NOW() WHERE employee_id = %s",
            (new_dept_id, emp_id)
        )

        # Get new dept name for OLAP
        dept = DepartmentManager().get_by_id(new_dept_id)
        new_dept_name = dept["department_name"] if dept else ""

        # ── SCD Type 2: close old, open new ──────────────────
        self._scd2_close_current(emp_id)
        self._scd2_open_new(emp_id, new_dept_name, old)

        print(f"[SCD2] Employee {emp_id}: dept changed → '{new_dept_name}'")
        return True

    # ── Update Salary (triggers SCD Type 2) ──────────────────
    def update_salary(self, emp_id: int, new_salary: float, reason: str = "") -> bool:
        """
        Updates salary. Logs to Salary_History.
        Triggers SCD Type 2 if change > 5%.
        """
        self.use_oltp()

        old = self.get_by_id(emp_id)
        if not old:
            raise ValueError(f"Employee {emp_id} not found.")

        old_salary = float(old["monthly_income"])
        change_pct = abs(new_salary - old_salary) / old_salary

        # Update OLTP
        self.db.execute(
            "UPDATE Employees SET monthly_income = %s, updated_at = NOW() WHERE employee_id = %s",
            (new_salary, emp_id)
        )

        # Log to salary history
        self.db.execute("""
            INSERT INTO Salary_History (employee_id, old_salary, new_salary, change_date, change_reason)
            VALUES (%s, %s, %s, %s, %s)
        """, (emp_id, old_salary, new_salary, date.today(), reason))

        # Trigger SCD2 only if salary changed more than 5%
        if change_pct > 0.05:
            self._scd2_close_current(emp_id)
            old["monthly_income"] = new_salary
            dept_name = old.get("department_name", "")
            self._scd2_open_new(emp_id, dept_name, old)
            print(f"[SCD2] Employee {emp_id}: salary changed {change_pct:.1%} → SCD2 triggered")

        return True

    # ── Deactivate (soft delete) ──────────────────────────────
    def deactivate(self, emp_id: int) -> bool:
        self.use_oltp()
        self.db.execute(
            "UPDATE Employees SET is_active = FALSE, attrition = 'Yes', updated_at = NOW() "
            "WHERE employee_id = %s",
            (emp_id,)
        )
        return True

    # ── SCD Type 2 helpers (private) ──────────────────────────
    def _scd2_insert(self, emp_id: int, emp: Employee):
        """First-time insert into Dim_Employee (new employee)."""
        dept = DepartmentManager().get_by_id(emp.department_id)
        dept_name = dept["department_name"] if dept else ""

        self.use_olap()
        self.db.execute("""
            INSERT INTO Dim_Employee (
                employee_id, first_name, last_name, email, gender, age,
                education, education_field, marital_status, department_name,
                job_role, job_level, monthly_income, business_travel,
                over_time, attrition, stock_option_level,
                total_working_years, years_at_company,
                start_date, end_date, is_current
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, NULL, 1
            )
        """, (
            emp_id, emp.first_name, emp.last_name, emp.email,
            emp.gender, emp.age, emp.education, emp.education_field,
            emp.marital_status, dept_name, emp.job_role, emp.job_level,
            emp.monthly_income, emp.business_travel, emp.over_time,
            emp.attrition, emp.stock_option_level, emp.total_working_years,
            emp.years_at_company, date.today()
        ))
        self.use_oltp()

    def _scd2_close_current(self, emp_id: int):
        """Close the current OLAP row for this employee."""
        self.use_olap()
        self.db.execute("""
            UPDATE Dim_Employee
            SET end_date = %s, is_current = 0
            WHERE employee_id = %s AND is_current = 1
        """, (date.today(), emp_id))
        self.use_oltp()

    def _scd2_open_new(self, emp_id: int, dept_name: str, emp_data: dict):
        """Open a fresh OLAP row with updated attributes."""
        self.use_olap()
        self.db.execute("""
            INSERT INTO Dim_Employee (
                employee_id, first_name, last_name, email, gender, age,
                education, education_field, marital_status, department_name,
                job_role, job_level, monthly_income, business_travel,
                over_time, attrition, stock_option_level,
                total_working_years, years_at_company,
                start_date, end_date, is_current
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, NULL, 1
            )
        """, (
            emp_id,
            emp_data.get("first_name"), emp_data.get("last_name"),
            emp_data.get("email"),      emp_data.get("gender"),
            emp_data.get("age"),        emp_data.get("education"),
            emp_data.get("education_field"), emp_data.get("marital_status"),
            dept_name,
            emp_data.get("job_role"),   emp_data.get("job_level"),
            emp_data.get("monthly_income"), emp_data.get("business_travel"),
            emp_data.get("over_time"),  emp_data.get("attrition"),
            emp_data.get("stock_option_level", 0),
            emp_data.get("total_working_years", 0),
            emp_data.get("years_at_company", 0),
            date.today()
        ))
        self.use_oltp()


# ══════════════════════════════════════════════════════════════
# PROJECT MANAGER
# ══════════════════════════════════════════════════════════════
class ProjectManager(BaseManager):

    def get_all(self) -> list[dict]:
        self.use_oltp()
        return self.db.fetch_all("""
            SELECT p.*, d.department_name
            FROM Projects p
            LEFT JOIN Departments d ON p.department_id = d.department_id
            ORDER BY p.start_date DESC
        """)

    def get_by_id(self, project_id: int) -> dict | None:
        self.use_oltp()
        return self.db.fetch_one(
            "SELECT * FROM Projects WHERE project_id = %s", (project_id,)
        )

    def add(self, project: Project) -> int:
        errors = project.validate()
        if errors:
            raise ValueError(f"Validation failed: {errors}")

        self.use_oltp()
        return self.db.execute("""
            INSERT INTO Projects (project_name, department_id, start_date,
                                  end_date, status, budget, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            project.project_name, project.department_id,
            project.start_date, project.end_date,
            project.status, project.budget, project.description
        ))

    def update_status(self, project_id: int, new_status: str) -> bool:
        if new_status not in Project.VALID_STATUSES:
            raise ValueError(f"Invalid status: {new_status}")
        self.use_oltp()
        self.db.execute(
            "UPDATE Projects SET status = %s WHERE project_id = %s",
            (new_status, project_id)
        )
        return True

    def assign_employee(self, assignment: ProjectAssignment) -> int:
        errors = assignment.validate()
        if errors:
            raise ValueError(f"Validation failed: {errors}")

        self.use_oltp()
        return self.db.execute("""
            INSERT INTO Project_Assignments
                (employee_id, project_id, role_in_project, assigned_date, hours_allocated)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                role_in_project = VALUES(role_in_project),
                hours_allocated = VALUES(hours_allocated)
        """, (
            assignment.employee_id, assignment.project_id,
            assignment.role_in_project, assignment.assigned_date,
            assignment.hours_allocated
        ))

    def get_assignments(self, project_id: int) -> list[dict]:
        self.use_oltp()
        return self.db.fetch_all("""
            SELECT
                pa.*,
                CONCAT(e.first_name, ' ', e.last_name) AS employee_name,
                e.job_role, d.department_name
            FROM Project_Assignments pa
            JOIN Employees e  ON pa.employee_id  = e.employee_id
            JOIN Departments d ON e.department_id = d.department_id
            WHERE pa.project_id = %s
        """, (project_id,))


# ══════════════════════════════════════════════════════════════
# REVIEW MANAGER
# ══════════════════════════════════════════════════════════════
class ReviewManager(BaseManager):

    def submit(self, review: Review) -> int:
        errors = review.validate()
        if errors:
            raise ValueError(f"Validation failed: {errors}")

        self.use_oltp()
        review_id = self.db.execute("""
            INSERT INTO Performance_Reviews (
                employee_id, reviewer_id, review_date, review_year,
                review_quarter, performance_rating, job_satisfaction,
                environment_satisfaction, relationship_satisfaction,
                work_life_balance, job_involvement, comments
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            review.employee_id, review.reviewer_id, review.review_date,
            review.review_year, review.review_quarter,
            review.performance_rating, review.job_satisfaction,
            review.environment_satisfaction, review.relationship_satisfaction,
            review.work_life_balance, review.job_involvement, review.comments
        ))
        return review_id

    def get_by_employee(self, emp_id: int) -> list[dict]:
        self.use_oltp()
        return self.db.fetch_all("""
            SELECT
                pr.*,
                CONCAT(r.first_name, ' ', r.last_name) AS reviewer_name
            FROM Performance_Reviews pr
            LEFT JOIN Employees r ON pr.reviewer_id = r.employee_id
            WHERE pr.employee_id = %s
            ORDER BY pr.review_date DESC
        """, (emp_id,))

    def get_by_year(self, year: int) -> list[dict]:
        self.use_oltp()
        return self.db.fetch_all(
            "SELECT * FROM Performance_Reviews WHERE review_year = %s ORDER BY review_date DESC",
            (year,)
        )


# ══════════════════════════════════════════════════════════════
# ANALYTICS MANAGER  (reads from OLAP only)
# ══════════════════════════════════════════════════════════════
class AnalyticsManager(BaseManager):

    def get_yoy_performance(self) -> list[dict]:
        """Year-over-year avg performance per department."""
        self.use_olap()
        return self.db.fetch_all("""
            WITH yearly AS (
                SELECT
                    f.review_year,
                    d.department_name,
                    ROUND(AVG(f.performance_rating), 2)  AS avg_rating,
                    ROUND(AVG(f.job_satisfaction), 2)     AS avg_satisfaction,
                    COUNT(DISTINCT f.employee_id)         AS employee_count
                FROM Fact_PerformanceReviews f
                JOIN Dim_Department d ON f.dept_key = d.dept_key
                GROUP BY f.review_year, d.department_name
            )
            SELECT *,
                LAG(avg_rating) OVER (
                    PARTITION BY department_name ORDER BY review_year
                ) AS prev_year_rating
            FROM yearly
            ORDER BY review_year, department_name
        """)

    def get_top_performers(self, year: int = None, limit: int = 10) -> list[dict]:
        """Top performers per department using DENSE_RANK."""
        self.use_olap()
        year_filter = f"AND f.review_year = {year}" if year else ""
        return self.db.fetch_all(f"""
            WITH ranked AS (
                SELECT
                    de.employee_id,
                    CONCAT(de.first_name, ' ', de.last_name) AS full_name,
                    de.department_name,
                    de.job_role,
                    de.job_level,
                    de.monthly_income,
                    ROUND(AVG(f.performance_rating), 2)       AS avg_rating,
                    COUNT(f.fact_id)                          AS total_reviews,
                    DENSE_RANK() OVER (
                        PARTITION BY de.department_name
                        ORDER BY AVG(f.performance_rating) DESC
                    ) AS dept_rank
                FROM Fact_PerformanceReviews f
                JOIN Dim_Employee de
                    ON f.surrogate_key = de.surrogate_key AND de.is_current = 1
                {year_filter}
                GROUP BY
                    de.employee_id, de.first_name, de.last_name,
                    de.department_name, de.job_role, de.job_level, de.monthly_income
            )
            SELECT * FROM ranked
            WHERE dept_rank <= {limit}
            ORDER BY department_name, dept_rank
        """)

    def get_attrition_risk(self) -> list[dict]:
        """Risk-scored employees using NTILE."""
        self.use_olap()
        return self.db.fetch_all("""
            WITH scores AS (
                SELECT
                    de.employee_id,
                    CONCAT(de.first_name, ' ', de.last_name) AS full_name,
                    de.department_name, de.job_role,
                    de.monthly_income, de.over_time,
                    de.years_at_company,
                    ROUND(AVG(f.job_satisfaction), 2)          AS avg_satisfaction,
                    ROUND(AVG(f.work_life_balance), 2)         AS avg_wlb,
                    (
                        (5 - ROUND(AVG(f.job_satisfaction), 0))
                      + (5 - ROUND(AVG(f.work_life_balance), 0))
                      + (5 - ROUND(AVG(f.environment_satisfaction), 0))
                      + CASE WHEN de.over_time = 'Yes' THEN 3 ELSE 0 END
                      + CASE WHEN de.years_at_company < 2 THEN 2 ELSE 0 END
                    ) AS risk_score
                FROM Fact_PerformanceReviews f
                JOIN Dim_Employee de
                    ON f.surrogate_key = de.surrogate_key AND de.is_current = 1
                WHERE de.attrition = 'No'
                GROUP BY
                    de.employee_id, de.first_name, de.last_name,
                    de.department_name, de.job_role, de.monthly_income,
                    de.over_time, de.years_at_company
            )
            SELECT *,
                NTILE(4) OVER (ORDER BY risk_score DESC) AS risk_quartile
            FROM scores
            ORDER BY risk_score DESC
        """)

    def get_department_kpis(self) -> list[dict]:
        """High-level KPI summary per department."""
        self.use_olap()
        return self.db.fetch_all("""
            SELECT
                d.department_name,
                COUNT(DISTINCT f.employee_id)           AS headcount,
                ROUND(AVG(de.monthly_income), 2)        AS avg_salary,
                ROUND(AVG(f.performance_rating), 2)     AS avg_performance,
                SUM(f.attrition_flag)                   AS attrition_count,
                ROUND(SUM(f.attrition_flag) * 100.0
                    / NULLIF(COUNT(DISTINCT f.employee_id), 0), 2) AS attrition_rate
            FROM Fact_PerformanceReviews f
            JOIN Dim_Employee de ON f.surrogate_key = de.surrogate_key AND de.is_current = 1
            JOIN Dim_Department d ON f.dept_key = d.dept_key
            GROUP BY d.department_name
            ORDER BY headcount DESC
        """)

    def get_employee_history(self, emp_id: int) -> list[dict]:
        """Full SCD Type 2 history for one employee."""
        self.use_olap()
        return self.db.fetch_all("""
            SELECT
                surrogate_key, employee_id, department_name,
                job_role, job_level, monthly_income,
                start_date,
                COALESCE(CAST(end_date AS CHAR), 'Present') AS end_date,
                is_current,
                DATEDIFF(COALESCE(end_date, CURDATE()), start_date) AS days_in_role
            FROM Dim_Employee
            WHERE employee_id = %s
            ORDER BY start_date ASC
        """, (emp_id,))

    def get_salary_distribution(self) -> list[dict]:
        """Salary percentile by department."""
        self.use_olap()
        return self.db.fetch_all("""
            SELECT
                employee_id, department_name, job_role, monthly_income,
                ROUND(PERCENT_RANK() OVER (
                    PARTITION BY department_name
                    ORDER BY monthly_income
                ) * 100, 1) AS salary_percentile,
                ROUND(AVG(monthly_income) OVER (
                    PARTITION BY department_name
                ), 2) AS dept_avg_salary
            FROM Dim_Employee
            WHERE is_current = 1
            ORDER BY department_name, monthly_income DESC
        """)
