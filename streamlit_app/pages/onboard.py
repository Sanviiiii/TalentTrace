"""streamlit_app/pages/onboard.py"""
import streamlit as st
from datetime import date
from backend.managers import EmployeeManager, DepartmentManager
from backend.models import Employee

def render():
    st.title("Employee Onboarding")
    st.markdown("Add a new employee or update an existing one. Department/salary changes automatically trigger **SCD Type 2** updates in the Data Warehouse.")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["New Employee", "Update Department (SCD2)", "Update Salary (SCD2)"])

    with tab1:
        st.subheader("New Employee Details")
        dept_mgr  = DepartmentManager()
        depts     = dept_mgr.get_all()
        dept_opts = {d["department_name"]: d["department_id"] for d in depts}

        with st.form("new_employee_form"):
            c1,c2 = st.columns(2)
            with c1:
                first_name = st.text_input("First Name*")
                email      = st.text_input("Email*")
                gender     = st.selectbox("Gender", ["Male","Female","Other"])
                dept_name  = st.selectbox("Department*", list(dept_opts.keys()))
                job_level  = st.slider("Job Level", 1, 5, 2)
                monthly_income = st.number_input("Monthly Income (₹)*", min_value=1000, max_value=20000, value=5000, step=500)
                hire_date  = st.date_input("Hire Date*", value=date.today())
            with c2:
                last_name  = st.text_input("Last Name*")
                phone      = st.text_input("Phone")
                age        = st.number_input("Age*", min_value=18, max_value=65, value=28)
                job_role   = st.text_input("Job Role*", value="Analyst")
                education  = st.slider("Education Level (1-5)", 1, 5, 3)
                edu_field  = st.selectbox("Education Field", ["Life Sciences","Medical","Marketing","Technical Degree","Human Resources","Other"])
                marital    = st.selectbox("Marital Status", ["Single","Married","Divorced"])

            c1,c2,c3 = st.columns(3)
            with c1: travel   = st.selectbox("Business Travel", ["Travel_Rarely","Travel_Frequently","Non-Travel"])
            with c2: overtime = st.selectbox("Over Time", ["No","Yes"])
            with c3: distance = st.number_input("Distance from Home (km)", 1, 100, 10)

            submitted = st.form_submit_button("Onboard Employee", use_container_width=True, type="primary")
            if submitted:
                if not all([first_name, last_name, email, job_role]):
                    st.error("Please fill all required (*) fields.")
                else:
                    try:
                        emp = Employee(
                            first_name=first_name, last_name=last_name, email=email, phone=phone, gender=gender, age=int(age),
                            hire_date=hire_date, department_id=dept_opts[dept_name], job_role=job_role, job_level=int(job_level),
                            monthly_income=float(monthly_income), education=int(education), education_field=edu_field,
                            marital_status=marital, business_travel=travel, distance_from_home=int(distance), over_time=overtime,
                        )
                        errors = emp.validate()
                        if errors:
                            for e in errors: st.error(e)
                        else:
                            mgr = EmployeeManager()
                            emp_id = mgr.add(emp)
                            st.success(f"Employee '{first_name} {last_name}' onboarded! ID: **{emp_id}**")
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab2:
        st.subheader("Change Employee Department")
        st.markdown("<div class='warning-box'><b>SCD Type 2 will be triggered:</b> The old department record will be closed and a new record opened.</div>", unsafe_allow_html=True)
        with st.form("update_dept_form"):
            emp_id_input = st.number_input("Employee ID*", min_value=1, step=1)
            new_dept     = st.selectbox("New Department*", list(dept_opts.keys()))
            reason       = st.text_input("Reason for transfer")
            submitted2   = st.form_submit_button("Update Department", use_container_width=True, type="primary")
            if submitted2:
                try:
                    mgr = EmployeeManager()
                    mgr.update_department(int(emp_id_input), dept_opts[new_dept], reason)
                    st.markdown(f"<div class='success-box'>Department updated for Employee {emp_id_input} → <b>{new_dept}</b></div>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(str(e))

    with tab3:
        st.subheader("Update Employee Salary")
        with st.form("update_salary_form"):
            emp_id_s   = st.number_input("Employee ID*", min_value=1, step=1, key="sal_id")
            new_salary = st.number_input("New Monthly Income (₹)*", min_value=1000, value=8000, step=500)
            reason_s   = st.text_input("Reason")
            submitted3 = st.form_submit_button("Update Salary", use_container_width=True, type="primary")
            if submitted3:
                try:
                    mgr = EmployeeManager()
                    mgr.update_salary(int(emp_id_s), float(new_salary), reason_s)
                    st.markdown(f"<div class='success-box'>Salary updated for Employee {emp_id_s} → ₹{new_salary:,}/month</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(str(e))