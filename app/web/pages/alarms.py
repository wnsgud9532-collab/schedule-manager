from datetime import date, datetime
import streamlit as st
import app.core.database as db
from app.core.schedule_manager import get_manager
from app.core.timeutil import now_kst, today_kst
from app.core import notifier


def render():
    st.markdown("## 🔔 알람 설정")

    # ── 설정 ────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("### ⏱ 알림 시간 설정")

        minutes = st.number_input(
            "근무 시작 몇 분 전에 알림을 받을까요?",
            min_value=1, max_value=120,
            value=int(db.get_setting("alarm_minutes_before", "10")),
            step=1,
            key="alarm_minutes",
        )

        # 버튼 세로 배치 — 모바일에서 터치하기 편하도록
        if st.button("💾  설정 저장", type="primary",
                     use_container_width=True, key="alarm_save"):
            db.set_setting("alarm_minutes_before", str(minutes))
            st.success(f"저장 완료! ({minutes}분 전 알림)")

        if st.button("📅  오늘 근무 알람 등록",
                     use_container_width=True, key="alarm_today"):
            notifier.schedule_all_today_alarms(minutes)
            st.success(f"오늘 알람 등록 완료! ({minutes}분 전)")

        if st.button("🔔  테스트 알림 전송",
                     use_container_width=True, key="alarm_test"):
            notifier.send_test_notification()
            st.info("테스트 알림을 전송했습니다.")

    st.info(
        "💡 알람을 등록하면 근무 시작 설정 시간 전에 Windows 알림이 전송됩니다.\n"
        "앱(웹 서버)이 실행 중이어야 알람이 동작합니다."
    )

    # ── 오늘 스케쥴 ─────────────────────────────────────────────────
    st.divider()
    st.markdown(f"### 📅 오늘 ({today_kst().strftime('%m월 %d일')}) 스케쥴")

    mgr    = get_manager()
    shifts = mgr.get_todays_shifts()
    now    = now_kst()

    if not shifts:
        st.caption("오늘 등록된 스케쥴이 없습니다.")
    else:
        for s in sorted(shifts, key=lambda x: x.start_time):
            future = datetime.combine(s.date, s.start_time) > now
            bg     = "#f0fdf4" if future else "#f8fafc"
            icon   = "🔔" if future else "✓"
            t_col  = "#374151" if future else "#94a3b8"

            st.markdown(
                f'<div style="background:{bg}; border-radius:10px; '
                f'padding:14px 16px; margin:6px 0;">'
                f'<div style="display:flex; align-items:center; gap:12px;">'
                f'<span style="font-size:22px;">{icon}</span>'
                f'<div style="flex:1;">'
                f'<div style="font-weight:700; font-size:16px; color:#0f172a;">'
                f'{s.employee_name}</div>'
                f'<div style="font-size:14px; color:{t_col}; margin-top:2px;">'
                f'{s.time_range_str()}</div>'
                f'</div></div></div>',
                unsafe_allow_html=True,
            )
