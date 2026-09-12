"""
models.py
─────────
Pure data classes (entities). No database calls here.
These represent the real-world objects in the system.

Each class:
  - Stores attributes for one entity
  - Has a __repr__ for easy debugging
  - Has a to_dict() for passing data to Streamlit / pandas
  - Has a validate() to catch bad data before it hits MySQL
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


# ══════════════════════════════════════════════════════════════
# DEPARTMENT
# ══════════════════════════════════════════════════════════════
@dataclass
class Department:
    department_name : str
    location        : str          = "HQ"
    department_id   : Optional[int] = None
    created_at      : Optional[datetime] = None

    def validate(self):
        errors = []
        if not self.department_name or len(self.department_name.strip()) == 0:
            errors.append("Department name cannot be empty.")
        if len(self.department_name) > 100:
            errors.append("Department name too long (max 100 chars).")
        return errors

    def to_dict(self) -> dict:
        return {
            "department_id"  : self.department_id,
            "department_name": self.department_name,
            "location"       : self.location,
        }

    def __repr__(self):
        return f"Department(id={self.department_id}, name='{self.department_name}')"


# ══════════════════════════════════════════════════════════════
# EMPLOYEE
# ══════════════════════════════════════════════════════════════
@dataclass
class Employee:
    first_name              : str
    last_name               : str
    email                   : str
    hire_date               : date
    department_id           : int
    job_role                : str
    monthly_income          : float
    job_level               : int              = 1
    gender                  : str              = "Male"
    age                     : int              = 25
    education               : int              = 3
    education_field         : str              = "Other"
    marital_status          : str              = "Single"
    business_travel         : str              = "Travel_Rarely"
    distance_from_home      : int              = 5
    attrition               : str              = "No"
    over_time               : str              = "No"
    stock_option_level      : int              = 0
    total_working_years     : int              = 0
    num_companies_worked    : int              = 0
    percent_salary_hike     : int              = 11
    training_times_last_year: int              = 2
    years_at_company        : int              = 0
    years_in_current_role   : int              = 0
    years_since_last_promo  : int              = 0
    years_with_curr_manager : int              = 0
    phone                   : str              = ""
    is_active               : bool             = True
    employee_id             : Optional[int]    = None
    created_at              : Optional[datetime] = None

    # ── Computed properties ───────────────────────────────────
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def annual_income(self) -> float:
        return self.monthly_income * 12

    # ── Validation ────────────────────────────────────────────
    def validate(self) -> list[str]:
        errors = []
        if not self.first_name or not self.last_name:
            errors.append("First and last name are required.")
        if "@" not in self.email or "." not in self.email:
            errors.append("Invalid email address.")
        if not (18 <= self.age <= 100):
            errors.append("Age must be between 18 and 100.")
        if not (1 <= self.job_level <= 5):
            errors.append("Job level must be 1–5.")
        if self.monthly_income <= 0:
            errors.append("Monthly income must be positive.")
        if self.gender not in ("Male", "Female", "Other"):
            errors.append("Gender must be Male, Female, or Other.")
        if self.attrition not in ("Yes", "No"):
            errors.append("Attrition must be Yes or No.")
        if self.marital_status not in ("Single", "Married", "Divorced"):
            errors.append("Invalid marital status.")
        if self.business_travel not in ("Non-Travel", "Travel_Rarely", "Travel_Frequently"):
            errors.append("Invalid business travel value.")
        return errors

    # ── Serialization ─────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "employee_id"           : self.employee_id,
            "first_name"            : self.first_name,
            "last_name"             : self.last_name,
            "full_name"             : self.full_name,
            "email"                 : self.email,
            "phone"                 : self.phone,
            "gender"                : self.gender,
            "age"                   : self.age,
            "hire_date"             : str(self.hire_date),
            "department_id"         : self.department_id,
            "job_role"              : self.job_role,
            "job_level"             : self.job_level,
            "monthly_income"        : self.monthly_income,
            "annual_income"         : self.annual_income,
            "education"             : self.education,
            "education_field"       : self.education_field,
            "marital_status"        : self.marital_status,
            "business_travel"       : self.business_travel,
            "attrition"             : self.attrition,
            "over_time"             : self.over_time,
            "years_at_company"      : self.years_at_company,
            "is_active"             : self.is_active,
        }

    def __repr__(self):
        return (f"Employee(id={self.employee_id}, name='{self.full_name}', "
                f"dept={self.department_id}, role='{self.job_role}')")


# ══════════════════════════════════════════════════════════════
# PROJECT
# ══════════════════════════════════════════════════════════════
@dataclass
class Project:
    project_name    : str
    department_id   : int
    start_date      : date
    status          : str              = "Planning"
    end_date        : Optional[date]   = None
    budget          : Optional[float]  = None
    description     : str              = ""
    project_id      : Optional[int]    = None
    created_at      : Optional[datetime] = None

    VALID_STATUSES = ("Planning", "Active", "On Hold", "Completed", "Cancelled")

    @property
    def is_active(self) -> bool:
        return self.status == "Active"

    @property
    def duration_days(self) -> Optional[int]:
        if self.end_date:
            return (self.end_date - self.start_date).days
        return None

    def validate(self) -> list[str]:
        errors = []
        if not self.project_name:
            errors.append("Project name is required.")
        if self.status not in self.VALID_STATUSES:
            errors.append(f"Status must be one of: {self.VALID_STATUSES}")
        if self.end_date and self.end_date < self.start_date:
            errors.append("End date cannot be before start date.")
        if self.budget is not None and self.budget < 0:
            errors.append("Budget cannot be negative.")
        return errors

    def to_dict(self) -> dict:
        return {
            "project_id"   : self.project_id,
            "project_name" : self.project_name,
            "department_id": self.department_id,
            "start_date"   : str(self.start_date),
            "end_date"     : str(self.end_date) if self.end_date else None,
            "status"       : self.status,
            "budget"       : self.budget,
            "description"  : self.description,
        }

    def __repr__(self):
        return f"Project(id={self.project_id}, name='{self.project_name}', status='{self.status}')"


# ══════════════════════════════════════════════════════════════
# PERFORMANCE REVIEW
# ══════════════════════════════════════════════════════════════
@dataclass
class Review:
    employee_id             : int
    review_date             : date
    review_year             : int
    performance_rating      : int
    job_satisfaction        : int       = 3
    environment_satisfaction: int       = 3
    relationship_satisfaction: int      = 3
    work_life_balance       : int       = 3
    job_involvement         : int       = 3
    review_quarter          : int       = 1
    reviewer_id             : Optional[int]  = None
    comments                : str            = ""
    review_id               : Optional[int]  = None
    created_at              : Optional[datetime] = None

    # ── Computed ──────────────────────────────────────────────
    @property
    def overall_score(self) -> float:
        """Average of all satisfaction scores + performance."""
        scores = [
            self.performance_rating,
            self.job_satisfaction,
            self.environment_satisfaction,
            self.relationship_satisfaction,
            self.work_life_balance,
            self.job_involvement,
        ]
        return round(sum(scores) / len(scores), 2)

    @property
    def rating_label(self) -> str:
        mapping = {1: "Poor", 2: "Below Average", 3: "Excellent", 4: "Outstanding"}
        return mapping.get(self.performance_rating, "Unknown")

    # ── Validation ────────────────────────────────────────────
    def validate(self) -> list[str]:
        errors = []
        for field_name, value in [
            ("performance_rating",       self.performance_rating),
            ("job_satisfaction",         self.job_satisfaction),
            ("environment_satisfaction", self.environment_satisfaction),
            ("relationship_satisfaction",self.relationship_satisfaction),
            ("work_life_balance",        self.work_life_balance),
            ("job_involvement",          self.job_involvement),
        ]:
            if not (1 <= value <= 4):
                errors.append(f"{field_name} must be between 1 and 4.")
        if not (1 <= self.review_quarter <= 4):
            errors.append("Quarter must be 1–4.")
        if self.review_year < 2000:
            errors.append("Review year seems invalid.")
        return errors

    def to_dict(self) -> dict:
        return {
            "review_id"              : self.review_id,
            "employee_id"            : self.employee_id,
            "reviewer_id"            : self.reviewer_id,
            "review_date"            : str(self.review_date),
            "review_year"            : self.review_year,
            "review_quarter"         : self.review_quarter,
            "performance_rating"     : self.performance_rating,
            "rating_label"           : self.rating_label,
            "job_satisfaction"       : self.job_satisfaction,
            "environment_satisfaction": self.environment_satisfaction,
            "relationship_satisfaction": self.relationship_satisfaction,
            "work_life_balance"      : self.work_life_balance,
            "job_involvement"        : self.job_involvement,
            "overall_score"          : self.overall_score,
            "comments"               : self.comments,
        }

    def __repr__(self):
        return (f"Review(id={self.review_id}, emp={self.employee_id}, "
                f"year={self.review_year}, rating={self.performance_rating})")


# ══════════════════════════════════════════════════════════════
# PROJECT ASSIGNMENT
# ══════════════════════════════════════════════════════════════
@dataclass
class ProjectAssignment:
    employee_id     : int
    project_id      : int
    assigned_date   : date
    role_in_project : str              = "Contributor"
    hours_allocated : int              = 0
    released_date   : Optional[date]   = None
    assignment_id   : Optional[int]    = None

    def validate(self) -> list[str]:
        errors = []
        if self.hours_allocated < 0:
            errors.append("Hours allocated cannot be negative.")
        if self.released_date and self.released_date < self.assigned_date:
            errors.append("Release date cannot be before assignment date.")
        return errors

    def to_dict(self) -> dict:
        return {
            "assignment_id" : self.assignment_id,
            "employee_id"   : self.employee_id,
            "project_id"    : self.project_id,
            "role_in_project": self.role_in_project,
            "assigned_date" : str(self.assigned_date),
            "released_date" : str(self.released_date) if self.released_date else None,
            "hours_allocated": self.hours_allocated,
        }

    def __repr__(self):
        return (f"Assignment(emp={self.employee_id}, "
                f"project={self.project_id}, role='{self.role_in_project}')")
