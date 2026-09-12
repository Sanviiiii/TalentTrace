"""
synthesizer.py
--------------
Step 1 of the Enterprise HR Analytics project.

What this script does:
  1. Reads the original IBM HR dataset (1,470 rows).
  2. Scales it up to 100,000+ rows using realistic random variation.
  3. For ~5,000 employees, generates 2-3 historical records to satisfy
     SCD Type 2 (department changes, salary hikes, promotions).
  4. Outputs two CSV files:
       - data/employees_synthesized.csv   (100K current snapshot)
       - data/employees_historical.csv    (SCD Type 2 history records)
"""

import pandas as pd
import numpy as np
from faker import Faker
import random
import uuid
from datetime import datetime, timedelta
import os

# ── reproducibility ──────────────────────────────────────────────────────────
random.seed(42)
np.random.seed(42)
fake = Faker()
Faker.seed(42)

# ── load source data ──────────────────────────────────────────────────────────
SOURCE_PATH = "data/WA_Fn-UseC_-HR-Employee-Attrition.csv"
TARGET_ROWS = 100_000
SCD_EMPLOYEE_COUNT = 5_000   # employees who will have historical records

df_source = pd.read_csv(SOURCE_PATH)
print(f"Source dataset loaded: {len(df_source)} rows, {len(df_source.columns)} columns")

# ── valid categorical values (from source) ────────────────────────────────────
DEPARTMENTS      = ["Sales", "Research & Development", "Human Resources"]
JOB_ROLES        = {
    "Sales":                    ["Sales Executive", "Sales Representative", "Manager"],
    "Research & Development":   ["Research Scientist", "Laboratory Technician",
                                 "Manufacturing Director", "Healthcare Representative",
                                 "Research Director", "Manager"],
    "Human Resources":          ["Human Resources", "Manager"],
}
EDUCATION_FIELDS = ["Life Sciences", "Medical", "Marketing",
                    "Technical Degree", "Human Resources", "Other"]
MARITAL_STATUS   = ["Single", "Married", "Divorced"]
BUSINESS_TRAVEL  = ["Travel_Rarely", "Travel_Frequently", "Non-Travel"]
GENDERS          = ["Male", "Female"]
ATTRITION        = ["Yes", "No"]          # weighted below

# salary bands per job level (realistic ranges)
SALARY_BAND = {
    1: (1_000,  5_000),
    2: (4_000,  9_000),
    3: (7_000, 13_000),
    4: (11_000, 17_000),
    5: (15_000, 20_000),
}

# ── helper: generate one synthetic employee row ───────────────────────────────
def make_employee(emp_id: int) -> dict:
    dept       = random.choice(DEPARTMENTS)
    job_level  = random.choices([1, 2, 3, 4, 5], weights=[30, 30, 20, 12, 8])[0]
    job_role   = random.choice(JOB_ROLES[dept])
    age        = random.randint(18, 60)
    yrs_company= random.randint(0, min(age - 18, 40))
    yrs_role   = random.randint(0, yrs_company)
    yrs_promo  = random.randint(0, yrs_role)
    yrs_mgr    = random.randint(0, yrs_company)
    salary_lo, salary_hi = SALARY_BAND[job_level]
    monthly_income = random.randint(salary_lo, salary_hi)

    return {
        "EmployeeID":               emp_id,
        "Age":                      age,
        "Attrition":                random.choices(ATTRITION, weights=[16, 84])[0],
        "BusinessTravel":           random.choice(BUSINESS_TRAVEL),
        "DailyRate":                random.randint(100, 1500),
        "Department":               dept,
        "DistanceFromHome":         random.randint(1, 29),
        "Education":                random.randint(1, 5),
        "EducationField":           random.choice(EDUCATION_FIELDS),
        "EnvironmentSatisfaction":  random.randint(1, 4),
        "Gender":                   random.choice(GENDERS),
        "HourlyRate":               random.randint(30, 100),
        "JobInvolvement":           random.randint(1, 4),
        "JobLevel":                 job_level,
        "JobRole":                  job_role,
        "JobSatisfaction":          random.randint(1, 4),
        "MaritalStatus":            random.choice(MARITAL_STATUS),
        "MonthlyIncome":            monthly_income,
        "MonthlyRate":              random.randint(2_000, 27_000),
        "NumCompaniesWorked":       random.randint(0, 9),
        "OverTime":                 random.choices(["Yes", "No"], weights=[28, 72])[0],
        "PercentSalaryHike":        random.randint(11, 25),
        "PerformanceRating":        random.choices([3, 4], weights=[85, 15])[0],
        "RelationshipSatisfaction": random.randint(1, 4),
        "StockOptionLevel":         random.choices([0, 1, 2, 3], weights=[40, 35, 15, 10])[0],
        "TotalWorkingYears":        random.randint(0, 40),
        "TrainingTimesLastYear":    random.randint(0, 6),
        "WorkLifeBalance":          random.randint(1, 4),
        "YearsAtCompany":           yrs_company,
        "YearsInCurrentRole":       yrs_role,
        "YearsSinceLastPromotion":  yrs_promo,
        "YearsWithCurrManager":     yrs_mgr,
        # PII generated via Faker
        "FirstName":                fake.first_name(),
        "LastName":                 fake.last_name(),
        "Email":                    fake.unique.email(),
        "Phone":                    fake.phone_number()[:15],
        "HireDate":                 fake.date_between(
                                        start_date="-{0}y".format(yrs_company + 1),
                                        end_date="today").isoformat(),
    }

# ── build 100K employee snapshot ──────────────────────────────────────────────
print(f"Synthesizing {TARGET_ROWS:,} employee records …")
rows = [make_employee(i + 1) for i in range(TARGET_ROWS)]
df_synth = pd.DataFrame(rows)

os.makedirs("data", exist_ok=True)
df_synth.to_csv("data/employees_synthesized.csv", index=False)
print(f"  ✓ Saved  data/employees_synthesized.csv  ({len(df_synth):,} rows)")

# ── SCD Type 2: generate historical records ────────────────────────────────────
"""
For SCD_EMPLOYEE_COUNT employees we create 2–3 snapshots:
  - Snapshot 1 (oldest):  original dept / lower salary  →  end_date set
  - Snapshot 2 (middle):  possible dept change / moderate salary
  - Snapshot 3 (current): is_current = 1, end_date = NULL

Columns added for SCD:
  surrogate_key, start_date, end_date, is_current
"""

print(f"\nGenerating SCD Type 2 history for {SCD_EMPLOYEE_COUNT:,} employees …")

today = datetime.today().date()

scd_rows = []

scd_emp_ids = random.sample(range(1, TARGET_ROWS + 1), SCD_EMPLOYEE_COUNT)

for emp_id in scd_emp_ids:
    # how many history versions? 2 or 3
    versions = random.choice([2, 3])

    # pick a hire date between 3-10 years ago
    yrs_ago   = random.randint(3, 10)
    hire_date = today - timedelta(days=365 * yrs_ago)

    dept_sequence  = [random.choice(DEPARTMENTS)]
    for _ in range(versions - 1):
        # sometimes change department, sometimes stay
        if random.random() < 0.6:
            new_dept = random.choice([d for d in DEPARTMENTS if d != dept_sequence[-1]])
        else:
            new_dept = dept_sequence[-1]
        dept_sequence.append(new_dept)

    salary = random.randint(2_000, 8_000)   # start low

    version_start = hire_date
    for v_idx, dept in enumerate(dept_sequence):
        is_current = 1 if v_idx == len(dept_sequence) - 1 else 0

        if is_current:
            version_end = None
        else:
            # each version lasts 1-3 years
            gap = timedelta(days=365 * random.randint(1, 3))
            version_end = version_start + gap

        # salary grows between versions
        salary = int(salary * random.uniform(1.05, 1.25))

        job_level  = random.choices([1, 2, 3, 4, 5], weights=[30, 30, 20, 12, 8])[0]
        job_role   = random.choice(JOB_ROLES[dept])

        scd_rows.append({
            "SurrogateKey":             str(uuid.uuid4()),
            "EmployeeID":               emp_id,
            "Department":               dept,
            "JobRole":                  job_role,
            "JobLevel":                 job_level,
            "MonthlyIncome":            min(salary, 19_999),
            "PerformanceRating":        random.choices([3, 4], weights=[85, 15])[0],
            "EnvironmentSatisfaction":  random.randint(1, 4),
            "JobSatisfaction":          random.randint(1, 4),
            "StartDate":                version_start.isoformat(),
            "EndDate":                  version_end.isoformat() if version_end else None,
            "IsCurrent":                is_current,
        })

        if version_end:
            version_start = version_end

df_scd = pd.DataFrame(scd_rows)
df_scd.to_csv("data/employees_historical.csv", index=False)
print(f"  ✓ Saved  data/employees_historical.csv  ({len(df_scd):,} rows)")

# ── summary ───────────────────────────────────────────────────────────────────
print("\n── Summary ──────────────────────────────────────────────────────────────")
print(f"  Main snapshot  : {len(df_synth):,} rows  →  data/employees_synthesized.csv")
print(f"  SCD history    : {len(df_scd):,} rows  →  data/employees_historical.csv")
print(f"  Employees with history : {df_scd['EmployeeID'].nunique():,}")
print(f"  Current records (SCD)  : {df_scd[df_scd['IsCurrent']==1].shape[0]:,}")
print(f"  Historical records     : {df_scd[df_scd['IsCurrent']==0].shape[0]:,}")
print("\nDepartment distribution in main dataset:")
print(df_synth["Department"].value_counts().to_string())
print("\nJob Level distribution:")
print(df_synth["JobLevel"].value_counts().sort_index().to_string())
print("\n✅ Data synthesis complete!")
