"""streamlit_app/app.py — Main entry point"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="TalentTrace",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>

/* Simply hide the duplicate auto-generated sidebar navigation */
[data-testid="stSidebarNav"] { display: none !important; }

/* Global Notifications */
.success-box { background: rgba(34, 197, 94, 0.1); border-left: 4px solid #22c55e; padding: 12px; border-radius: 4px; color: var(--text-color); margin-bottom: 15px; }
.warning-box { background: rgba(249, 115, 22, 0.1); border-left: 4px solid #f97316; padding: 12px; border-radius: 4px; color: var(--text-color); margin-bottom: 15px; }
/* ── SUBTLE GLOBAL ANIMATIONS ── */
/* 1. Page Load Fade & Slide */
@keyframes fadeInSlideUp {
    0% { opacity: 0; transform: translateY(15px); }
    100% { opacity: 1; transform: translateY(0); }
}
[data-testid="stMainBlockContainer"] {
    animation: fadeInSlideUp 0.6s ease-out forwards;
}

/* 2. Button Hover Lift */
button[data-baseweb="button"] {
    transition: all 0.2s ease-in-out !important;
}
button[data-baseweb="button"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15) !important;
    filter: brightness(1.05);
}
button[data-baseweb="button"]:active {
    transform: translateY(0px);
}

/* 3. Input Field Focus Glow */
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within {
    transition: box-shadow 0.2s ease-in-out;
    box-shadow: 0 0 8px rgba(59, 130, 246, 0.4) !important;
}

/* 4. Tab Hover Effect */
[data-testid="stTabs"] button:hover {
    color: var(--primary-color) !important;
    transition: color 0.2s ease-in-out;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<h2 style='text-align: center; margin-bottom: 20px;'>TalentTrace</h2>", unsafe_allow_html=True)
    
    # Restored native radio buttons
    page = st.radio("Navigate", [
        "Home",
        "Onboard Employee",
        "Projects",
        "Performance Review",
        "Analytics Dashboard",
    ], label_visibility="collapsed")
    
    st.markdown("---")
    st.caption("Enterprise HR Analytics v1.0")

# Routing
if page == "Home":                from streamlit_app.pages import home;      home.render()
elif page == "Onboard Employee":  from streamlit_app.pages import onboard;   onboard.render()
elif page == "Projects":          from streamlit_app.pages import projects;  projects.render()
elif page == "Performance Review":from streamlit_app.pages import reviews;   reviews.render()
elif page == "Analytics Dashboard":from streamlit_app.pages import dashboard;dashboard.render()