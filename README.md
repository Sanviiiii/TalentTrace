# Enterprise Employee Analytics & Data Warehouse System

A full-stack HR analytics platform built with Python OOP, MySQL (OLTP + OLAP Star Schema), and Streamlit.

---

## Project Structure

```
enterprise-hr-analytics/
├── backend/
│   ├── __init__.py
│   ├── db_manager.py          # Singleton MySQL connection manager
│   ├── models.py              # Entity classes: Employee, Project, Review...
│   └── managers.py            # DAL: EmployeeManager, AnalyticsManager...
├── sql/
│   ├── 01_oltp_ddl.sql        # OLTP schema — 6 normalized tables
│   ├── 02_olap_ddl.sql        # OLAP Star Schema — Fact + 4 Dim tables
│   ├── 03_etl_procedures.sql  # 5 ETL stored procedures (incl. SCD2)
│   └── 04_analytical_queries.sql  # CTEs + Window Functions for dashboards
├── scripts/
│   ├── synthesizer.py         # Scales 1,470 → 100,000 rows + SCD2 history
│   └── data_loader.py         # Bulk loads CSVs into MySQL
├── streamlit_app/
│   ├── app.py                 # Main entry point + sidebar navigation
│   └── pages/
│       ├── home.py            # Overview and architecture
│       ├── onboard.py         # Employee forms + SCD2 trigger
│       ├── projects.py        # Project creation + assignments
│       ├── reviews.py         # Performance review submission
│       └── dashboard.py       # OLAP analytics + Plotly charts
├── data/
│   └── WA_Fn-UseC_-HR-Employee-Attrition.csv   # IBM HR source dataset
├── diagrams/                  # draw.io ER + Star Schema diagrams (manual)
├── .env.example               # Template for DB credentials
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Database | MySQL 8.0 (OLTP + OLAP) |
| Frontend | Streamlit + Plotly |
| Data Synthesis | pandas + Faker |
| OOP Backend | Singleton, DAL, Entity classes |
| Deployment | Streamlit Community Cloud |

---

## SETUP GUIDE

### Prerequisites

- Python 3.11+
- MySQL 8.0 (with MySQL Workbench)
- Git

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/enterprise-hr-analytics.git
cd enterprise-hr-analytics
```

---

### Step 2 — Create virtual environment

```bash
# Create
python -m venv venv

# Activate — Windows:
venv\Scripts\activate

# Activate — Mac/Linux:
source venv/bin/activate

# Install all packages
pip install -r requirements.txt
```

---

### Step 3 — Configure database credentials

```bash
cp .env.example .env
```

Open `.env` and fill in your MySQL password:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_actual_password
```

---

### Step 4 — Set up MySQL schemas

Open **MySQL Workbench**, connect to your local server.
Run these files **in this exact order**:

```
1. sql/01_oltp_ddl.sql         → creates hr_oltp schema + 6 tables
2. sql/02_olap_ddl.sql         → creates hr_olap schema + star schema
3. sql/03_etl_procedures.sql   → creates 5 ETL stored procedures
```

Verify:
```sql
SHOW DATABASES;
-- Expected: hr_oltp, hr_olap

USE hr_oltp; SHOW TABLES;
-- Expected: Departments, Employees, Projects,
--           Project_Assignments, Performance_Reviews, Salary_History

USE hr_olap; SHOW TABLES;
-- Expected: Dim_Date, Dim_Department, Dim_Employee,
--           Dim_Project, Fact_PerformanceReviews
```

---

### Step 5 — Synthesize data

```bash
python scripts/synthesizer.py
```

Expected output:
```
Source dataset loaded: 1470 rows, 35 columns
Synthesizing 100,000 employee records ...
  ✓ Saved  data/employees_synthesized.csv  (100,000 rows)
Generating SCD Type 2 history for 5,000 employees ...
  ✓ Saved  data/employees_historical.csv  (12,451 rows)
✅ Data synthesis complete!
```

---

### Step 6 — Load data into MySQL

```bash
python scripts/data_loader.py
```

Expected output:
```
STEP 1: Loading Employees into hr_oltp
  ✅ Employees: 100,000 rows
STEP 2: Generating Performance Reviews
  ✅ Reviews: 60,000 rows
STEP 3: Loading Projects & Assignments
  ✅ Projects: 10 | Assignments: 200
STEP 4: Loading SCD Type 2 → hr_olap.Dim_Employee
  ✅ Dim_Employee SCD2: 12,451 rows
STEP 5: Running ETL Stored Procedures
  ✅ sp_populate_dim_date
  ✅ sp_load_dim_department
  ✅ sp_load_dim_project
✅ ALL DATA LOADED!
```

---

### Step 7 — Run the Streamlit app

```bash
streamlit run streamlit_app/app.py
```

Opens at: **http://localhost:8501**

---

## TESTING GUIDE

### Test 1 — Check packages installed

```bash
python -c "import pandas; import faker; import mysql.connector; import streamlit; import plotly; print('✅ All packages OK')"
```

### Test 2 — Test models (no MySQL needed)

```bash
python -c "
from backend.models import Employee, Department, Project, Review
from datetime import date

emp = Employee('Shayan','Haque','s@test.com',date(2024,1,1),1,'Data Engineer',85000,age=23,job_level=2)
assert emp.validate() == [], 'Validation failed'
assert emp.full_name == 'Shayan Haque'
assert emp.annual_income == 1020000

r = Review(1,date(2024,1,1),2024,4,review_quarter=2)
assert r.rating_label == 'Outstanding'

print('✅ All model tests passed')
"
```

### Test 3 — Test Singleton pattern

```bash
python -c "
from backend.db_manager import DatabaseConnection
db1 = DatabaseConnection()
db2 = DatabaseConnection()
assert db1 is db2, 'Singleton broken!'
print('✅ Singleton works — same object returned')
"
```

### Test 4 — Test synthesizer output

```bash
python -c "
import pandas as pd
df1 = pd.read_csv('data/employees_synthesized.csv')
df2 = pd.read_csv('data/employees_historical.csv')
assert len(df1) >= 100000
assert df2['IsCurrent'].sum() == 5000
print(f'✅ Main: {len(df1):,} rows | SCD2: {len(df2):,} rows')
"
```

### Test 5 — Test database connection (needs MySQL running)

```bash
python -c "
from backend.db_manager import DatabaseConnection
db = DatabaseConnection()
db.connect('hr_oltp')
rows = db.fetch_all('SELECT department_name FROM Departments')
print('Departments:', [r['department_name'] for r in rows])
assert len(rows) == 3
print('✅ DB connection test passed')
db.disconnect()
"
```

### Test 6 — Verify Streamlit pages load

```bash
python -c "
import ast, os
pages = ['streamlit_app/pages/home.py','streamlit_app/pages/onboard.py',
         'streamlit_app/pages/projects.py','streamlit_app/pages/reviews.py',
         'streamlit_app/pages/dashboard.py']
for p in pages:
    with open(p) as f: src = f.read()
    ast.parse(src)
    assert 'def render():' in src
    print(f'  ✅ {p.split(\"/\")[-1]}')
print('✅ All Streamlit pages OK')
"
```

---

## Data Warehousing Concepts

### SCD Type 2
When department or salary changes (>5%) via the UI:
- Old row: `end_date = today, is_current = 0`
- New row: `start_date = today, end_date = NULL, is_current = 1`

### Star Schema
```
Fact_PerformanceReviews (central fact table)
    ├── surrogate_key → Dim_Employee  (SCD Type 2)
    ├── dept_key      → Dim_Department
    ├── project_key   → Dim_Project
    └── date_key      → Dim_Date
```

### Advanced SQL Used
| Function | Used For |
|---|---|
| `LAG()` | Year-over-year performance comparison |
| `DENSE_RANK()` | Top performers leaderboard per department |
| `NTILE(4)` | Attrition risk quartile bucketing |
| `PERCENT_RANK()` | Salary percentile within department |
| CTEs | Multi-step analytical pipeline queries |

---

## Streamlit Cloud Deployment

1. Push all code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set main file: `streamlit_app/app.py`
5. Under **Settings → Secrets**, add:

```toml
DB_HOST = "your-cloud-db-host"
DB_PORT = "3306"
DB_USER = "your-db-user"
DB_PASSWORD = "your-db-password"
```

6. Click **Deploy** → get your public URL

---

## Common Errors & Fixes

| Error | Fix |
|---|---|
| `No module named 'mysql'` | `pip install mysql-connector-python` |
| `No module named 'dotenv'` | `pip install python-dotenv` |
| `Access denied for user 'root'` | Check `.env` password matches MySQL |
| `Table doesn't exist` | Re-run SQL files in correct order (01 → 02 → 03) |
| `streamlit: command not found` | Activate venv first |
| `ModuleNotFoundError: backend` | Run commands from project root folder |
| `Import managers error` | Ensure `__init__.py` exists in `backend/` |

---

## Team Responsibilities

| Teammate | Role | Files Owned |
|---|---|---|
| Teammate 1 | Data Engineer / DB Lead | `synthesizer.py`, `data_loader.py`, all `.sql` files, diagrams |
| Teammate 2 | Python / Backend Lead | `db_manager.py`, `models.py`, `managers.py` |
| Teammate 3 | Frontend / DevOps Lead | all `streamlit_app/` files, GitHub PRs, Streamlit Cloud deploy |

---

## GitHub Branch Strategy

```bash
main                          # protected — only merged PRs
├── feature/database-design   # Teammate 1
├── feature/etl-pipeline      # Teammate 1
├── feature/python-backend    # Teammate 2
└── feature/streamlit-ui      # Teammate 3
```
