-- ============================================================
-- FILE: 01_oltp_ddl.sql
-- PURPOSE: Create the OLTP (operational) schema
--          This is the live, normalized database the app
--          reads and writes to daily.
-- RUN THIS FIRST in MySQL Workbench.
-- ============================================================

-- Create and select the OLTP database
CREATE DATABASE IF NOT EXISTS hr_oltp;
USE hr_oltp;

-- ────────────────────────────────────────────────────────────
-- TABLE 1: Departments
-- Master list of all departments in the company
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Departments (
    department_id   INT             AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(100)    NOT NULL UNIQUE,
    location        VARCHAR(100)    DEFAULT 'HQ',
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP
);

-- ────────────────────────────────────────────────────────────
-- TABLE 2: Employees
-- Core employee table. One row per employee (current state).
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Employees (
    employee_id             INT             AUTO_INCREMENT PRIMARY KEY,
    first_name              VARCHAR(100)    NOT NULL CHECK (first_name REGEXP '^[A-Za-z]+$'),
    last_name               VARCHAR(100)    NOT NULL CHECK (last_name REGEXP '^[A-Za-z]+$'),
    email                   VARCHAR(150)    NOT NULL UNIQUE,
    phone                   VARCHAR(20),
    gender                  ENUM('Male','Female','Other'),
    age                     INT             CHECK (age BETWEEN 18 AND 100),
    date_of_birth           DATE,
    hire_date               DATE            NOT NULL,
    department_id           INT             NOT NULL,
    job_role                VARCHAR(100)    NOT NULL,
    job_level               INT             CHECK (job_level BETWEEN 1 AND 5),
    monthly_income          DECIMAL(10,2)   NOT NULL,
    education               INT             CHECK (education BETWEEN 1 AND 5),
    education_field         VARCHAR(100),
    marital_status          ENUM('Single','Married','Divorced'),
    business_travel         ENUM('Non-Travel','Travel_Rarely','Travel_Frequently'),
    distance_from_home      INT,
    attrition               ENUM('Yes','No') DEFAULT 'No',
    over_time               ENUM('Yes','No') DEFAULT 'No',
    stock_option_level      INT             DEFAULT 0,
    total_working_years     INT             DEFAULT 0,
    num_companies_worked    INT             DEFAULT 0,
    percent_salary_hike     INT             DEFAULT 0,
    training_times_last_year INT            DEFAULT 0,
    years_at_company        INT             DEFAULT 0,
    years_in_current_role   INT             DEFAULT 0,
    years_since_last_promo  INT             DEFAULT 0,
    years_with_curr_manager INT             DEFAULT 0,
    is_active               BOOLEAN         DEFAULT TRUE,
    created_at              DATETIME        DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME        DEFAULT CURRENT_TIMESTAMP
                                            ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES Departments(department_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- ────────────────────────────────────────────────────────────
-- TABLE 3: Projects
-- All company projects, past and present
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Projects (
    project_id      INT             AUTO_INCREMENT PRIMARY KEY,
    project_name    VARCHAR(200)    NOT NULL,
    department_id   INT,
    start_date      DATE            NOT NULL,
    end_date        DATE,
    status          ENUM('Planning','Active','On Hold','Completed','Cancelled')
                                    DEFAULT 'Planning',
    budget          DECIMAL(15,2),
    description     TEXT,
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES Departments(department_id)
        ON DELETE SET NULL
);

-- ────────────────────────────────────────────────────────────
-- TABLE 4: Project_Assignments
-- Which employee is assigned to which project (M:N bridge)
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Project_Assignments (
    assignment_id   INT             AUTO_INCREMENT PRIMARY KEY,
    employee_id     INT             NOT NULL,
    project_id      INT             NOT NULL,
    role_in_project VARCHAR(100)    DEFAULT 'Contributor',
    assigned_date   DATE            NOT NULL,
    released_date   DATE,
    hours_allocated INT             DEFAULT 0,

    FOREIGN KEY (employee_id)
        REFERENCES Employees(employee_id)
        ON DELETE CASCADE,
    FOREIGN KEY (project_id)
        REFERENCES Projects(project_id)
        ON DELETE CASCADE,

    -- An employee can only have one active role per project
    UNIQUE KEY uq_emp_project (employee_id, project_id)
);

-- ────────────────────────────────────────────────────────────
-- TABLE 5: Performance_Reviews
-- Annual/quarterly reviews submitted by managers
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Performance_Reviews (
    review_id               INT             AUTO_INCREMENT PRIMARY KEY,
    employee_id             INT             NOT NULL,
    reviewer_id             INT,                        -- manager's employee_id
    review_date             DATE            NOT NULL,
    review_year             INT             NOT NULL,
    review_quarter          INT             CHECK (review_quarter BETWEEN 1 AND 4),
    performance_rating      INT             NOT NULL
                                            CHECK (performance_rating BETWEEN 1 AND 4),
    job_satisfaction        INT             CHECK (job_satisfaction BETWEEN 1 AND 4),
    environment_satisfaction INT            CHECK (environment_satisfaction BETWEEN 1 AND 4),
    relationship_satisfaction INT           CHECK (relationship_satisfaction BETWEEN 1 AND 4),
    work_life_balance       INT             CHECK (work_life_balance BETWEEN 1 AND 4),
    job_involvement         INT             CHECK (job_involvement BETWEEN 1 AND 4),
    comments                TEXT,
    created_at              DATETIME        DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES Employees(employee_id)
        ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id)
        REFERENCES Employees(employee_id)
        ON DELETE SET NULL
);

-- ────────────────────────────────────────────────────────────
-- TABLE 6: Salary_History
-- Tracks every salary change for audit trail
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Salary_History (
    history_id      INT             AUTO_INCREMENT PRIMARY KEY,
    employee_id     INT             NOT NULL,
    old_salary      DECIMAL(10,2)   NOT NULL,
    new_salary      DECIMAL(10,2)   NOT NULL,
    change_date     DATE            NOT NULL,
    change_reason   VARCHAR(200),
    changed_by      INT,            -- manager employee_id

    FOREIGN KEY (employee_id)
        REFERENCES Employees(employee_id)
        ON DELETE CASCADE
);

-- ────────────────────────────────────────────────────────────
-- INDEXES (for query performance on large datasets)
-- ────────────────────────────────────────────────────────────
CREATE INDEX idx_emp_dept     ON Employees(department_id);
CREATE INDEX idx_emp_active   ON Employees(is_active);
CREATE INDEX idx_emp_attrition ON Employees(attrition);
CREATE INDEX idx_review_emp   ON Performance_Reviews(employee_id);
CREATE INDEX idx_review_year  ON Performance_Reviews(review_year);
CREATE INDEX idx_assign_emp   ON Project_Assignments(employee_id);
CREATE INDEX idx_assign_proj  ON Project_Assignments(project_id);

-- ────────────────────────────────────────────────────────────
-- SEED: Insert base departments
-- ────────────────────────────────────────────────────────────
INSERT INTO Departments (department_name, location) VALUES
    ('Sales',                   'New York'),
    ('Research & Development',  'San Francisco'),
    ('Human Resources',         'Chicago');

SELECT 'hr_oltp schema created successfully!' AS status;
 use hr_oltp;
 show tables;
 
 select * from Employees
 limit 5;
 
 CALL sp_populate_dim_date();
 
 -- Alter table
 -- 1. Drop the violating rows
DELETE FROM Employees 
WHERE first_name REGEXP '[0-9]' 
   OR last_name REGEXP '[0-9]';

-- 2. Add the constraints
-- Drop the violating rows
DELETE FROM Employees
WHERE first_name REGEXP '[0-9]'OR last_name REGEXP '[0-9]';

ALTER TABLE Employees
ADD CONSTRAINT chk_first_name_letters
CHECK (first_name REGEXP '^[A-Za-z]+$'),
ADD CONSTRAINT chk_last_name_letters
CHECK (last_name REGEXP '^[A-Za-z]+$');