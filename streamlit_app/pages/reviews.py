"""streamlit_app/pages/reviews.py"""
import streamlit as st
import pandas as pd
from datetime import date
from backend.managers import ReviewManager
from backend.models import Review

def render():
    st.title("Performance Reviews")
    st.markdown("---")
    tab1, tab2 = st.tabs(["Submit Review", "View Reviews"])

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

            overall = round((perf_rating+job_sat+env_sat+rel_sat+wlb+involvement)/6, 2)
            label   = {1:"Poor",2:"Below Average",3:"Excellent",4:"Outstanding"}.get(perf_rating,"—")
            st.markdown(f"**Predicted Overall Score: `{overall}/4.0`  |  Rating: `{label}`**")

            submitted = st.form_submit_button("Submit Review", use_container_width=True, type="primary")
            if submitted:
                try:
                    review = Review(
                        employee_id=int(emp_id), review_date=review_date, review_year=int(review_year),
                        review_quarter=int(quarter), performance_rating=int(perf_rating),
                        job_satisfaction=int(job_sat), environment_satisfaction=int(env_sat),
                        relationship_satisfaction=int(rel_sat), work_life_balance=int(wlb),
                        job_involvement=int(involvement), reviewer_id=int(reviewer_id) if reviewer_id > 0 else None,
                        comments=comments
                    )
                    errors = review.validate()
                    if errors:
                        for e in errors: st.error(e)
                    else:
                        mgr = ReviewManager()
                        rid = mgr.submit(review)
                        st.markdown(f"<div class='success-box'>Review submitted! ID: <b>{rid}</b> | Score: <b>{overall}/4.0</b></div>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(str(e))

    with tab2:
        st.subheader("Employee Review History")
        emp_id_v = st.number_input("Enter Employee ID", min_value=1, step=1, key="view_emp")
        if st.button("Load Reviews"):
            try:
                mgr     = ReviewManager()
                reviews = mgr.get_by_employee(int(emp_id_v))
                if reviews:
                    df = pd.DataFrame(reviews)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    import plotly.express as px
                    fig = px.line(df.sort_values("review_year"), x="review_year", y="performance_rating", markers=True)
                    st.plotly_chart(fig, theme="streamlit", use_container_width=True)
                else:
                    st.info("No reviews found.")
            except Exception as e:
                st.error(str(e))