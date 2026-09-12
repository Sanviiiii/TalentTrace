"""
streamlit_app/app.py — Main entry point
Run: streamlit run streamlit_app/app.py
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="HR Analytics Platform",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #1e293b; }
[data-testid="stSidebar"] * { color: #f1f5f9 !important; }
.metric-card {
    background: linear-gradient(135deg,#1e40af,#3b82f6);
    border-radius:12px; padding:20px; color:white;
    text-align:center; margin:5px;
}
.metric-value { font-size:2rem; font-weight:700; }
.metric-label { font-size:0.85rem; opacity:0.85; margin-top:4px; }
.success-box {
    background:#dcfce7; border-left:4px solid #16a34a;
    padding:12px 16px; border-radius:6px; margin:10px 0;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 👥 HR Analytics")
    st.markdown("---")
    page = st.radio("Navigate",[
        "🏠 Home",
        "➕ Onboard Employee",
        "📁 Projects",
        "📝 Performance Review",
        "📊 Analytics Dashboard",
    ], label_visibility="collapsed")
    st.markdown("---")
    st.caption("Enterprise HR Analytics v1.0")

if   page == "🏠 Home":              from streamlit_app.pages import home;      home.render()
elif page == "➕ Onboard Employee":  from streamlit_app.pages import onboard;   onboard.render()
elif page == "📁 Projects":          from streamlit_app.pages import projects;   projects.render()
elif page == "📝 Performance Review":from streamlit_app.pages import reviews;    reviews.render()
elif page == "📊 Analytics Dashboard":from streamlit_app.pages import dashboard; dashboard.render()
