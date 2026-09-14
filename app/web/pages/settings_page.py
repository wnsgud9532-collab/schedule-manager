import streamlit as st
import app.core.database as db
from app.core.schedule_manager import get_manager


def render():
    st.markdown("## ⚙️ 설정")

    # ── App info ──────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("### 앱 정보")
        st.markdown(
            "**근무 스케쥴러 v1.0.0**  \n"
            "Python + Streamlit  \n"
            "Developed by 박준형"
        )

    # ── Alarm defaults ────────────────────────────────────────────────
    st.divider()
    with st.container(border=True):
        st.markdown("### 알람 기본값")

        minutes = st.number_input(
            "근무 시작 전 기본 알림 시간 (분)",
            min_value=1,
            max_value=120,
            value=int(db.get_setting("alarm_minutes_before", "10")),
            step=1,
            key="settings_alarm_min",
        )
        if st.button("저장", type="primary", key="settings_save"):
            db.set_setting("alarm_minutes_before", str(minutes))
            st.success("저장 완료!")

    # ── DB stats ──────────────────────────────────────────────────────
    st.divider()
    with st.container(border=True):
        st.markdown("### 데이터베이스 현황")
        st.caption("저장 경로: `data/schedule.db`")

        mgr       = get_manager()
        employees = mgr.get_employees()
        st.metric("등록된 직원 수", f"{len(employees)}명")
