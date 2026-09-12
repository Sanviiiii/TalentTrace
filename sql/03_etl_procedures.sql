-- ============================================================
-- FILE: 03_etl_procedures.sql
-- PURPOSE: ETL logic to move data from OLTP → OLAP
--
-- Contains:
--   1. Populate Dim_Date (one-time calendar fill)
--   2. ETL: OLTP → Dim_Department
--   3. ETL: OLTP → Dim_Project
--   4. ETL: Historical CSV → Dim_Employee (with SCD Type 2)
--   5. ETL: OLTP Reviews → Fact_PerformanceReviews
--   6. Analytical queries using CTEs + Window Functions
-- ============================================================

USE hr_olap;

-- ─────────────────────────────────────────────────────────────
-- PROCEDURE 1: Populate Dim_Date
-- Fills every date from 2015-01-01 to 2030-12-31.
-- Run once. Never needs to run again.
-- ─────────────────────────────────────────────────────────────
DROP PROCEDURE IF EXISTS sp_populate_dim_date;

DELIMITER $$
CREATE PROCEDURE sp_populate_dim_date()
BEGIN
    DECLARE v_date DATE DEFAULT '2015-01-01';
    DECLARE v_end  DATE DEFAULT '2030-12-31';

    WHILE v_date <= v_end DO
        INSERT IGNORE INTO Dim_Date (
            date_key, full_date, day_of_week, day_name,
            day_of_month, day_of_year, week_of_year,
            month_number, month_name, quarter, year,
            is_weekend
        )
        VALUES (
            DATE_FORMAT(v_date, '%Y%m%d'),
            v_date,
            DAYOFWEEK(v_date),
            DAYNAME(v_date),
            DAY(v_date),
            DAYOFYEAR(v_date),
            WEEK(v_date, 3),
            MONTH(v_date),
            MONTHNAME(v_date),
            QUARTER(v_date),
            YEAR(v_date),
            CASE WHEN DAYOFWEEK(v_date) IN (1,7) THEN TRUE ELSE FALSE END
        );
        SET v_date = DATE_ADD(v_date, INTERVAL 1 DAY);
    END WHILE;

    SELECT CONCAT('Dim_Date populated: ', COUNT(*), ' rows') AS status
    FROM Dim_Date;
END$$
DELIMITER ;

-- ─────────────────────────────────────────────────────────────
-- PROCEDURE 2: ETL → Dim_Department
-- Copies departments from OLTP, skips existing ones.
-- ─────────────────────────────────────────────────────────────
DROP PROCEDURE IF EXISTS sp_load_dim_department;

DELIMITER $$
CREATE PROCEDURE sp_load_dim_department()
BEGIN
    INSERT INTO hr_olap.Dim_Department (department_id, department_name, location)
    SELECT
        d.department_id,
        d.department_name,
        d.location
    FROM hr_oltp.Departments d
    WHERE NOT EXISTS (
        SELECT 1
        FROM hr_olap.Dim_Department dd
        WHERE dd.department_id = d.department_id
    );

    SELECT CONCAT('Dim_Department: ', ROW_COUNT(), ' new rows inserted') AS status;
END$$
DELIMITER ;

-- ─────────────────────────────────────────────────────────────
-- PROCEDURE 3: ETL → Dim_Project
-- ─────────────────────────────────────────────────────────────
DROP PROCEDURE IF EXISTS sp_load_dim_project;

DELIMITER $$
CREATE PROCEDURE sp_load_dim_project()
BEGIN
    INSERT INTO hr_olap.Dim_Project (
        project_id, project_name, status, start_date, end_date, budget, dept_key
    )
    SELECT
        p.project_id,
        p.project_name,
        p.status,
        p.start_date,
        p.end_date,
        p.budget,
        dd.dept_key
    FROM hr_oltp.Projects p
    LEFT JOIN hr_olap.Dim_Department dd
        ON p.department_id = dd.department_id
    WHERE NOT EXISTS (
        SELECT 1
        FROM hr_olap.Dim_Project dp
        WHERE dp.project_id = p.project_id
    );

    SELECT CONCAT('Dim_Project: ', ROW_COUNT(), ' new rows inserted') AS status;
END$$
DELIMITER ;

-- ─────────────────────────────────────────────────────────────
-- PROCEDURE 4: SCD Type 2 — Load / Update Dim_Employee
--
-- Logic:
--   CASE A — New employee (never seen before):
--     → INSERT new row, is_current=1, start_date=today, end_date=NULL
--
--   CASE B — Existing employee, key attributes changed
--             (dept or monthly_income changed by >5%):
--     → UPDATE old row: set end_date=today, is_current=0
--     → INSERT new row: is_current=1, start_date=today
--
--   CASE C — Existing employee, nothing changed:
--     → Do nothing
-- ─────────────────────────────────────────────────────────────
DROP PROCEDURE IF EXISTS sp_scd2_load_dim_employee;

DELIMITER $$
CREATE PROCEDURE sp_scd2_load_dim_employee()
BEGIN
    DECLARE done        INT DEFAULT FALSE;
    DECLARE v_emp_id    INT;
    DECLARE v_dept      VARCHAR(100);
    DECLARE v_income    DECIMAL(10,2);
    DECLARE v_role      VARCHAR(100);
    DECLARE v_level     INT;
    DECLARE v_fname     VARCHAR(100);
    DECLARE v_lname     VARCHAR(100);
    DECLARE v_email     VARCHAR(150);
    DECLARE v_gender    VARCHAR(10);
    DECLARE v_age       INT;
    DECLARE v_edu       INT;
    DECLARE v_edu_field VARCHAR(100);
    DECLARE v_marital   VARCHAR(20);
    DECLARE v_travel    VARCHAR(50);
    DECLARE v_overtime  VARCHAR(5);
    DECLARE v_attrition VARCHAR(5);
    DECLARE v_stock     INT;
    DECLARE v_workyrs   INT;
    DECLARE v_comyrs    INT;
    DECLARE v_hike      INT;
    DECLARE v_perfrating INT;
    DECLARE v_envsatisf INT;
    DECLARE v_jobsatisf INT;

    -- Cursor over the current OLTP employee snapshot
    DECLARE emp_cursor CURSOR FOR
        SELECT
            e.employee_id,
            d.department_name,
            e.monthly_income,
            e.job_role,
            e.job_level,
            e.first_name,
            e.last_name,
            e.email,
            e.gender,
            e.age,
            e.education,
            e.education_field,
            e.marital_status,
            e.business_travel,
            e.over_time,
            e.attrition,
            e.stock_option_level,
            e.total_working_years,
            e.years_at_company,
            e.percent_salary_hike,
            0,  -- performance_rating (will come from reviews)
            0,  -- environment_satisfaction
            0   -- job_satisfaction
        FROM hr_oltp.Employees e
        JOIN hr_oltp.Departments d ON e.department_id = d.department_id;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    OPEN emp_cursor;

    read_loop: LOOP
        FETCH emp_cursor INTO
            v_emp_id, v_dept, v_income, v_role, v_level,
            v_fname, v_lname, v_email, v_gender, v_age,
            v_edu, v_edu_field, v_marital, v_travel,
            v_overtime, v_attrition, v_stock, v_workyrs,
            v_comyrs, v_hike, v_perfrating, v_envsatisf, v_jobsatisf;

        IF done THEN LEAVE read_loop; END IF;

        -- Check if a current record already exists
        IF NOT EXISTS (
            SELECT 1 FROM hr_olap.Dim_Employee
            WHERE employee_id = v_emp_id AND is_current = 1
        ) THEN
            -- CASE A: Brand new employee → INSERT
            INSERT INTO hr_olap.Dim_Employee (
                employee_id, first_name, last_name, email, gender, age,
                education, education_field, marital_status, department_name,
                job_role, job_level, monthly_income, business_travel,
                over_time, attrition, stock_option_level, total_working_years,
                years_at_company, percent_salary_hike, performance_rating,
                environment_satisfaction, job_satisfaction,
                start_date, end_date, is_current
            )
            VALUES (
                v_emp_id, v_fname, v_lname, v_email, v_gender, v_age,
                v_edu, v_edu_field, v_marital, v_dept,
                v_role, v_level, v_income, v_travel,
                v_overtime, v_attrition, v_stock, v_workyrs,
                v_comyrs, v_hike, v_perfrating,
                v_envsatisf, v_jobsatisf,
                CURDATE(), NULL, 1
            );

        ELSE
            -- Check if key attributes changed (dept or income changed >5%)
            IF EXISTS (
                SELECT 1 FROM hr_olap.Dim_Employee
                WHERE employee_id  = v_emp_id
                  AND is_current   = 1
                  AND (
                      department_name <> v_dept
                      OR ABS(monthly_income - v_income) / monthly_income > 0.05
                  )
            ) THEN
                -- CASE B: Attribute changed → close old record
                UPDATE hr_olap.Dim_Employee
                SET end_date   = CURDATE(),
                    is_current = 0
                WHERE employee_id = v_emp_id
                  AND is_current  = 1;

                -- Open new version
                INSERT INTO hr_olap.Dim_Employee (
                    employee_id, first_name, last_name, email, gender, age,
                    education, education_field, marital_status, department_name,
                    job_role, job_level, monthly_income, business_travel,
                    over_time, attrition, stock_option_level, total_working_years,
                    years_at_company, percent_salary_hike, performance_rating,
                    environment_satisfaction, job_satisfaction,
                    start_date, end_date, is_current
                )
                VALUES (
                    v_emp_id, v_fname, v_lname, v_email, v_gender, v_age,
                    v_edu, v_edu_field, v_marital, v_dept,
                    v_role, v_level, v_income, v_travel,
                    v_overtime, v_attrition, v_stock, v_workyrs,
                    v_comyrs, v_hike, v_perfrating,
                    v_envsatisf, v_jobsatisf,
                    CURDATE(), NULL, 1
                );
            END IF;
            -- CASE C: No changes → do nothing
        END IF;

    END LOOP;

    CLOSE emp_cursor;

    SELECT CONCAT('Dim_Employee SCD2 sync complete. Current records: ',
        (SELECT COUNT(*) FROM hr_olap.Dim_Employee WHERE is_current=1)) AS status;
END$$
DELIMITER ;

-- ─────────────────────────────────────────────────────────────
-- PROCEDURE 5: ETL → Fact_PerformanceReviews
-- Loads review records from OLTP, joins to dim surrogate keys
-- ─────────────────────────────────────────────────────────────
DROP PROCEDURE IF EXISTS sp_load_fact_reviews;

DELIMITER $$
CREATE PROCEDURE sp_load_fact_reviews()
BEGIN
    INSERT INTO hr_olap.Fact_PerformanceReviews (
        surrogate_key, dept_key, date_key,
        employee_id, review_id,
        performance_rating, job_satisfaction,
        environment_satisfaction, relationship_satisfaction,
        work_life_balance, job_involvement,
        monthly_income_at_review, percent_salary_hike,
        years_at_company, training_times_last_year,
        review_year, review_quarter, attrition_flag
    )
    SELECT
        de.surrogate_key,
        dd.dept_key,
        DATE_FORMAT(pr.review_date, '%Y%m%d') AS date_key,
        pr.employee_id,
        pr.review_id,
        pr.performance_rating,
        pr.job_satisfaction,
        pr.environment_satisfaction,
        pr.relationship_satisfaction,
        pr.work_life_balance,
        pr.job_involvement,
        e.monthly_income,
        e.percent_salary_hike,
        e.years_at_company,
        e.training_times_last_year,
        pr.review_year,
        pr.review_quarter,
        CASE WHEN e.attrition = 'Yes' THEN 1 ELSE 0 END
    FROM hr_oltp.Performance_Reviews pr
    JOIN hr_oltp.Employees e
        ON pr.employee_id = e.employee_id
    JOIN hr_oltp.Departments d
        ON e.department_id = d.department_id
    JOIN hr_olap.Dim_Employee de
        ON pr.employee_id = de.employee_id AND de.is_current = 1
    JOIN hr_olap.Dim_Department dd
        ON d.department_id = dd.department_id
    -- Skip already-loaded reviews
    WHERE pr.review_id NOT IN (
        SELECT DISTINCT review_id FROM hr_olap.Fact_PerformanceReviews
        WHERE review_id IS NOT NULL
    );

    SELECT CONCAT('Fact_PerformanceReviews: ', ROW_COUNT(), ' new rows inserted') AS status;
END$$
DELIMITER ;

-- ─────────────────────────────────────────────────────────────
-- RUN ALL ETL IN ORDER:
-- ─────────────────────────────────────────────────────────────
-- CALL sp_populate_dim_date();
-- CALL sp_load_dim_department();
-- CALL sp_load_dim_project();
-- CALL sp_scd2_load_dim_employee();
-- CALL sp_load_fact_reviews();

SELECT 'ETL procedures created successfully! Uncomment the CALL statements above to run.' AS next_step;

CALL sp_populate_dim_date()