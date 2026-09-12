"""
data_loader.py — Bulk-loads synthesized CSVs into MySQL
Run AFTER SQL scripts and synthesizer.py
"""

import pandas as pd
import numpy as np
import random
from datetime import date, timedelta
from backend.db_manager import DatabaseConnection
import os
from dotenv import load_dotenv

load_dotenv()
random.seed(42)
np.random.seed(42)

BATCH_SIZE = 5_000
DATA_DIR   = "data"
SYNTH_FILE = f"{DATA_DIR}/employees_synthesized.csv"
HIST_FILE  = f"{DATA_DIR}/employees_historical.csv"

db = DatabaseConnection()

def log(msg):    print(f"  {msg}")
def header(msg): print(f"\n{'─'*55}\n  {msg}\n{'─'*55}")

def load_employees():
    header("STEP 1: Loading Employees into hr_oltp")
    db.connect("hr_oltp")
    depts    = db.fetch_all("SELECT department_id, department_name FROM Departments")
    dept_map = {d["department_name"]: d["department_id"] for d in depts}

    df = pd.read_csv(SYNTH_FILE)
    df["department_id"]  = df["Department"].map(dept_map).fillna(1).astype(int)
    df["HireDate"]       = pd.to_datetime(df["HireDate"], errors="coerce").dt.date
    df["HireDate"]       = df["HireDate"].fillna(date(2020, 1, 1))
    df["Phone"]          = df["Phone"].astype(str).str[:15]
    df["MonthlyIncome"]  = df["MonthlyIncome"].clip(lower=1000, upper=19999)

    query = """
        INSERT IGNORE INTO Employees (
            first_name,last_name,email,phone,gender,age,
            hire_date,department_id,job_role,job_level,
            monthly_income,education,education_field,
            marital_status,business_travel,distance_from_home,
            attrition,over_time,stock_option_level,
            total_working_years,num_companies_worked,
            percent_salary_hike,training_times_last_year,
            years_at_company,years_in_current_role,
            years_since_last_promo,years_with_curr_manager
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    total = 0
    for i in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[i:i+BATCH_SIZE]
        data  = [(
            str(r["FirstName"])[:100], str(r["LastName"])[:100],
            str(r["Email"])[:150],     str(r["Phone"])[:15],
            str(r["Gender"]),          int(r["Age"]),
            r["HireDate"],             int(r["department_id"]),
            str(r["JobRole"])[:100],   int(r["JobLevel"]),
            float(r["MonthlyIncome"]), int(r["Education"]),
            str(r["EducationField"]),  str(r["MaritalStatus"]),
            str(r["BusinessTravel"]),  int(r["DistanceFromHome"]),
            str(r["Attrition"]),       str(r["OverTime"]),
            int(r["StockOptionLevel"]),int(r["TotalWorkingYears"]),
            int(r["NumCompaniesWorked"]),int(r["PercentSalaryHike"]),
            int(r["TrainingTimesLastYear"]),int(r["YearsAtCompany"]),
            int(r["YearsInCurrentRole"]),int(r["YearsSinceLastPromotion"]),
            int(r["YearsWithCurrManager"])
        ) for _, r in batch.iterrows()]
        total += db.execute_many(query, data)
        log(f"Batch {i//BATCH_SIZE+1}: total {total:,} rows inserted")
    log(f"✅ Employees: {total:,} rows")

def load_reviews():
    header("STEP 2: Generating Performance Reviews")
    db.connect("hr_oltp")
    emp_ids = [e["employee_id"] for e in db.fetch_all("SELECT employee_id FROM Employees LIMIT 20000")]
    query = """
        INSERT IGNORE INTO Performance_Reviews (
            employee_id,review_date,review_year,review_quarter,
            performance_rating,job_satisfaction,environment_satisfaction,
            relationship_satisfaction,work_life_balance,job_involvement
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    rows = []
    for emp_id in emp_ids:
        for year in [2022, 2023, 2024]:
            q = random.randint(1,4)
            rows.append((emp_id, date(year, q*3, random.randint(1,28)), year, q,
                random.choices([3,4],weights=[85,15])[0],
                random.randint(1,4),random.randint(1,4),
                random.randint(1,4),random.randint(1,4),random.randint(1,4)))
    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        total += db.execute_many(query, rows[i:i+BATCH_SIZE])
    log(f"✅ Reviews: {total:,} rows")

def load_projects():
    header("STEP 3: Loading Projects & Assignments")
    db.connect("hr_oltp")
    names    = ["HR Digital Transformation","Sales Analytics Platform","Employee Wellness Initiative",
                "Cloud Migration Phase 1","Data Warehouse Build","Performance Management System",
                "Recruitment Automation","Learning Management Portal","Payroll Modernisation",
                "Diversity & Inclusion Program"]
    dept_ids = [d["department_id"] for d in db.fetch_all("SELECT department_id FROM Departments")]
    statuses = ["Planning","Active","Active","Completed","On Hold"]
    proj_ids = []
    for name in names:
        start = date(random.randint(2022,2024), random.randint(1,6), 1)
        pid   = db.execute(
            "INSERT INTO Projects (project_name,department_id,start_date,end_date,status,budget) VALUES (%s,%s,%s,%s,%s,%s)",
            (name, random.choice(dept_ids), start, start+timedelta(days=random.randint(180,540)),
             random.choice(statuses), random.randint(50000,500000)))
        proj_ids.append(pid)
    emp_ids = [e["employee_id"] for e in db.fetch_all("SELECT employee_id FROM Employees ORDER BY RAND() LIMIT 300")]
    roles   = ["Lead","Contributor","Analyst","Reviewer","Coordinator"]
    adata   = []
    for pid in proj_ids:
        for emp_id in random.sample(emp_ids, min(20, len(emp_ids))):
            adata.append((emp_id, pid, random.choice(roles), date(2024, random.randint(1,6), 1), random.randint(10,160)))
    inserted = db.execute_many(
        "INSERT IGNORE INTO Project_Assignments (employee_id,project_id,role_in_project,assigned_date,hours_allocated) VALUES (%s,%s,%s,%s,%s)",
        adata)
    log(f"✅ Projects: {len(proj_ids)} | Assignments: {inserted:,}")

def load_scd2():
    header("STEP 4: Loading SCD Type 2 → hr_olap.Dim_Employee")
    df = pd.read_csv(HIST_FILE)
    db.connect("hr_olap")
    query = """
        INSERT IGNORE INTO Dim_Employee (
            employee_id,department_name,job_role,job_level,
            monthly_income,performance_rating,environment_satisfaction,
            job_satisfaction,start_date,end_date,is_current
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    data = [(int(r["EmployeeID"]),str(r["Department"]),str(r["JobRole"]),int(r["JobLevel"]),
             float(r["MonthlyIncome"]),int(r["PerformanceRating"]),int(r["EnvironmentSatisfaction"]),
             int(r["JobSatisfaction"]),str(r["StartDate"]),
             str(r["EndDate"]) if pd.notna(r["EndDate"]) else None, int(r["IsCurrent"]))
            for _, r in df.iterrows()]
    total = 0
    for i in range(0, len(data), BATCH_SIZE):
        total += db.execute_many(query, data[i:i+BATCH_SIZE])
    log(f"✅ Dim_Employee SCD2: {total:,} rows")

def run_etl():
    header("STEP 5: Running ETL Stored Procedures")
    db.connect("hr_olap")
    for proc in ["sp_populate_dim_date","sp_load_dim_department","sp_load_dim_project"]:
        try:
            db.call_procedure(proc)
            log(f"✅ {proc}")
        except Exception as e:
            log(f"⚠️  {proc} skipped — {e}")

if __name__ == "__main__":
    print("\n" + "═"*55)
    print("  Enterprise HR Analytics — Data Loader")
    print("═"*55)
    try:
        load_employees()
        load_reviews()
        load_projects()
        load_scd2()
        run_etl()
        print("\n✅ ALL DATA LOADED! Run: streamlit run streamlit_app/app.py\n")
    except Exception as e:
        print(f"\n❌ Loader failed: {e}")
        raise
