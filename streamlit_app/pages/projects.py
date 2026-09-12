"""streamlit_app/pages/projects.py — Projects and assignments"""
import streamlit as st
from datetime import date
from backend.managers import ProjectManager, DepartmentManager, EmployeeManager
from backend.models import Project, ProjectAssignment

def render():
    st.title("📁 Project Management")
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["➕ New Project", "👤 Assign Employee", "📋 View Projects"])

    dept_mgr  = DepartmentManager()
    depts     = dept_mgr.get_all()
    dept_opts = {d["department_name"]: d["department_id"] for d in depts}

    # ── TAB 1: New Project ────────────────────────────────────
    with tab1:
        st.subheader("Create New Project")
        with st.form("new_project_form"):
            c1,c2 = st.columns(2)
            with c1:
                proj_name  = st.text_input("Project Name*")
                dept_name  = st.selectbox("Department*", list(dept_opts.keys()))
                start_date = st.date_input("Start Date*", value=date.today())
                budget     = st.number_input("Budget (₹)", min_value=0, value=100000, step=10000)
            with c2:
                status     = st.selectbox("Status", ["Planning","Active","On Hold","Completed","Cancelled"])
                end_date   = st.date_input("End Date (optional)", value=None)
                description= st.text_area("Description", height=120)
            submitted = st.form_submit_button("➕ Create Project", use_container_width=True, type="primary")
            if submitted:
                if not proj_name:
                    st.error("Project name is required.")
                else:
                    try:
                        proj = Project(
                            project_name=proj_name,
                            department_id=dept_opts[dept_name],
                            start_date=start_date,
                            end_date=end_date,
                            status=status, budget=float(budget),
                            description=description
                        )
                        errors = proj.validate()
                        if errors:
                            for e in errors: st.error(e)
                        else:
                            mgr = ProjectManager()
                            pid = mgr.add(proj)
                            st.success(f"✅ Project '{proj_name}' created! Project ID: **{pid}**")
                    except Exception as e:
                        st.error(str(e))

    # ── TAB 2: Assign Employee ────────────────────────────────
    with tab2:
        st.subheader("Assign Employee to Project")
        try:
            proj_mgr   = ProjectManager()
            all_projs  = proj_mgr.get_all()
            proj_opts  = {f"[{p['project_id']}] {p['project_name']}": p["project_id"] for p in all_projs}
        except:
            proj_opts = {}
            st.warning("No projects found. Create a project first.")

        with st.form("assign_form"):
            sel_proj   = st.selectbox("Select Project*", list(proj_opts.keys()) if proj_opts else ["—"])
            emp_id_a   = st.number_input("Employee ID*", min_value=1, step=1)
            role       = st.selectbox("Role in Project", ["Lead","Contributor","Analyst","Reviewer","Coordinator"])
            hours      = st.number_input("Hours Allocated", min_value=0, max_value=500, value=40)
            assigned_d = st.date_input("Assigned Date", value=date.today())
            submitted2 = st.form_submit_button("👤 Assign Employee", use_container_width=True, type="primary")
            if submitted2 and proj_opts:
                try:
                    asgn = ProjectAssignment(
                        employee_id=int(emp_id_a),
                        project_id=proj_opts[sel_proj],
                        assigned_date=assigned_d,
                        role_in_project=role,
                        hours_allocated=int(hours)
                    )
                    mgr = ProjectManager()
                    mgr.assign_employee(asgn)
                    st.success(f"✅ Employee {emp_id_a} assigned to project as **{role}**")
                except Exception as e:
                    st.error(str(e))

    # ── TAB 3: View Projects ──────────────────────────────────
    with tab3:
        st.subheader("All Projects")
        try:
            import pandas as pd
            mgr   = ProjectManager()
            projs = mgr.get_all()
            if projs:
                df = pd.DataFrame(projs)
                status_filter = st.multiselect("Filter by Status", df["status"].unique().tolist(), default=df["status"].unique().tolist())
                df = df[df["status"].isin(status_filter)]
                st.dataframe(df[["project_id","project_name","department_name","status","start_date","end_date","budget"]],
                             use_container_width=True, hide_index=True)
                if st.checkbox("Show assignments for a project"):
                    pid = st.number_input("Project ID", min_value=1, step=1)
                    asgns = mgr.get_assignments(int(pid))
                    if asgns:
                        st.dataframe(pd.DataFrame(asgns), use_container_width=True, hide_index=True)
                    else:
                        st.info("No assignments found for this project.")
            else:
                st.info("No projects yet. Create one above!")
        except Exception as e:
            st.error(f"Could not load projects: {e}")
