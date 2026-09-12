-- ============================================================
-- FILE: 04_analytical_queries.sql
-- PURPOSE: Advanced SQL queries used by the Streamlit dashboards.
--          All queries use CTEs and/or Window Functions.
-- ============================================================

USE hr_olap;

-- ─────────────────────────────────────────────────────────────
-- QUERY 1: Year-over-Year Average Performance per Department
-- Uses: CTE + GROUP BY + year comparison
-- Dashboard: Line chart — YoY Performance Trends
-- ─────────────────────────────────────────────────────────────
WITH yearly_avg AS (
    SELECT
        f.review_year,
        d.department_name,
        ROUND(AVG(f.performance_rating), 2)     AS avg_rating,
        ROUND(AVG(f.job_satisfaction), 2)        AS avg_job_satisfaction,
        ROUND(AVG(f.work_life_balance), 2)       AS avg_wlb,
        COUNT(DISTINCT f.employee_id)            AS employee_count
    FROM Fact_PerformanceReviews f
    JOIN Dim_Department d ON f.dept_key = d.dept_key
    GROUP BY f.review_year, d.department_name
)
SELECT
    review_year,
    department_name,
    avg_rating,
    avg_job_satisfaction,
    avg_wlb,
    employee_count,
    -- Compare to previous year
    LAG(avg_rating) OVER (
        PARTITION BY department_name ORDER BY review_year
    ) AS prev_year_rating,
    ROUND(avg_rating - LAG(avg_rating) OVER (
        PARTITION BY department_name ORDER BY review_year
    ), 2) AS rating_change
FROM yearly_avg
ORDER BY review_year, department_name;


-- ─────────────────────────────────────────────────────────────
-- QUERY 2: Top 10 Performers per Department (Current Year)
-- Uses: DENSE_RANK() Window Function
-- Dashboard: Leaderboard / Bar chart
-- ─────────────────────────────────────────────────────────────
WITH ranked_employees AS (
    SELECT
        de.employee_id,
        CONCAT(de.first_name, ' ', de.last_name)    AS full_name,
        de.department_name,
        de.job_role,
        de.job_level,
        de.monthly_income,
        ROUND(AVG(f.performance_rating), 2)          AS avg_rating,
        COUNT(f.fact_id)                             AS total_reviews,
        DENSE_RANK() OVER (
            PARTITION BY de.department_name
            ORDER BY AVG(f.performance_rating) DESC,
                     de.monthly_income DESC
        ) AS dept_rank
    FROM Fact_PerformanceReviews f
    JOIN Dim_Employee de
        ON f.surrogate_key = de.surrogate_key AND de.is_current = 1
    WHERE f.review_year = YEAR(CURDATE())
    GROUP BY
        de.employee_id, de.first_name, de.last_name,
        de.department_name, de.job_role, de.job_level, de.monthly_income
)
SELECT *
FROM ranked_employees
WHERE dept_rank <= 10
ORDER BY department_name, dept_rank;


-- ─────────────────────────────────────────────────────────────
-- QUERY 3: Attrition Risk Analysis
-- Employees with LOW satisfaction + HIGH overtime = risk
-- Uses: CTE + CASE scoring + NTILE window function
-- Dashboard: Attrition risk heatmap
-- ─────────────────────────────────────────────────────────────
WITH risk_scores AS (
    SELECT
        de.employee_id,
        CONCAT(de.first_name, ' ', de.last_name)    AS full_name,
        de.department_name,
        de.job_role,
        de.monthly_income,
        de.over_time,
        de.years_at_company,
        ROUND(AVG(f.job_satisfaction), 2)            AS avg_job_satisfaction,
        ROUND(AVG(f.work_life_balance), 2)           AS avg_wlb,
        ROUND(AVG(f.environment_satisfaction), 2)    AS avg_env_satisfaction,
        -- Risk score: lower satisfaction + overtime = higher risk
        (
            (5 - ROUND(AVG(f.job_satisfaction), 0))         -- 1=satisfied→low risk
          + (5 - ROUND(AVG(f.work_life_balance), 0))
          + (5 - ROUND(AVG(f.environment_satisfaction), 0))
          + CASE WHEN de.over_time = 'Yes' THEN 3 ELSE 0 END
          + CASE WHEN de.years_at_company < 2 THEN 2 ELSE 0 END
        ) AS risk_score
    FROM Fact_PerformanceReviews f
    JOIN Dim_Employee de
        ON f.surrogate_key = de.surrogate_key AND de.is_current = 1
    WHERE de.attrition = 'No'   -- only look at employees still here
    GROUP BY
        de.employee_id, de.first_name, de.last_name,
        de.department_name, de.job_role, de.monthly_income,
        de.over_time, de.years_at_company
),
risk_buckets AS (
    SELECT *,
        NTILE(4) OVER (ORDER BY risk_score DESC) AS risk_quartile
        -- 1 = highest risk, 4 = lowest risk
    FROM risk_scores
)
SELECT
    employee_id, full_name, department_name, job_role,
    monthly_income, over_time, years_at_company,
    avg_job_satisfaction, avg_wlb, avg_env_satisfaction,
    risk_score,
    CASE risk_quartile
        WHEN 1 THEN 'High Risk'
        WHEN 2 THEN 'Medium Risk'
        WHEN 3 THEN 'Low Risk'
        WHEN 4 THEN 'Very Low Risk'
    END AS risk_category
FROM risk_buckets
ORDER BY risk_score DESC;


-- ─────────────────────────────────────────────────────────────
-- QUERY 4: Department-level KPI Summary
-- Uses: Multi-level CTE
-- Dashboard: KPI cards at top of dashboard
-- ─────────────────────────────────────────────────────────────
WITH dept_metrics AS (
    SELECT
        d.department_name,
        COUNT(DISTINCT de.employee_id)              AS headcount,
        ROUND(AVG(de.monthly_income), 2)            AS avg_salary,
        ROUND(AVG(f.performance_rating), 2)         AS avg_performance,
        SUM(f.attrition_flag)                       AS attrition_count,
        COUNT(f.fact_id)                            AS total_reviews
    FROM Fact_PerformanceReviews f
    JOIN Dim_Employee de ON f.surrogate_key = de.surrogate_key AND de.is_current = 1
    JOIN Dim_Department d ON f.dept_key = d.dept_key
    GROUP BY d.department_name
),
overall AS (
    SELECT
        'Company Total'                             AS department_name,
        SUM(headcount)                              AS headcount,
        ROUND(AVG(avg_salary), 2)                   AS avg_salary,
        ROUND(AVG(avg_performance), 2)              AS avg_performance,
        SUM(attrition_count)                        AS attrition_count,
        SUM(total_reviews)                          AS total_reviews
    FROM dept_metrics
)
SELECT *, ROUND(attrition_count * 100.0 / NULLIF(headcount, 0), 2) AS attrition_rate_pct
FROM dept_metrics
UNION ALL
SELECT *, ROUND(attrition_count * 100.0 / NULLIF(headcount, 0), 2)
FROM overall
ORDER BY headcount DESC;


-- ─────────────────────────────────────────────────────────────
-- QUERY 5: Employee SCD History — view all versions of an employee
-- Uses: Self-join on Dim_Employee
-- Used when HR clicks on an employee to see their career history
-- ─────────────────────────────────────────────────────────────
-- Replace 1001 with the actual employee_id from the UI:
SELECT
    surrogate_key,
    employee_id,
    department_name,
    job_role,
    job_level,
    monthly_income,
    start_date,
    COALESCE(end_date, 'Present')   AS end_date,
    is_current,
    DATEDIFF(
        COALESCE(end_date, CURDATE()),
        start_date
    ) AS days_in_role
FROM Dim_Employee
WHERE employee_id = 1001
ORDER BY start_date ASC;


-- ─────────────────────────────────────────────────────────────
-- QUERY 6: Salary Percentile by Department
-- Uses: PERCENT_RANK() Window Function
-- Dashboard: Salary distribution visual
-- ─────────────────────────────────────────────────────────────
SELECT
    employee_id,
    department_name,
    job_role,
    monthly_income,
    ROUND(PERCENT_RANK() OVER (
        PARTITION BY department_name
        ORDER BY monthly_income
    ) * 100, 1) AS salary_percentile,
    ROUND(AVG(monthly_income) OVER (
        PARTITION BY department_name
    ), 2) AS dept_avg_salary
FROM Dim_Employee
WHERE is_current = 1
ORDER BY department_name, monthly_income DESC;
