from datetime import date, timedelta
import streamlit as st
from app.core import sheets_client

WEEKDAYS   = ["월", "화", "수", "목", "금", "토", "일"]
TIME_SLOTS = [6, 7, 8, 13, 15, 16, 22]

_HEADER_BG   = "#e0f2fe"   # 연한 하늘색
_HEADER_TEXT = "#1e293b"
_SAT_TEXT    = "#7c3aed"   # 보라
_SUN_TEXT    = "#dc2626"   # 빨강
_TIME_BG     = "#1e3a8a"   # 시간대 컬럼 진한 남색 배경
_TIME_TEXT   = "#ffffff"
_BORDER      = "#d1d5db"   # 연한 회색

# 시간대별 행 배경 (출퇴근 현황 페이지의 오전조/오후조/야간조 색상과 동일 계열)
_AM_ROW_BG    = "#FFF3E0"   # 오전 (06:00, 07:00, 08:00) - 연한 주황
_PM_ROW_BG    = "#E3F2FD"   # 오후 (13:00, 15:00, 16:00) - 연한 파랑
_NIGHT_ROW_BG = "#F3E5F5"   # 야간 (22:00) - 연한 보라

_ROW_BG_BY_HOUR = {
    6: _AM_ROW_BG, 7: _AM_ROW_BG, 8: _AM_ROW_BG,
    13: _PM_ROW_BG, 15: _PM_ROW_BG, 16: _PM_ROW_BG,
    22: _NIGHT_ROW_BG,
}


def _week_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _weekday_color(d: date) -> str:
    if d.weekday() == 5:
        return _SAT_TEXT
    if d.weekday() == 6:
        return _SUN_TEXT
    return _HEADER_TEXT


@st.cache_data(ttl=60, show_spinner=False)
def _load_week(week_start: date) -> dict:
    return sheets_client.fetch_weekly_schedule(week_start)


# ── 주간 표 HTML ─────────────────────────────────────────────────────────
def _build_grid(days: list[date], work: dict) -> str:
    html = """
<style>
.wtbl{width:100%%;border-collapse:collapse;table-layout:fixed;font-family:'Malgun Gothic',sans-serif;font-size:13px;}
.wtbl th,.wtbl td{border:1px solid %(border)s;}
.wtbl th{padding:8px 4px;text-align:center;font-size:14px;font-weight:700;}
.wtbl .tcol{width:64px;background:%(tbg)s;color:%(ttxt)s;text-align:center;
            font-weight:700;padding:8px 4px;vertical-align:middle;}
.wtbl .dcell{padding:6px 4px;vertical-align:middle;text-align:center;}
.wgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:4px 8px;}
.wname{color:#000000;text-align:center;line-height:1.6;font-weight:600;}
</style>
""" % {"border": _BORDER, "tbg": _TIME_BG, "ttxt": _TIME_TEXT}

    html += '<table class="wtbl"><tr><th class="tcol">시간대</th>'
    for d in days:
        wd    = WEEKDAYS[d.weekday()]
        color = _weekday_color(d)
        html += (
            f'<th style="background:{_HEADER_BG};color:{color};">'
            f'{d.month}/{d.day} ({wd})</th>'
        )
    html += "</tr>"

    for hour in TIME_SLOTS:
        row_bg = _ROW_BG_BY_HOUR.get(hour)
        tcol_style = f' style="background:{row_bg};color:{_HEADER_TEXT};"' if row_bg else ""
        cell_style = f' style="background:{row_bg};"' if row_bg else ""
        html += f'<tr><td class="tcol"{tcol_style}>{hour:02d}:00</td>'
        for d in days:
            names = [name for name, h in work[d] if h == hour]
            name_divs = "".join(f'<div class="wname">{n}</div>' for n in names)
            cell = f'<div class="wgrid">{name_divs}</div>' if names else ""
            html += f'<td class="dcell"{cell_style}>{cell}</td>'
        html += "</tr>"

    html += "</table>"
    return html


# ── 메인 렌더 ─────────────────────────────────────────────────────────
def render():
    st.markdown("## 📋 주간 근무표")

    today = date.today()
    if "weekly_start" not in st.session_state:
        st.session_state.weekly_start = _week_monday(today)

    ws = st.session_state.weekly_start
    we = ws + timedelta(days=6)

    # ── 내비게이션 ─────────────────────────────────────────────────────
    n1, n2, n3, n4 = st.columns([1.3, 3, 1.3, 1.3])
    with n1:
        if st.button("← 이전 주", use_container_width=True, key="week_prev"):
            st.session_state.weekly_start -= timedelta(weeks=1)
            st.rerun()
    with n2:
        if ws.month == we.month:
            label = f"{ws.year}년 {ws.month}월 {ws.day}일 ~ {we.day}일"
        else:
            label = f"{ws.year}년 {ws.month}월 {ws.day}일 ~ {we.month}월 {we.day}일"
        st.markdown(
            f"<h4 style='margin:0;padding-top:8px;text-align:center;'>{label}</h4>",
            unsafe_allow_html=True,
        )
    with n3:
        if st.button("이번 주", use_container_width=True, key="week_this"):
            st.session_state.weekly_start = _week_monday(today)
            st.rerun()
    with n4:
        if st.button("다음 주 →", use_container_width=True, key="week_next"):
            st.session_state.weekly_start += timedelta(weeks=1)
            st.rerun()

    days = [ws + timedelta(days=i) for i in range(7)]

    try:
        schedule = _load_week(ws)
    except Exception as e:
        st.error(f"구글 시트에서 스케줄을 불러오지 못했습니다: {e}")
        return

    work = schedule["work"]
    off  = schedule["off"]

    # ── 주간 그리드 ───────────────────────────────────────────────────
    grid_html = '<div style="overflow-x:auto;">' + _build_grid(days, work) + "</div>"
    st.markdown(grid_html, unsafe_allow_html=True)

    # ── 휴무자 섹션 ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**휴무자**")

    off_cols = st.columns(7)
    for col, d in zip(off_cols, days):
        wd    = WEEKDAYS[d.weekday()]
        color = _weekday_color(d)
        with col:
            st.markdown(
                f"<div style='font-weight:700;color:{color};'>{d.month}/{d.day} ({wd})</div>",
                unsafe_allow_html=True,
            )
            names = off[d]
            st.caption(", ".join(names) if names else "없음")
