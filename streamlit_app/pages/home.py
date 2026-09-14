"""streamlit_app/pages/home.py"""
import streamlit as st

def render():
    st.markdown("""
    <style>
    @keyframes slideUp { 0% { opacity: 0; transform: translateY(20px); } 100% { opacity: 1; transform: translateY(0); } }
    
    .animated-subtitle { font-size: 1.2rem; color: var(--text-color); opacity: 0.7; margin-bottom: 30px; animation: slideUp 0.6s ease; }
    
    .animated-card {
        background-color: var(--secondary-background-color);
        border-radius: 12px; padding: 24px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(128,128,128,0.2);
        text-align: center; transition: all 0.3s ease;
        animation: slideUp 0.8s ease;
    }
    .animated-card:hover { transform: translateY(-5px); border-color: var(--primary-color); }
    .val-text { font-size: 2.8rem; font-weight: 800; color: var(--text-color) !important; line-height: 1.1; }
    .lbl-text { font-size: 0.9rem; color: var(--text-color) !important; opacity: 0.8; text-transform: uppercase; margin-top: 8px;}
    
    .schema-box {
        background-color: var(--secondary-background-color);
        padding: 25px; border-radius: 12px;
        border-left: 5px solid var(--primary-color);
        border-top: 1px solid rgba(128,128,128,0.2);
        border-right: 1px solid rgba(128,128,128,0.2);
        border-bottom: 1px solid rgba(128,128,128,0.2);
        animation: slideUp 1s ease;
    }
    .schema-box h3 { margin-top:0; color: var(--text-color) !important; font-size: 1.5rem; }
    .schema-box ul { color: var(--text-color) !important; opacity: 0.85; line-height:1.8; font-size:1.05rem; }
    </style>
    """, unsafe_allow_html=True)

    # Restored standard title
    st.title("TalentTrace Analytics")
    st.markdown("<div class='animated-subtitle'>Welcome to the centralized HR Data Warehouse System</div>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    metrics = [("100K+","Employee Records"), ("2","MySQL Schemas"), ("SCD2","Historical Tracking"), ("5","ETL Procedures")]
    
    for col, (val, label) in zip([col1, col2, col3, col4], metrics):
        with col:
            st.markdown(f"""
            <div class='animated-card'>
                <div class='val-text'>{val}</div>
                <div class='lbl-text'>{label}</div>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div class='schema-box'>
            <h3>OLTP Schema (<code>hr_oltp</code>)</h3>
            <ul>
                <li><b>Departments</b> — master dept list</li>
                <li><b>Employees</b> — 100K records</li>
                <li><b>Projects</b> — company projects</li>
                <li><b>Project_Assignments</b> — bridge table</li>
                <li><b>Performance_Reviews</b> — reviews</li>
                <li><b>Salary_History</b> — audit trail</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class='schema-box' style='border-left-color: #10b981;'>
            <h3>OLAP Star Schema (<code>hr_olap</code>)</h3>
            <ul>
                <li><b>Fact_PerformanceReviews</b> — central fact</li>
                <li><b>Dim_Employee</b> — SCD Type 2</li>
                <li><b>Dim_Department</b> — dept dimension</li>
                <li><b>Dim_Project</b> — project dimension</li>
                <li><b>Dim_Date</b> — calendar 2015–2030</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)