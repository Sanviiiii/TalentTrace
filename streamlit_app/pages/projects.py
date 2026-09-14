"""streamlit_app/pages/projects.py"""
import streamlit as st
from datetime import date
from backend.managers import ProjectManager, DepartmentManager
from backend.models import Project, ProjectAssignment

def render():
    st.title("Project Management")
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["New Project", "Assign Employee", "View Projects"])

    dept_mgr  = DepartmentManager()
    depts     = dept_mgr.get_all()
    dept_opts = {d["department_name"]: d["department_id"] for d in depts}

    with tab1:
        st.subheader("Create New Project")
        with st.form("new_project_form"):
            c1,c2 = st.columns(2)
            with c1:
                proj_name  = st.text_input("Project Name*")
                dept_name  = st.selectbox("Department*", list(dept_opts.keys()))
                start_date = st.date_input("Start Date*", value=date.today())
                budget     = st.number_input("Budget (₹)", min_value=0, value=100000)
            with c2:
                status     = st.selectbox("Status", ["Planning","Active","On Hold","Completed","Cancelled"])
                end_date   = st.date_input("End Date (optional)", value=None)
                description= st.text_area("Description")
            submitted = st.form_submit_button("Create Project", use_container_width=True, type="primary")
            if submitted:
                if not proj_name: st.error("Project name required.")
                else:
                    try:
                        proj = Project(project_name=proj_name, department_id=dept_opts[dept_name], start_date=start_date, end_date=end_date, status=status, budget=float(budget), description=description)
                        mgr = ProjectManager()
                        pid = mgr.add(proj)
                        st.markdown(f"<div class='success-box'>Project created! ID: <b>{pid}</b></div>", unsafe_allow_html=True)
                    except Exception as e: st.error(str(e))

    with tab2:
        st.subheader("Assign Employee to Project")
        try:
            proj_mgr   = ProjectManager()
            all_projs  = proj_mgr.get_all()
            proj_opts  = {f"[{p['project_id']}] {p['project_name']}": p["project_id"] for p in all_projs}
        except: proj_opts = {}

        with st.form("assign_form"):
            sel_proj   = st.selectbox("Select Project*", list(proj_opts.keys()) if proj_opts else ["—"])
            emp_id_a   = st.number_input("Employee ID*", min_value=1, step=1)
            role       = st.selectbox("Role", ["Lead","Contributor","Analyst","Reviewer","Coordinator"])
            hours      = st.number_input("Hours", min_value=0, value=40)
            assigned_d = st.date_input("Assigned Date", value=date.today())
            submitted2 = st.form_submit_button("Assign Employee", use_container_width=True, type="primary")
            if submitted2 and proj_opts:
                try:
                    asgn = ProjectAssignment(employee_id=int(emp_id_a), project_id=proj_opts[sel_proj], assigned_date=assigned_d, role_in_project=role, hours_allocated=int(hours))
                    mgr = ProjectManager()
                    mgr.assign_employee(asgn)
                    st.markdown(f"<div class='success-box'>Employee {emp_id_a} assigned!</div>", unsafe_allow_html=True)
                except Exception as e: st.error(str(e))

    with tab3:
        st.subheader("All Projects")
        try:
            import pandas as pd
            mgr = ProjectManager()
            projs = mgr.get_all()
            if projs:
                st.dataframe(pd.DataFrame(projs), use_container_width=True, hide_index=True)
        except Exception as e: st.error(str(e))