from datetime import date, datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components
import app.core.database as db
from app.core.schedule_manager import get_manager

SHIFT_GROUPS = {
    "오전조": {"hours": {6, 7, 8},    "emoji": "🌅", "color": "#f59e0b"},
    "오후조": {"hours": {13, 15, 16}, "emoji": "☀️", "color": "#0ea5e9"},
    "야간조": {"hours": {22},         "emoji": "🌙", "color": "#6366f1"},
}
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


def _get_group(shift) -> str:
    for gname, ginfo in SHIFT_GROUPS.items():
        if shift.start_time.hour in ginfo["hours"]:
            return gname
    return "기타"


def _get_status(shift, now: datetime) -> tuple:
    start_dt = datetime.combine(shift.date, shift.start_time)
    end_dt   = datetime.combine(shift.date, shift.end_time)
    if shift.end_time <= shift.start_time:
        end_dt += timedelta(days=1)
    if now < start_dt:
        return "⏰ 출근 예정", "#d97706"
    elif now < end_dt:
        return "🟢 근무 중", "#16a34a"
    else:
        return "🏠 퇴근", "#94a3b8"


def render():
    # ── 자동 새로고침 (30초) ─────────────────────────────────────────
    components.html(
        "<script>setTimeout(()=>window.parent.location.reload(),30000)</script>",
        height=0,
    )

    now   = datetime.now()
    today = date.today()
    wd    = WEEKDAYS[today.weekday()]

    # ── 데이터 ──────────────────────────────────────────────────────
    mgr       = get_manager()
    shifts    = mgr.get_shifts_by_date(today)
    employees = mgr.get_employees()

    grouped: dict = {g: [] for g in SHIFT_GROUPS}
    for s in shifts:
        g = _get_group(s)
        grouped.setdefault(g, []).append(s)

    휴무_count = max(0, len(employees) - len(shifts))

    # ── 헤더 (타이틀 + 갱신 시각) ────────────────────────────────────
    st.markdown(
        f"""<div style="display:flex;justify-content:space-between;align-items:center;
        margin-bottom:6px;">
        <span style="font-size:16px;font-weight:700;color:#0f172a;">
          📋 출퇴근 현황 — {today.year}년 {today.month}월 {today.day}일 ({wd})
        </span>
        <span style="font-size:11px;color:#94a3b8;">🔄 마지막 갱신 {now.strftime('%H:%M:%S')}</span>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── 조별 통계 카드 ────────────────────────────────────────────────
    sc1, sc2, sc3, sc4 = st.columns(4)
    for col, (label, cnt, color) in zip(
        [sc1, sc2, sc3, sc4],
        [
            ("🌅 오전조", len(grouped["오전조"]), "#f59e0b"),
            ("☀️ 오후조", len(grouped["오후조"]), "#0ea5e9"),
            ("🌙 야간조", len(grouped["야간조"]), "#6366f1"),
            ("😴 휴무",   휴무_count,              "#94a3b8"),
        ],
    ):
        with col:
            st.markdown(
                f'<div style="background:{color}15;border:1px solid {color}45;'
                f'border-radius:8px;padding:5px 8px;text-align:center;margin-bottom:4px;">'
                f'<div style="font-size:11px;color:{color};font-weight:600;">{label}</div>'
                f'<div style="font-size:22px;font-weight:700;color:#1e293b;line-height:1.3;">{cnt}명</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── 미출근만 보기 토글 ────────────────────────────────────────────
    only_absent = st.toggle("📍 미출근만 보기 (현재 근무 시간대)", value=False, key="only_absent")

    # ── 근무자 행 생성 ────────────────────────────────────────────────
    rows = []
    for gname, ginfo in SHIFT_GROUPS.items():
        for s in sorted(grouped.get(gname, []), key=lambda x: x.start_time):
            is_active = s.is_active_at(now)
            if only_absent and not is_active:
                continue
            status_text, status_color = _get_status(s, now)
            rows.append((gname, ginfo, s, is_active, status_text, status_color))

    # ── HTML 컴팩트 테이블 ────────────────────────────────────────────
    tbl = (
        '<table style="width:100%;border-collapse:collapse;font-size:12.5px;">'
        '<thead><tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">'
        '<th style="padding:5px 10px;text-align:left;color:#64748b;font-weight:600;width:13%;">조</th>'
        '<th style="padding:5px 10px;text-align:left;color:#64748b;font-weight:600;width:22%;">이름</th>'
        '<th style="padding:5px 10px;text-align:left;color:#64748b;font-weight:600;width:30%;">근무시간</th>'
        '<th style="padding:5px 10px;text-align:left;color:#64748b;font-weight:600;width:35%;">상태</th>'
        '</tr></thead><tbody>'
    )

    prev_group = None
    for gname, ginfo, s, is_active, status_text, status_color in rows:
        if gname != prev_group:
            tbl += (
                f'<tr style="background:{ginfo["color"]}12;">'
                f'<td colspan="4" style="padding:4px 10px;font-size:11px;font-weight:700;'
                f'color:{ginfo["color"]};letter-spacing:0.04em;">'
                f'{ginfo["emoji"]} {gname}&nbsp;&nbsp;'
                f'<span style="font-weight:400;color:#94a3b8;">{len(grouped[gname])}명</span>'
                f'</td></tr>'
            )
            prev_group = gname

        row_bg  = "#fff1f2" if is_active else "#ffffff"
        row_bdr = "#fecdd3" if is_active else "#f1f5f9"
        absent_dot = (
            '<span style="color:#ef4444;font-size:10px;margin-left:4px;">●</span>'
            if is_active else ""
        )
        tbl += (
            f'<tr style="background:{row_bg};border-bottom:1px solid {row_bdr};">'
            f'<td style="padding:4px 10px;color:{ginfo["color"]};font-size:11px;font-weight:600;">'
            f'{ginfo["emoji"]}</td>'
            f'<td style="padding:4px 10px;font-weight:600;color:#0f172a;">'
            f'{s.employee_name}{absent_dot}</td>'
            f'<td style="padding:4px 10px;color:#475569;font-family:monospace;font-size:12px;">'
            f'{s.time_range_str()}</td>'
            f'<td style="padding:4px 10px;color:{status_color};font-weight:600;font-size:11.5px;">'
            f'{status_text}</td>'
            f'</tr>'
        )

    tbl += "</tbody></table>"

    if rows:
        st.markdown(tbl, unsafe_allow_html=True)
    else:
        st.info("현재 근무 중인 직원이 없습니다." if only_absent else "오늘 근무 데이터가 없습니다.")
