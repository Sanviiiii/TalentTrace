"""streamlit_app/pages/dashboard.py"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from backend.managers import AnalyticsManager

def _try_load(fn):
    try:
        return fn(), None
    except Exception as e:
        return None, str(e)

def render():
    st.title("Analytics Dashboard")
    st.markdown("Powered by hr_olap Star Schema — Window Functions + CTEs")
    st.markdown("---")

    mgr = AnalyticsManager()

    # ── KPI Cards ─────────────────────────────────────────────
    st.subheader("Department KPIs")
    kpis, err = _try_load(mgr.get_department_kpis)
    if err:
        st.warning(f"KPI data not available yet (run ETL first): {err}")
    elif kpis:
        df_kpi = pd.DataFrame(kpis)
        cols   = st.columns(len(df_kpi))
        for col, (_, row) in zip(cols, df_kpi.iterrows()):
            with col:
                st.metric(label=row["department_name"],
                          value=f"{int(row['headcount']):,}",
                          delta=f"Attrition: {row['attrition_rate']}%")
                st.caption(f"Avg Salary: ₹{row['avg_salary']:,.0f}")
                st.caption(f"Avg Performance: {row['avg_performance']}/4")

    st.markdown("---")

    # ── YoY Performance ───────────────────────────────────────
    st.subheader("Year-over-Year Performance Trends")
    st.caption("SQL: LAG() window function over review_year PARTITION BY department_name")
    yoy, err = _try_load(mgr.get_yoy_performance)
    if err:
        st.info(f"YoY data not available yet: {err}")
    elif yoy:
        df_yoy = pd.DataFrame(yoy)
        
        # Cast SQL Decimals to floats
        df_yoy["avg_rating"] = df_yoy["avg_rating"].astype(float)
        df_yoy["avg_satisfaction"] = df_yoy["avg_satisfaction"].astype(float)

        fig = px.line(df_yoy, x="review_year", y="avg_rating",
                      color="department_name", markers=True,
                      title="Average Performance Rating by Year & Department",
                      color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(yaxis=dict(range=[1,4]), legend_title="Department")
        st.plotly_chart(fig, theme="streamlit", use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig2 = px.bar(df_yoy, x="department_name", y="employee_count",
                          color="review_year", barmode="group",
                          title="Headcount Reviewed per Year",
                          color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig2, theme="streamlit", use_container_width=True)
        with col2:
            fig3 = px.bar(df_yoy, x="review_year", y="avg_satisfaction",
                          color="department_name", barmode="group",
                          title="Avg Job Satisfaction by Year",
                          color_discrete_sequence=px.colors.qualitative.Set1)
            fig3.update_layout(yaxis=dict(range=[1,4]))
            st.plotly_chart(fig3, theme="streamlit", use_container_width=True)

    st.markdown("---")

    # ── Top Performers ────────────────────────────────────────
    st.subheader("Top Performers by Department")
    st.caption("SQL: DENSE_RANK() OVER (PARTITION BY department_name ORDER BY avg_rating DESC)")
    c1, c2 = st.columns([1,3])
    with c1:
        year_filter = st.selectbox("Filter Year", [None, 2022, 2023, 2024], format_func=lambda x: "All Years" if x is None else str(x))
        top_n       = st.slider("Top N per dept", 3, 20, 5)
    top, err = _try_load(lambda: mgr.get_top_performers(year=year_filter, limit=top_n))
    if err:
        st.info(f"Top performers data not available yet: {err}")
    elif top:
        df_top = pd.DataFrame(top)
        
        # Cast SQL Decimals to floats
        df_top["avg_rating"] = df_top["avg_rating"].astype(float)
        df_top["monthly_income"] = df_top["monthly_income"].astype(float)

        with c2:
            fig = px.bar(df_top, x="full_name", y="avg_rating",
                         color="department_name", text="dept_rank",
                         title=f"Top {top_n} Performers per Department",
                         color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(xaxis_tickangle=-35)
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, theme="streamlit", use_container_width=True)
        
        st.dataframe(df_top[["dept_rank","full_name","department_name","job_role",
                               "job_level","avg_rating","monthly_income"]].rename(columns={
            "dept_rank":"Rank","full_name":"Name","department_name":"Dept",
            "job_role":"Role","job_level":"Level","avg_rating":"Avg Rating",
            "monthly_income":"Monthly Income"}),
            use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Attrition Risk ────────────────────────────────────────
    st.subheader("Attrition Risk Analysis")
    st.caption("SQL: NTILE(4) OVER (ORDER BY risk_score DESC) — scored by satisfaction + overtime + tenure")
    risk, err = _try_load(mgr.get_attrition_risk)
    if err:
        st.info(f"Attrition risk data not available yet: {err}")
    elif risk:
        df_risk = pd.DataFrame(risk)
        
        # Explicitly cast SQL Decimal values to native Python floats for Plotly
        df_risk["risk_score"] = df_risk["risk_score"].astype(float)
        df_risk["avg_satisfaction"] = df_risk["avg_satisfaction"].astype(float)
        df_risk["avg_wlb"] = df_risk["avg_wlb"].astype(float)

        color_map = {"High Risk":"#ef4444","Medium Risk":"#f97316","Low Risk":"#22c55e","Very Low Risk":"#86efac"}
        df_risk["risk_category"] = df_risk["risk_quartile"].map(
            {1:"High Risk",2:"Medium Risk",3:"Low Risk",4:"Very Low Risk"})

        c1, c2 = st.columns(2)
        with c1:
            risk_counts = df_risk["risk_category"].value_counts().reset_index()
            risk_counts.columns = ["category","count"]
            fig = px.pie(risk_counts, names="category", values="count",
                         title="Risk Distribution",
                         color="category", color_discrete_map=color_map)
            st.plotly_chart(fig, theme="streamlit", use_container_width=True)
        with c2:
            fig2 = px.scatter(df_risk.head(500),
                x="avg_satisfaction", y="avg_wlb",
                color="risk_category", size="risk_score",
                hover_data=["full_name","department_name","over_time"],
                title="Risk Scatter: Satisfaction vs Work-Life Balance",
                color_discrete_map=color_map)
            st.plotly_chart(fig2, theme="streamlit", use_container_width=True)

        st.markdown("#### High Risk Employees (Top 20)")
        high_risk = df_risk[df_risk["risk_category"]=="High Risk"].head(20)
        if not high_risk.empty:
            st.dataframe(high_risk[["full_name","department_name","job_role",
                                     "over_time","years_at_company","risk_score"]],
                use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Salary Distribution ───────────────────────────────────
    st.subheader("Salary Distribution by Department")
    st.caption("SQL: PERCENT_RANK() OVER (PARTITION BY department_name ORDER BY monthly_income)")
    sal, err = _try_load(mgr.get_salary_distribution)
    if err:
        st.info(f"Salary distribution not available yet: {err}")
    elif sal:
        df_sal = pd.DataFrame(sal)
        
        # Cast SQL Decimals to floats
        df_sal["monthly_income"] = df_sal["monthly_income"].astype(float)

        fig = px.box(df_sal, x="department_name", y="monthly_income",
                     color="department_name",
                     title="Salary Distribution per Department",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, theme="streamlit", use_container_width=True)

    st.markdown("---")

    # ── SCD2 History Viewer ───────────────────────────────────
    st.subheader("Employee Career History (SCD Type 2)")
    st.caption("View all historical versions of an employee from hr_olap.Dim_Employee")
    emp_id_h = st.number_input("Employee ID", min_value=1, step=1, key="hist_id")
    if st.button("View Career History"):
        hist, err = _try_load(lambda: mgr.get_employee_history(int(emp_id_h)))
        if err:
            st.error(err)
        elif hist:
            df_hist = pd.DataFrame(hist)
            st.dataframe(df_hist[["surrogate_key","department_name","job_role",
                                   "job_level","monthly_income","start_date",
                                   "end_date","is_current","days_in_role"]],
                use_container_width=True, hide_index=True)
            
            fig = px.timeline(
                df_hist.assign(
                    start=pd.to_datetime(df_hist["start_date"]),
                    end=pd.to_datetime(df_hist["end_date"].replace("Present", pd.Timestamp.today().strftime("%Y-%m-%d")))
                ),
                x_start="start", x_end="end",
                y="department_name", color="job_role",
                title=f"Career Timeline — Employee {emp_id_h}"
            )
            st.plotly_chart(fig, theme="streamlit", use_container_width=True)
        else:
            st.info("No history found for this employee.")