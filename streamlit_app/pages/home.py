"""streamlit_app/pages/home.py"""
import streamlit as st

def render():
    st.title("👥 Enterprise HR Analytics Platform")
    st.markdown("### Welcome to the centralized HR Data Warehouse System")
    st.markdown("---")
    col1,col2,col3,col4 = st.columns(4)
    metrics = [("100K+","Employee Records"),("2","MySQL Schemas"),("SCD2","Historical Tracking"),("5","ETL Procedures")]
    for col,(val,label) in zip([col1,col2,col3,col4],metrics):
        with col:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{val}</div><div class='metric-label'>{label}</div></div>",unsafe_allow_html=True)
    st.markdown("---")
    c1,c2 = st.columns(2)
    with c1:
        st.markdown("#### OLTP Schema (`hr_oltp`)")
        st.markdown("- **Departments** — master dept list\n- **Employees** — 100K records\n- **Projects** — company projects\n- **Project_Assignments** — bridge table\n- **Performance_Reviews** — reviews\n- **Salary_History** — audit trail")
    with c2:
        st.markdown("#### OLAP Star Schema (`hr_olap`)")
        st.markdown("- **Fact_PerformanceReviews** — central fact\n- **Dim_Employee** — SCD Type 2\n- **Dim_Department** — dept dimension\n- **Dim_Project** — project dimension\n- **Dim_Date** — calendar 2015–2030")
    st.markdown("---")
    st.markdown("### 🚀 Quick Navigation")
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.info("**➕ Onboard Employee**\nAdd employees, trigger SCD2 on dept/salary change")
    with c2: st.info("**📁 Projects**\nCreate projects and assign team members")
    with c3: st.info("**📝 Reviews**\nSubmit performance reviews")
    with c4: st.info("**📊 Dashboard**\nYoY trends, top performers, attrition risk")
