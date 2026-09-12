-- ============================================================
-- FILE: 02_olap_ddl.sql
-- PURPOSE: Create the OLAP Data Warehouse (Star Schema)
--          Used ONLY for analytics and dashboards.
--          Never written to directly by the app — only
--          populated via ETL from hr_oltp.
-- RUN THIS SECOND in MySQL Workbench.
-- ============================================================

CREATE DATABASE IF NOT EXISTS hr_olap;
USE hr_olap;

-- ────────────────────────────────────────────────────────────
-- DIM TABLE 1: Dim_Date
-- Pre-populated calendar table — every query joins to this.
-- Allows filtering by year, quarter, month, weekday etc.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Dim_Date (
    date_key        INT             PRIMARY KEY,   -- format: YYYYMMDD  e.g. 20240115
    full_date       DATE            NOT NULL,
    day_of_week     INT,                           -- 1=Mon … 7=Sun
    day_name        VARCHAR(10),
    day_of_month    INT,
    day_of_year     INT,
    week_of_year    INT,
    month_number    INT,
    month_name      VARCHAR(10),
    quarter         INT,                           -- 1-4
    year            INT,
    is_weekend      BOOLEAN         DEFAULT FALSE,
    is_holiday      BOOLEAN         DEFAULT FALSE
);

-- ────────────────────────────────────────────────────────────
-- DIM TABLE 2: Dim_Department
-- Conformed dimension — one row per department
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Dim_Department (
    dept_key        INT             AUTO_INCREMENT PRIMARY KEY,  -- surrogate key
    department_id   INT             NOT NULL,                    -- natural key from OLTP
    department_name VARCHAR(100)    NOT NULL,
    location        VARCHAR(100),
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP
);

-- ────────────────────────────────────────────────────────────
-- DIM TABLE 3: Dim_Project
-- One row per project
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Dim_Project (
    project_key     INT             AUTO_INCREMENT PRIMARY KEY,  -- surrogate key
    project_id      INT             NOT NULL,                    -- natural key from OLTP
    project_name    VARCHAR(200)    NOT NULL,
    status          VARCHAR(50),
    start_date      DATE,
    end_date        DATE,
    budget          DECIMAL(15,2),
    dept_key        INT,

    FOREIGN KEY (dept_key)
        REFERENCES Dim_Department(dept_key)
        ON DELETE SET NULL
);

-- ────────────────────────────────────────────────────────────
-- DIM TABLE 4: Dim_Employee  ← SCD TYPE 2
--
-- This is the most important dimension table.
-- Each row is a VERSION of an employee's attributes.
-- When an employee changes department or gets a salary bump,
-- a NEW row is inserted (old row's end_date is closed).
--
-- SCD Type 2 Columns:
--   surrogate_key  → unique ID for this specific version
--   employee_id    → natural key (same across all versions)
--   start_date     → when this version became active
--   end_date       → when this version was replaced (NULL = still active)
--   is_current     → 1 = this is the live record, 0 = historical
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Dim_Employee (
    surrogate_key           INT             AUTO_INCREMENT PRIMARY KEY,
    employee_id             INT             NOT NULL,       -- natural key

    -- Employee attributes (captured at THIS version)
    first_name              VARCHAR(100),
    last_name               VARCHAR(100),
    email                   VARCHAR(150),
    gender                  VARCHAR(10),
    age                     INT,
    education               INT,
    education_field         VARCHAR(100),
    marital_status          VARCHAR(20),
    department_name         VARCHAR(100),
    job_role                VARCHAR(100),
    job_level               INT,
    monthly_income          DECIMAL(10,2),
    business_travel         VARCHAR(50),
    over_time               VARCHAR(5),
    attrition               VARCHAR(5),
    stock_option_level      INT,
    total_working_years     INT,
    years_at_company        INT,
    percent_salary_hike     INT,
    performance_rating      INT,
    environment_satisfaction INT,
    job_satisfaction        INT,

    -- SCD Type 2 tracking columns
    start_date              DATE            NOT NULL,
    end_date                DATE,                          -- NULL means currently active
    is_current              TINYINT(1)      DEFAULT 1,

    -- Indexes for fast SCD lookups
    INDEX idx_emp_id        (employee_id),
    INDEX idx_is_current    (is_current),
    INDEX idx_start_date    (start_date)
);

-- ────────────────────────────────────────────────────────────
-- FACT TABLE: Fact_PerformanceReviews
--
-- Central fact table. One row per performance review event.
-- All foreign keys are SURROGATE keys from dimension tables.
-- Stores measurable metrics (scores, ratings, income at time).
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Fact_PerformanceReviews (
    fact_id                     INT             AUTO_INCREMENT PRIMARY KEY,

    -- Foreign keys to dimension tables (surrogate keys)
    surrogate_key               INT             NOT NULL,   -- → Dim_Employee
    dept_key                    INT,                        -- → Dim_Department
    project_key                 INT,                        -- → Dim_Project
    date_key                    INT,                        -- → Dim_Date

    -- Natural keys for traceability
    employee_id                 INT             NOT NULL,
    review_id                   INT,

    -- Measures (the numbers we aggregate in dashboards)
    performance_rating          INT,
    job_satisfaction            INT,
    environment_satisfaction    INT,
    relationship_satisfaction   INT,
    work_life_balance           INT,
    job_involvement             INT,
    monthly_income_at_review    DECIMAL(10,2),
    percent_salary_hike         INT,
    years_at_company            INT,
    training_times_last_year    INT,

    -- Degenerate dimensions (useful attributes, no separate dim needed)
    review_year                 INT,
    review_quarter              INT,
    attrition_flag              TINYINT(1)      DEFAULT 0,  -- 1 = left company

    created_at                  DATETIME        DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    FOREIGN KEY (surrogate_key)
        REFERENCES Dim_Employee(surrogate_key)
        ON DELETE RESTRICT,
    FOREIGN KEY (dept_key)
        REFERENCES Dim_Department(dept_key)
        ON DELETE SET NULL,
    FOREIGN KEY (project_key)
        REFERENCES Dim_Project(project_key)
        ON DELETE SET NULL,
    FOREIGN KEY (date_key)
        REFERENCES Dim_Date(date_key)
        ON DELETE SET NULL,

    -- Indexes for analytical queries
    INDEX idx_fact_emp          (employee_id),
    INDEX idx_fact_dept         (dept_key),
    INDEX idx_fact_year         (review_year),
    INDEX idx_fact_rating       (performance_rating),
    INDEX idx_fact_attrition    (attrition_flag)
);

SELECT 'hr_olap schema created successfully!' AS status;

 use hr_olap;
 show tables;