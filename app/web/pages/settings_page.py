import streamlit as st
import app.core.database as db
import app.core.cloud_backup as cloud_backup
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
        st.caption("저장 경로: `data/schedule.db` (앱 재시작 시 초기화됨 → GitHub Gist에 자동 백업/복원)")

        mgr       = get_manager()
        employees = mgr.get_employees()
        st.metric("등록된 직원 수", f"{len(employees)}명")

    # ── Cloud backup ──────────────────────────────────────────────────
    st.divider()
    with st.container(border=True):
        st.markdown("### ☁️ 자동 백업 (GitHub Gist)")
        st.caption(
            "엑셀로 가져온 근무 데이터는 저장/수정할 때마다 비공개 GitHub Gist에 자동 백업되고, "
            "앱이 잠들었다 깨어나거나 재배포되어 로컬 데이터가 비어있으면 자동으로 복원됩니다."
        )
        if st.button("지금 수동 백업", key="settings_manual_backup"):
            try:
                cloud_backup.save_backup(db.export_snapshot())
                st.success("백업 완료!")
            except Exception as e:
                st.error(f"백업 실패: {e}  \n(github_backup_token이 Secrets에 등록되어 있는지 확인하세요)")
