import streamlit as st
import app.core.database as db

st.set_page_config(
    page_title="근무 스케쥴러",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_resource
def _init():
    db.initialize_db()
    return True

_init()

st.markdown("""
<style>
[data-testid="stSidebar"] {
    background-color: #1e293b;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] .stRadio > label {
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] hr {
    border-color: #334155;
}
[data-testid="stSidebarNavLink"] {
    color: #e2e8f0 !important;
}
div[data-testid="stMetricValue"] {
    font-size: 1.6rem;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

NAV_ITEMS = [
    ("🏠  대시보드",    "dashboard"),
    ("📅  월간 캘린더", "monthly"),
    ("🔔  알람 설정",   "alarms"),
    ("📂  엑셀 가져오기", "import"),
    ("⚙️  설정",        "settings"),
]

with st.sidebar:
    st.markdown("## 근무 스케쥴러")
    st.caption("Schedule Manager")
    st.divider()

    labels  = [lbl for lbl, _ in NAV_ITEMS]
    page_map = {lbl: pid for lbl, pid in NAV_ITEMS}

    selected = st.radio("nav", labels, label_visibility="collapsed", key="main_nav")

    st.divider()
    st.caption("v1.0.0")
    st.caption("Developed by 박준형")

page = page_map[selected]

if page == "dashboard":
    from app.web.pages.dashboard import render
elif page == "monthly":
    from app.web.pages.monthly import render
elif page == "alarms":
    from app.web.pages.alarms import render
elif page == "import":
    from app.web.pages.import_page import render
else:
    from app.web.pages.settings_page import render

render()
