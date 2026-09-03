import calendar
from datetime import date
import streamlit as st
import app.core.database as db
from app.core.schedule_manager import get_manager
from app.models.schedule import Shift

_GROUP_STYLES = {
    "morning":   {"hours": {6, 7, 8},    "color": "#f59e0b", "label": "오전조"},
    "afternoon": {"hours": {13, 15, 16}, "color": "#0ea5e9", "label": "오후조"},
    "night":     {"hours": {22},         "color": "#6366f1", "label": "야간조"},
}
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


def _group_color(shift: Shift) -> str:
    h = shift.start_time.hour
    for g in _GROUP_STYLES.values():
        if h in g["hours"]:
            return g["color"]
    return "#94a3b8"


def _personal_html(year: int, month: int, emp_name: str, day_map: dict):
    cal   = calendar.monthcalendar(year, month)
    today = date.today()
    work_days, off_days, total_h = 0, 0, 0.0

    rows = (
        '<div class="scroll-x">'
        '<table style="width:100%;border-collapse:collapse;table-layout:fixed;'
        'min-width:420px;">'
    )
    rows += "<tr>"
    for i, wd in enumerate(WEEKDAYS):
        color = "#ef4444" if i == 6 else "#3b82f6" if i == 5 else "#374151"
        rows += (
            f'<th style="padding:8px 4px;text-align:center;background:#f1f5f9;'
            f'border:1px solid #e2e8f0;color:{color};font-size:13px;">{wd}</th>'
        )
    rows += "</tr>"

    for week in cal:
        rows += "<tr>"
        for i, day in enumerate(week):
            if day == 0:
                rows += '<td style="border:1px solid #e2e8f0;height:86px;background:#fafafa;"></td>'
                continue
            d      = date(year, month, day)
            shifts = [s for s in day_map.get(day, []) if s.employee_name == emp_name]
            is_td  = d == today
            is_sat = i == 5
            is_sun = i == 6

            bg      = "#dbeafe" if is_td else "white"
            day_col = "#1d4ed8" if is_td else "#ef4444" if is_sun else "#3b82f6" if is_sat else "#374151"
            rows += (
                f'<td style="border:1px solid #e2e8f0;padding:5px;height:86px;'
                f'vertical-align:top;background:{bg};">'
                f'<div style="font-weight:700;font-size:13px;color:{day_col};margin-bottom:4px;">{day}</div>'
            )
            if shifts:
                s     = shifts[0]
                color = _group_color(s)
                rows += (
                    f'<div style="background:{color};color:white;border-radius:5px;'
                    f'padding:3px 5px;font-size:11px;line-height:1.5;font-weight:600;">'
                    f'{s.time_range_str()}</div>'
                )
                work_days += 1
                total_h   += s.duration_hours()
            else:
                rows += '<div style="color:#94a3b8;font-size:11px;padding-top:2px;">휴무</div>'
                off_days += 1
            rows += "</td>"
        rows += "</tr>"

    rows += "</table></div>"
    return rows, work_days, off_days, total_h


def _all_html(year: int, month: int, day_map: dict):
    cal   = calendar.monthcalendar(year, month)
    today = date.today()

    rows = (
        '<div class="scroll-x">'
        '<table style="width:100%;border-collapse:collapse;table-layout:fixed;'
        'min-width:420px;">'
    )
    rows += "<tr>"
    for i, wd in enumerate(WEEKDAYS):
        color = "#ef4444" if i == 6 else "#3b82f6" if i == 5 else "#374151"
        rows += (
            f'<th style="padding:8px 4px;text-align:center;background:#f1f5f9;'
            f'border:1px solid #e2e8f0;color:{color};font-size:13px;">{wd}</th>'
        )
    rows += "</tr>"

    for week in cal:
        rows += "<tr>"
        for i, day in enumerate(week):
            if day == 0:
                rows += '<td style="border:1px solid #e2e8f0;height:96px;background:#fafafa;"></td>'
                continue
            d      = date(year, month, day)
            shifts = day_map.get(day, [])
            is_td  = d == today
            is_sat = i == 5
            is_sun = i == 6

            bg      = "#dbeafe" if is_td else "white"
            day_col = "#1d4ed8" if is_td else "#ef4444" if is_sun else "#3b82f6" if is_sat else "#374151"

            rows += (
                f'<td style="border:1px solid #e2e8f0;padding:4px;height:96px;'
                f'vertical-align:top;background:{bg};overflow:hidden;">'
                f'<div style="font-weight:700;font-size:13px;color:{day_col};margin-bottom:3px;">'
                f'{day} <span style="font-weight:400;color:#94a3b8;font-size:11px;">({len(shifts)})</span></div>'
            )
            for s in shifts[:4]:
                color = _group_color(s)
                rows += (
                    f'<div style="background:{color};color:white;border-radius:3px;'
                    f'padding:2px 4px;font-size:10px;margin:1px 0;white-space:nowrap;'
                    f'overflow:hidden;text-overflow:ellipsis;font-weight:600;">'
                    f'{s.employee_name}</div>'
                )
            if len(shifts) > 4:
                rows += (
                    f'<div style="color:#64748b;font-size:10px;margin-top:1px;">'
                    f'+{len(shifts)-4}명 더</div>'
                )
            rows += "</td>"
        rows += "</tr>"

    rows += "</table></div>"
    return rows


def render():
    st.markdown("## 📅 월간 캘린더")

    today = date.today()
    if "monthly_year"  not in st.session_state:
        st.session_state.monthly_year  = today.year
    if "monthly_month" not in st.session_state:
        st.session_state.monthly_month = today.month

    # ── 월 내비게이션 ────────────────────────────────────────────────
    n1, n2, n3, n4 = st.columns([1.4, 1, 4, 1.4])
    with n1:
        if st.button("← 이전 달", use_container_width=True, key="month_prev"):
            m, y = st.session_state.monthly_month - 1, st.session_state.monthly_year
            if m < 1: m, y = 12, y - 1
            st.session_state.monthly_month, st.session_state.monthly_year = m, y
    with n2:
        if st.button("오늘", use_container_width=True, key="month_today"):
            st.session_state.monthly_year, st.session_state.monthly_month = today.year, today.month
    with n3:
        yr, mo = st.session_state.monthly_year, st.session_state.monthly_month
        st.markdown(
            f"<h3 style='margin:0;padding-top:6px;'>{yr}년 {mo}월</h3>",
            unsafe_allow_html=True,
        )
    with n4:
        if st.button("다음 달 →", use_container_width=True, key="month_next"):
            m, y = st.session_state.monthly_month + 1, st.session_state.monthly_year
            if m > 12: m, y = 1, y + 1
            st.session_state.monthly_month, st.session_state.monthly_year = m, y

    year  = st.session_state.monthly_year
    month = st.session_state.monthly_month
    mgr   = get_manager()
    day_map = mgr.get_monthly_by_day(year, month)

    tab1, tab2 = st.tabs(["👤 개인 근무표", "📋 전체 근무표"])

    # ── 탭1: 개인 근무표 ─────────────────────────────────────────────
    with tab1:
        employees = mgr.get_employees()
        if not employees:
            st.info("등록된 직원이 없습니다.")
        else:
            emp_names = [e.name for e in employees]
            saved     = db.get_setting("personal_calendar_pinned_employee", "")
            default   = emp_names.index(saved) if saved in emp_names else 0

            emp = st.selectbox("직원 선택", emp_names, index=default, key="monthly_personal_emp")
            db.set_setting("personal_calendar_pinned_employee", emp)

            html, work_days, off_days, total_h = _personal_html(year, month, emp, day_map)
            st.markdown(html, unsafe_allow_html=True)

            st.divider()
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("근무일",      f"{work_days}일")
            sc2.metric("휴무일",      f"{off_days}일")
            sc3.metric("총 근무시간", f"{total_h:.0f}시간")

    # ── 탭2: 전체 근무표 ─────────────────────────────────────────────
    with tab2:
        st.markdown(_all_html(year, month, day_map), unsafe_allow_html=True)
