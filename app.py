import streamlit as st
import app.core.database as db

st.set_page_config(
    page_title="근무 스케쥴러",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

@st.cache_resource
def _init():
    db.initialize_db()
    return True

_init()

st.markdown("""
<style>
/* ══════════════════════════════════════════════════
   전역 기본값 — 버튼·입력 통일
══════════════════════════════════════════════════ */
.stButton > button {
    min-height: 2.75rem;
    font-weight: 600;
    border-radius: 10px;
    letter-spacing: -0.01em;
    transition: transform 0.1s, opacity 0.1s;
}
.stButton > button:active { transform: scale(0.97); }

.stSelectbox > div > div,
.stNumberInput input,
.stDateInput input,
.stTextInput input {
    min-height: 2.5rem;
    font-size: 1rem !important;
}

div[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 700;
}
div[data-testid="stMetricLabel"] { font-size: 0.9rem; }

/* ══════════════════════════════════════════════════
   사이드바
══════════════════════════════════════════════════ */
[data-testid="stSidebar"] { background-color: #1e293b; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stRadio > label { color: #e2e8f0 !important; }
[data-testid="stSidebar"] hr { border-color: #334155; }
[data-testid="stSidebarNavLink"] { color: #e2e8f0 !important; }
/* 사이드바 라디오 터치 타깃 (옵션 항목에만 적용 — 위젯 자체 라벨("nav")은 제외) */
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
    padding: 0.45rem 0 !important;
    min-height: 2.5rem;
    display: flex;
    align-items: center;
    font-size: 1rem !important;
}

/* ══════════════════════════════════════════════════
   탭
══════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] {
    font-weight: 600;
    padding: 0.6rem 1.1rem;
    border-radius: 8px 8px 0 0;
    font-size: 0.95rem;
}

/* ══════════════════════════════════════════════════
   가로 스크롤 테이블 래퍼
══════════════════════════════════════════════════ */
.scroll-x {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    border-radius: 8px;
    padding-bottom: 4px;
}

/* ══════════════════════════════════════════════════
   모바일  ≤ 640px
══════════════════════════════════════════════════ */
@media (max-width: 640px) {
    /* 본문 여백 최소화 (제목 위 빈 공간 축소 — 상단 고정 툴바에 안 가릴 만큼만 남김) */
    [data-testid="stMainBlockContainer"] {
        padding-top: 4.5rem !important;
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
        padding-bottom: 4rem !important;
        max-width: 100% !important;
    }

    /* 컬럼 세로 쌓기 */
    [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
        gap: 0.35rem !important;
    }
    [data-testid="column"] {
        width: 100% !important;
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }

    /* 버튼 터치 타깃 */
    .stButton > button {
        min-height: 3rem !important;
        font-size: 1rem !important;
    }

    /* 입력 터치 타깃 */
    .stSelectbox > div > div,
    .stNumberInput input,
    .stDateInput input {
        min-height: 3rem !important;
        font-size: 1rem !important;
    }

    /* 헤딩 크기 */
    h2 { font-size: 1.4rem !important; }
    h3 { font-size: 1.2rem !important; }
    h4 { font-size: 1.05rem !important; }

    /* 탭 */
    .stTabs [data-baseweb="tab"] {
        font-size: 0.88rem !important;
        padding: 0.55rem 0.7rem !important;
    }

    /* 메트릭 */
    div[data-testid="stMetricValue"] { font-size: 2rem !important; }

    /* Plotly 차트 */
    .js-plotly-plot { width: 100% !important; }

    /* 사이드바 토글 버튼 크게 */
    [data-testid="collapsedControl"] {
        width: 2.5rem !important;
        height: 2.5rem !important;
    }
}
</style>
""", unsafe_allow_html=True)

NAV_ITEMS = [
    ("🏠  대시보드",      "dashboard"),
    ("📅  월간 캘린더",   "monthly"),
    ("📋  주간 근무표",   "weekly"),
    # ("🔔  알람 설정",     "alarms"),  # 임시 비활성화 (추후 재사용 예정, 코드는 유지)
    ("📂  엑셀 가져오기", "import"),
    ("⚙️  설정",          "settings"),
]

with st.sidebar:
    st.markdown("## 근무 스케쥴러")
    st.caption("Schedule Manager")
    st.divider()

    labels   = [lbl for lbl, _ in NAV_ITEMS]
    page_map = {lbl: pid for lbl, pid in NAV_ITEMS}

    selected = st.radio("nav", labels, label_visibility="collapsed", key="main_nav")

    st.divider()
    st.markdown(
        '<p style="color:#475569; font-size:11px; text-align:center; margin:0;">'
        'Developed by 박준형 · v1.0</p>',
        unsafe_allow_html=True,
    )

page = page_map[selected]

if page == "dashboard":
    from app.web.pages.dashboard import render
elif page == "monthly":
    from app.web.pages.monthly import render
elif page == "weekly":
    from app.web.pages.weekly import render
elif page == "alarms":
    from app.web.pages.alarms import render
elif page == "import":
    from app.web.pages.import_page import render
else:
    from app.web.pages.settings_page import render

render()
