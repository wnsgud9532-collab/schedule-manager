import gspread
import re
import time
from datetime import date, datetime, time as dtime, timedelta
from typing import Optional
from google.oauth2.service_account import Credentials
from pathlib import Path

SHEET_ID = '1FkApqvnGIjdD7iRRs933YPNGQHZlhZ2Uw8ytUYS53uI'
_CRED_FILE = Path(__file__).parent.parent.parent / 'service-account.json'
_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

_CACHE: dict = {'data': None, 'ts': 0.0}
_CACHE_TTL = 30  # seconds

_OFF_CODES = {'주', '무', '공', '연', '병'}
_HOLIDAY_CODES = {'주', '무', '공'}
_SHIFT_ORDER = {'오전': 0, '오후': 1, '야간': 2}


def _get_credentials() -> Credentials:
    """
    서비스 계정 인증 정보를 가져옵니다.
      - 로컬: 프로젝트 루트의 service-account.json 파일
      - 배포(Streamlit Cloud): st.secrets["gcp_service_account"] (Secrets에 등록한 값)
    로컬 파일이 있으면 그걸 우선 사용합니다.
    """
    if _CRED_FILE.exists():
        return Credentials.from_service_account_file(str(_CRED_FILE), scopes=_SCOPES)

    import streamlit as st
    return Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=_SCOPES
    )


# ── 레거시 (Apps Script 대시보드 탭 읽기) ─────────────────────────────────────

def fetch_attendance() -> tuple[str, list[dict], list[dict]]:
    """구글 시트 '대시보드' 탭에서 출퇴근 데이터를 가져옵니다 (레거시)."""
    creds = _get_credentials()
    gc = gspread.authorize(creds)
    rows = gc.open_by_key(SHEET_ID).worksheet('대시보드').get_all_values()

    date_str = rows[1][0].strip() if len(rows) > 1 else ''
    employees: list[dict] = []
    overnight_workers: list[dict] = []
    in_overnight = False

    for row in rows[3:]:
        if not any(c.strip() for c in row):
            continue
        first = row[0].strip() if row else ''
        if '야간 근무자' in first:
            in_overnight = True
            continue
        if in_overnight:
            if first in ('이름', '번호', ''):
                continue
            if len(row) >= 4:
                overnight_workers.append({
                    'name': first,
                    'time': row[1].strip(),
                    'checkin': row[2].strip(),
                    'checkout': row[3].strip(),
                })
        else:
            if first in ('번호', ''):
                continue
            try:
                int(first)
            except ValueError:
                continue
            if len(row) >= 6:
                employees.append({
                    'num': first,
                    'name': row[1].strip(),
                    'shift': row[2].strip(),
                    'time': row[3].strip(),
                    'checkin': row[4].strip(),
                    'checkout': row[5].strip(),
                })

    return date_str, employees, overnight_workers


# ── 실시간 판정 ───────────────────────────────────────────────────────────────

def fetch_attendance_realtime(force: bool = False) -> tuple[str, list[dict], list[dict]]:
    """
    실시간 출퇴근 현황.
      - '스케줄' 탭 → 오늘/어제 근무자 추출
      - '출,퇴근 날인 체크' 응답 시트 → 타임스탬프 읽어 Python에서 출/퇴근 판정
      - 캐시 TTL 30초 (force=True 이면 즉시 갱신)

    Returns: (date_str, employees, overnight_workers)
      employees dict    : {num, name, shift, time, checkin, checkout}
      overnight dict    : {name, time, checkin, checkout}
    """
    now = time.time()
    if not force and _CACHE['data'] is not None and now - _CACHE['ts'] < _CACHE_TTL:
        return _CACHE['data']

    creds = _get_credentials()
    gc = gspread.authorize(creds)
    wb = gc.open_by_key(SHEET_ID)

    today = date.today()
    yesterday = today - timedelta(days=1)

    # 시트 3개 읽기
    schedule_rows = wb.worksheet('스케줄').get_all_values()
    response_rows = wb.worksheet('출,퇴근 날인 체크').get_all_values()
    # 부서원명단은 이름 검증 목적으로만 보관 (현재 로직에서는 불필요)
    # member_rows = wb.worksheet('부서원명단').get_all_values()

    responses = _parse_responses(response_rows)

    today_shifts = _parse_schedule_for_date(schedule_rows, today)
    yesterday_night = [
        (name, hour)
        for name, hour in _parse_schedule_for_date(schedule_rows, yesterday)
        if hour >= 22
    ]

    # 오늘 근무자 판정
    employees_raw = []
    for name, start_hour in today_shifts:
        checkin_str, checkout_str = _judge_worker(name, start_hour, today, responses)
        employees_raw.append({
            'name':     name,
            'shift':    _classify_shift(start_hour),
            'time':     f"{start_hour:02d}:00",
            'checkin':  checkin_str,
            'checkout': checkout_str,
            '_hour':    start_hour,
        })

    # 오전 → 오후 → 야간, 동일 조 내에서는 출근 시간순 정렬
    employees_raw.sort(key=lambda e: (_SHIFT_ORDER.get(e['shift'], 3), e['_hour']))
    employees = [
        {k: v for k, v in e.items() if k != '_hour'} | {'num': str(i)}
        for i, e in enumerate(employees_raw, 1)
    ]

    # 어제 야간 근무자 판정
    overnight = []
    for name, start_hour in yesterday_night:
        checkin_str, checkout_str = _judge_worker(name, start_hour, yesterday, responses)
        overnight.append({
            'name':     name,
            'time':     f"{start_hour:02d}:00",
            'checkin':  checkin_str,
            'checkout': checkout_str,
        })

    date_str = today.strftime('%Y년 %m월 %d일')
    result = (date_str, employees, overnight)
    _CACHE.update({'data': result, 'ts': time.time()})
    return result


# ── 파싱 헬퍼 ────────────────────────────────────────────────────────────────

def _parse_responses(rows: list[list]) -> list[dict]:
    """응답 시트 파싱. A열=타임스탬프, B열=이름."""
    result = []
    for row in rows[1:]:  # 헤더 행 스킵
        if len(row) < 2:
            continue
        ts = _parse_timestamp(row[0])
        name = row[1].strip() if row[1] else ''
        if ts and name:
            result.append({'name': name, 'ts': ts})
    return result


def _parse_timestamp(raw) -> datetime | None:
    """여러 포맷의 타임스탬프를 datetime으로 변환."""
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, date):
        return datetime.combine(raw, dtime.min)

    s = str(raw).strip()
    if not s:
        return None

    # 구글 폼 한국어 포맷: "2026. 6. 12 오전 9:21:37"
    m = re.match(
        r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\s+(오전|오후)\s+(\d{1,2}):(\d{2}):(\d{2})',
        s,
    )
    if m:
        y, mo, d, ampm, h, mi, sec = m.groups()
        h = int(h)
        if ampm == '오후' and h != 12:
            h += 12
        elif ampm == '오전' and h == 12:
            h = 0
        try:
            return datetime(int(y), int(mo), int(d), h, int(mi), int(sec))
        except ValueError:
            return None

    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass

    return None


def _find_date_column(rows: list[list], target: date) -> tuple[Optional[int], Optional[int]]:
    """
    스케줄 시트에서 날짜 행과 target 날짜의 컬럼 인덱스를 찾음.
    날짜 행 자동 감지: C열(index 2)부터 1~31 정수가 20개 이상인 행.
    """
    date_row_idx = None
    for i, row in enumerate(rows):
        if sum(1 for c in row[2:] if _is_day_number(c)) >= 20:
            date_row_idx = i
            break
    if date_row_idx is None:
        return None, None

    date_row = rows[date_row_idx]
    target_col = next(
        (ci for ci in range(2, len(date_row)) if _to_int(date_row[ci]) == target.day),
        None,
    )
    return date_row_idx, target_col


def _parse_schedule_for_date(rows: list[list], target: date) -> list[tuple[str, int]]:
    """스케줄 시트에서 target 날짜 근무자 목록 반환."""
    if not rows:
        return []

    date_row_idx, target_col = _find_date_column(rows, target)
    if date_row_idx is None or target_col is None:
        return []

    # 날짜 행(+0) → 요일 행(+1) → 근무자 데이터(+2 부터)
    result = []
    for row in rows[date_row_idx + 2:]:
        if len(row) <= target_col:
            continue
        name = row[1].strip() if len(row) > 1 else ''
        if not name or name in ('이름', '성명'):
            continue
        code = row[target_col].strip()
        if not code or code in _OFF_CODES:
            continue
        h = _to_int(code)
        if h is not None and 0 <= h <= 23:
            result.append((name, h))

    return result


def fetch_weekly_schedule(week_start: date) -> dict:
    """
    '스케줄' 탭에서 week_start(월요일)부터 7일간의 근무/휴무 데이터를 가져옴.

    Returns: {
        'work': {date: [(name, hour), ...]},  # 시간대별 근무자
        'off':  {date: [name, ...]},          # 휴무자 (코드 '주'/'무'/'공')
    }
    """
    creds = _get_credentials()
    gc = gspread.authorize(creds)
    rows = gc.open_by_key(SHEET_ID).worksheet('스케줄').get_all_values()

    days = [week_start + timedelta(days=i) for i in range(7)]
    work: dict[date, list[tuple[str, int]]] = {}
    off: dict[date, list[str]] = {}

    for d in days:
        date_row_idx, target_col = _find_date_column(rows, d)
        day_work: list[tuple[str, int]] = []
        day_off: list[str] = []

        if date_row_idx is not None and target_col is not None:
            for row in rows[date_row_idx + 2:]:
                if len(row) <= target_col:
                    continue
                name = row[1].strip() if len(row) > 1 else ''
                if not name or name in ('이름', '성명'):
                    continue
                code = row[target_col].strip()
                if not code:
                    continue
                if code in _HOLIDAY_CODES:
                    day_off.append(name)
                    continue
                if code in _OFF_CODES:
                    continue
                h = _to_int(code)
                if h is not None and 0 <= h <= 23:
                    day_work.append((name, h))

        work[d] = day_work
        off[d] = day_off

    return {'work': work, 'off': off}


# ── 판정 헬퍼 ────────────────────────────────────────────────────────────────

def _classify_shift(hour: int) -> str:
    if 6 <= hour <= 12:
        return '오전'
    if 13 <= hour <= 16:
        return '오후'
    if hour >= 22 or hour <= 1:
        return '야간'
    return '기타'


def _judge_worker(
    name: str,
    start_hour: int,
    base_date: date,
    responses: list[dict],
) -> tuple[str, str]:
    """
    출근/퇴근 판정.
      - 기준선 = 출근 예정 + 4.5시간
      - 기준선 이전 첫 응답 → 출근
      - 기준선 이후 첫 응답 → 퇴근
      - 윈도우: 출근 예정 -3시간 ~ +12시간
    """
    scheduled = datetime.combine(base_date, dtime(start_hour % 24, 0))
    midpoint  = scheduled + timedelta(hours=4.5)
    win_start = scheduled - timedelta(hours=3)
    win_end   = scheduled + timedelta(hours=12)

    hits = sorted(
        (r for r in responses
         if r['name'] == name and win_start <= r['ts'] <= win_end),
        key=lambda x: x['ts'],
    )

    checkin  = next((r for r in hits if r['ts'] < midpoint), None)
    checkout = next((r for r in hits if r['ts'] >= midpoint), None)

    return (
        '🟢' if checkin  else '🔴',
        '🟢' if checkout else '🔴',
    )


# ── 공통 유틸 ─────────────────────────────────────────────────────────────────

def _is_day_number(cell) -> bool:
    v = _to_int(cell)
    return v is not None and 1 <= v <= 31


def _to_int(cell) -> int | None:
    try:
        return int(float(str(cell).strip()))
    except (ValueError, TypeError):
        return None
