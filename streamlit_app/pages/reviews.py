"""streamlit_app/pages/reviews.py — Performance review submission"""
import streamlit as st
import pandas as pd
from datetime import date
from backend.managers import ReviewManager, EmployeeManager
from backend.models import Review

def render():
    st.title("📝 Performance Reviews")
    st.markdown("---")
    tab1, tab2 = st.tabs(["➕ Submit Review", "📋 View Reviews"])

    # ── TAB 1: Submit Review ──────────────────────────────────
    with tab1:
        st.subheader("Submit a Performance Review")
        st.info("Ratings are on a scale of 1–4: 1=Poor, 2=Below Average, 3=Excellent, 4=Outstanding")
        with st.form("review_form"):
            c1,c2 = st.columns(2)
            with c1:
                emp_id      = st.number_input("Employee ID*", min_value=1, step=1)
                review_year = st.number_input("Review Year*", min_value=2020, max_value=2030, value=date.today().year)
                reviewer_id = st.number_input("Reviewer (Manager) ID", min_value=0, step=1, value=0)
                perf_rating = st.slider("Performance Rating*", 1, 4, 3)
                job_sat     = st.slider("Job Satisfaction", 1, 4, 3)
                env_sat     = st.slider("Environment Satisfaction", 1, 4, 3)
            with c2:
                review_date = st.date_input("Review Date*", value=date.today())
                quarter     = st.selectbox("Quarter*", [1,2,3,4])
                rel_sat     = st.slider("Relationship Satisfaction", 1, 4, 3)
                wlb         = st.slider("Work-Life Balance", 1, 4, 3)
                involvement = st.slider("Job Involvement", 1, 4, 3)
            comments = st.text_area("Comments / Notes", height=100)

            # Live preview of overall score
            overall = round((perf_rating+job_sat+env_sat+rel_sat+wlb+involvement)/6, 2)
            label   = {1:"Poor",2:"Below Average",3:"Excellent",4:"Outstanding"}.get(perf_rating,"—")
            st.markdown(f"**Predicted Overall Score: `{overall}/4.0`  |  Rating: `{label}`**")

            submitted = st.form_submit_button("📝 Submit Review", use_container_width=True, type="primary")
            if submitted:
                try:
                    review = Review(
                        employee_id=int(emp_id),
                        review_date=review_date,
                        review_year=int(review_year),
                        review_quarter=int(quarter),
                        performance_rating=int(perf_rating),
                        job_satisfaction=int(job_sat),
                        environment_satisfaction=int(env_sat),
                        relationship_satisfaction=int(rel_sat),
                        work_life_balance=int(wlb),
                        job_involvement=int(involvement),
                        reviewer_id=int(reviewer_id) if reviewer_id > 0 else None,
                        comments=comments
                    )
                    errors = review.validate()
                    if errors:
                        for e in errors: st.error(e)
                    else:
                        mgr = ReviewManager()
                        rid = mgr.submit(review)
                        st.success(f"✅ Review submitted! Review ID: **{rid}** | Score: **{overall}/4.0**")
                except Exception as e:
                    st.error(str(e))

    # ── TAB 2: View Reviews ───────────────────────────────────
    with tab2:
        st.subheader("Employee Review History")
        emp_id_v = st.number_input("Enter Employee ID to view reviews", min_value=1, step=1, key="view_emp")
        if st.button("🔍 Load Reviews"):
            try:
                mgr     = ReviewManager()
                reviews = mgr.get_by_employee(int(emp_id_v))
                if reviews:
                    df = pd.DataFrame(reviews)
                    st.dataframe(df[["review_id","review_year","review_quarter","performance_rating",
                                     "job_satisfaction","work_life_balance","environment_satisfaction",
                                     "review_date","reviewer_name"]].rename(columns={
                        "performance_rating":"Perf","job_satisfaction":"Job Sat",
                        "work_life_balance":"WLB","environment_satisfaction":"Env Sat"
                    }), use_container_width=True, hide_index=True)

                    import plotly.express as px
                    fig = px.line(df.sort_values("review_year"),
                        x="review_year", y="performance_rating",
                        title=f"Performance Trend — Employee {emp_id_v}",
                        markers=True, color_discrete_sequence=["#3b82f6"])
                    fig.update_layout(yaxis=dict(range=[0,5]), template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"No reviews found for Employee {emp_id_v}")
            except Exception as e:
                st.error(str(e))
