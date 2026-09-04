from datetime import date, time, timedelta
import streamlit as st
from app.core.schedule_manager import get_manager
from app.core.timeutil import today_kst

WEEKDAYS   = ["월", "화", "수", "목", "금", "토", "일"]
TIME_SLOTS = [6, 7, 8, 13, 15, 16, 22]
SHIFT_DURATION_HOURS = 9  # 모든 근무는 9시간 (예: 06:00 시작 → 15:00 종료)

_SHIFT_HOUR_LABELS = {
    6:  "06:00 (오전)", 7:  "07:00 (오전)", 8:  "08:00 (오전)",
    13: "13:00 (오후)", 15: "15:00 (오후)", 16: "16:00 (오후)",
    22: "22:00 (야간)",
}

_HEADER_BG   = "#e0f2fe"   # 연한 하늘색
_HEADER_TEXT = "#1e293b"
_SAT_TEXT    = "#7c3aed"   # 보라
_SUN_TEXT    = "#dc2626"   # 빨강
_TIME_BG     = "#1e3a8a"   # 시간대 컬럼 진한 남색 배경
_TIME_TEXT   = "#ffffff"
_BORDER      = "#d1d5db"   # 연한 회색

# 오늘 날짜 컬럼 강조 (배경 채움 없이 테두리로만 표시)
_TODAY_BORDER = "#1d4ed8"   # 오늘 컬럼 테두리 (진한 파란색)

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


def _shift_end_time(start_hour: int) -> time:
    return time((start_hour + SHIFT_DURATION_HOURS) % 24, 0)


def _weekday_color(d: date) -> str:
    if d.weekday() == 5:
        return _SAT_TEXT
    if d.weekday() == 6:
        return _SUN_TEXT
    return _HEADER_TEXT


@st.cache_data(ttl=60, show_spinner=False)
def _load_week(week_start: date) -> dict:
    return get_manager().get_weekly_schedule(week_start)


# ── 주간 표 HTML ─────────────────────────────────────────────────────────
def _build_grid(days: list[date], work: dict, today: date) -> str:
    # 모바일 우선(기본값 = 좁은 화면에 꽉 차는 컴팩트 표) → 넓은 화면에서 %(min_desktop)s 이상 시 여유있게 확대
    html = """
<style>
.wtbl{width:100%%;border-collapse:collapse;table-layout:fixed;font-family:'Malgun Gothic',sans-serif;font-size:9.5px;}
.wtbl th,.wtbl td{border:1px solid %(border)s;}
.wtbl th{padding:3px 1px;text-align:center;font-size:9.5px;font-weight:700;line-height:1.25;}
.wtbl .tcol{width:34px;background:%(tbg)s;color:%(ttxt)s;text-align:center;
            font-weight:700;padding:3px 1px;vertical-align:middle;line-height:1.2;
            white-space:nowrap;font-size:8.5px;}
.wtbl .dcell{padding:2px 1px;vertical-align:middle;text-align:center;}
.wgrid{display:grid;grid-template-columns:1fr;gap:1px;}
.wname{color:#000000;text-align:center;line-height:1.25;font-weight:600;white-space:nowrap;}

@media (min-width: 641px) {
    .wtbl{min-width:720px;font-size:13px;}
    .wtbl th{padding:8px 4px;font-size:14px;}
    .wtbl .tcol{width:64px;padding:8px 4px;font-size:14px;}
    .wtbl .dcell{padding:6px 4px;}
    .wgrid{grid-template-columns:repeat(2,1fr);gap:4px 8px;}
    .wname{line-height:1.6;}
}
</style>
""" % {"border": _BORDER, "tbg": _TIME_BG, "ttxt": _TIME_TEXT}

    html += '<table class="wtbl"><tr><th class="tcol">시간대</th>'
    for d in days:
        wd    = WEEKDAYS[d.weekday()]
        color = _weekday_color(d)
        extra = (
            f'border-left:2px solid {_TODAY_BORDER};'
            f'border-right:2px solid {_TODAY_BORDER};'
            f'border-top:2px solid {_TODAY_BORDER};'
        ) if d == today else ""
        html += (
            f'<th style="background:{_HEADER_BG};color:{color};{extra}">'
            f'{d.month}/{d.day} ({wd})</th>'
        )
    html += "</tr>"

    for i, hour in enumerate(TIME_SLOTS):
        row_bg = _ROW_BG_BY_HOUR.get(hour)
        is_last_row = i == len(TIME_SLOTS) - 1
        tcol_style = f' style="background:{row_bg};color:{_HEADER_TEXT};"' if row_bg else ""
        html += f'<tr><td class="tcol"{tcol_style}>{hour:02d}:00</td>'
        for d in days:
            names = [name for name, h in work[d] if h == hour]
            name_divs = "".join(f'<div class="wname">{n}</div>' for n in names)
            cell = f'<div class="wgrid">{name_divs}</div>' if names else ""
            style_parts = [f'background:{row_bg};'] if row_bg else []
            if d == today:
                style_parts.append(f'border-left:2px solid {_TODAY_BORDER};')
                style_parts.append(f'border-right:2px solid {_TODAY_BORDER};')
                if is_last_row:
                    style_parts.append(f'border-bottom:2px solid {_TODAY_BORDER};')
            cell_style = f' style="{"".join(style_parts)}"' if style_parts else ""
            html += f'<td class="dcell"{cell_style}>{cell}</td>'
        html += "</tr>"

    html += "</table>"
    return html


# ── 근무 수정 다이얼로그 ───────────────────────────────────────────────
@st.dialog("✏️ 근무 수정")
def _edit_dialog():
    mgr = get_manager()
    employees = [e.name for e in mgr.get_employees()]

    tab_edit, tab_history = st.tabs(["근무 수정", "수정 기록"])

    # ── 수정 탭 ───────────────────────────────────────────────────────
    with tab_edit:
        if not employees:
            st.info("등록된 근무자가 없습니다. 먼저 엑셀을 가져와주세요.")
        else:
            name   = st.selectbox("근무자", employees, key="editshift_name")
            target = st.date_input("날짜", value=today_kst(), key="editshift_date")

            current = mgr.get_shift_for_employee(name, target)

            if current:
                s = current[0]
                st.caption(f"현재: **{s.start_str()} ~ {s.end_str()}** 근무")
                mode = st.radio(
                    "변경 내용", ["근무 시간 변경", "휴무로 변경"],
                    horizontal=True, key="editshift_mode",
                )

                if mode == "근무 시간 변경":
                    hours = list(_SHIFT_HOUR_LABELS)
                    default_idx = hours.index(s.start_time.hour) if s.start_time.hour in hours else 0
                    new_hour = st.selectbox(
                        "새 근무 시작 시간", hours, index=default_idx,
                        format_func=lambda h: _SHIFT_HOUR_LABELS[h],
                        key="editshift_hour",
                    )
                    if st.button("저장", type="primary", key="editshift_save_time"):
                        mgr.edit_shift_time(s.id, time(new_hour, 0), _shift_end_time(new_hour))
                        _load_week.clear()
                        st.success(f"{name} · {target.month}/{target.day} → {_SHIFT_HOUR_LABELS[new_hour]} 근무로 수정했습니다.")
                        st.rerun()
                else:
                    st.warning(f"{name}님을 {target.month}/{target.day} 휴무로 변경합니다.")
                    if st.button("휴무로 저장", type="primary", key="editshift_save_off"):
                        mgr.mark_shift_off(s.id)
                        _load_week.clear()
                        st.success(f"{name} · {target.month}/{target.day} 를 휴무로 변경했습니다.")
                        st.rerun()
            else:
                st.caption("현재: **휴무** (근무 기록 없음)")
                hours = list(_SHIFT_HOUR_LABELS)
                new_hour = st.selectbox(
                    "근무로 등록할 시작 시간", hours,
                    format_func=lambda h: _SHIFT_HOUR_LABELS[h],
                    key="editshift_hour_new",
                )
                if st.button("근무로 등록", type="primary", key="editshift_save_new"):
                    mgr.add_shift(name, target, time(new_hour, 0), _shift_end_time(new_hour))
                    _load_week.clear()
                    st.success(f"{name} · {target.month}/{target.day} 를 {_SHIFT_HOUR_LABELS[new_hour]} 근무로 등록했습니다.")
                    st.rerun()

    # ── 수정 기록 탭 ──────────────────────────────────────────────────
    with tab_history:
        records = mgr.get_modified_shifts()
        if not records:
            st.info("수정된 근무 기록이 없습니다.")
        else:
            st.caption(f"총 {len(records)}건 수정됨")
            for r in records:
                c1, c2 = st.columns([5, 1.3])
                with c1:
                    orig = f'{r["original_start_time"]}~{r["original_end_time"]}'
                    now  = "휴무" if r["note"] == "삭제" else f'{r["start_time"]}~{r["end_time"]}'
                    st.markdown(
                        f'**{r["employee_name"]}** · {r["date"].month}/{r["date"].day} '
                        f'&nbsp;&nbsp;{orig} → **{now}**'
                    )
                with c2:
                    if st.button("삭제(되돌리기)", key=f"restore_{r['id']}", use_container_width=True):
                        mgr.restore_shift(r["id"])
                        _load_week.clear()
                        st.rerun()
            st.divider()
            if st.button("전체 되돌리기", key="restore_all_shifts"):
                n = mgr.restore_all_shifts()
                _load_week.clear()
                st.success(f"{n}건 되돌렸습니다.")
                st.rerun()


# ── 메인 렌더 ─────────────────────────────────────────────────────────
def render():
    today = today_kst()
    if "weekly_start" not in st.session_state:
        st.session_state.weekly_start = _week_monday(today)

    ws = st.session_state.weekly_start
    we = ws + timedelta(days=6)

    # 모바일에서는 제목/버튼/날짜 라벨 영역을 데스크탑보다 훨씬 작고 조밀하게
    # (기본 모바일 CSS는 버튼을 세로로 꽉 채워 쌓고 요소 사이 간격도 넓어서
    #  표가 첫 화면 아래로 밀려나므로, 이 영역(.st-key-weekly_top) 전체를
    #  컴팩트한 크기 + 좁은 간격 + 한 줄(넘치면 자동 줄바꿈)로 오버라이드)
    st.markdown(
        """
<style>
@media (max-width: 640px) {
    .st-key-weekly_top [data-testid="stVerticalBlock"] {
        gap: 0.3rem !important;
    }
    .st-key-weekly_top h2 {
        font-size: 1.15rem !important;
        margin: 0 !important;
    }
    .st-key-weekly_nav_edit [data-testid="stHorizontalBlock"],
    .st-key-weekly_nav_dates [data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 0.3rem !important;
    }
    .st-key-weekly_nav_edit [data-testid="stColumn"],
    .st-key-weekly_nav_dates [data-testid="stColumn"] {
        width: auto !important;
        min-width: 0 !important;
        flex: 0 1 auto !important;
    }
    /* 오른쪽 정렬용 빈 스페이서 칸은 모바일에서 숨김 */
    .st-key-weekly_nav_edit [data-testid="stColumn"]:first-child {
        display: none !important;
    }
    .st-key-weekly_nav_edit .stButton > button,
    .st-key-weekly_nav_dates .stButton > button {
        min-height: 1.9rem !important;
        font-size: 0.72rem !important;
        padding: 0.15rem 0.5rem !important;
        white-space: nowrap !important;
    }
    .st-key-weekly_nav_dates h4 {
        font-size: 0.72rem !important;
        margin: 0 !important;
        padding-top: 0 !important;
        white-space: nowrap !important;
    }
}
</style>
""",
        unsafe_allow_html=True,
    )

    with st.container(key="weekly_top"):
        st.markdown("## 📋 주간 근무표")

        # ── 근무 수정 버튼 ───────────────────────────────────────────
        with st.container(key="weekly_nav_edit"):
            top_l, top_r = st.columns([5, 1.4])
            with top_r:
                if st.button("✏️ 근무 수정", use_container_width=True, key="open_edit_dialog"):
                    _edit_dialog()

        # ── 내비게이션 ───────────────────────────────────────────────
        with st.container(key="weekly_nav_dates"):
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
        st.error(f"근무 데이터를 불러오지 못했습니다: {e}")
        return

    work = schedule["work"]
    off  = schedule["off"]

    # ── 주간 그리드 (화면 폭에 맞춰 같은 표가 알차게 축소/확대) ─────────
    grid_html = '<div class="scroll-x">' + _build_grid(days, work, today) + "</div>"
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
