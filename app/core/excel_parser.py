"""
엑셀 스케쥴 파일 파서.
지원 포맷:
  A) 리스트형  - 열: 이름, 날짜, 출근시간, 퇴근시간
  B) 매트릭스형 - 행: 직원, 열: 날짜(1~31), 셀: 시간범위 or 근무코드
"""
import re
from datetime import date, time
from typing import List, Tuple, Optional, Dict
import pandas as pd
from app.models.schedule import Shift

TIME_RANGE_RE = re.compile(
    r"(\d{1,2})[:\-]?(\d{2})?\s*[\-~]\s*(\d{1,2})[:\-]?(\d{2})?"
)
OFF_KEYWORDS = {"휴", "off", "휴무", "휴일", "off day", "-", "x", ""}


def _parse_time_str(s: str) -> Optional[time]:
    s = s.strip()
    for fmt in ("%H:%M", "%H%M", "%H시%M분", "%H시"):
        try:
            from datetime import datetime as dt
            return dt.strptime(s, fmt).time()
        except ValueError:
            pass
    m = re.match(r"^(\d{1,2}):?(\d{2})?$", s)
    if m:
        h = int(m.group(1))
        mi = int(m.group(2)) if m.group(2) else 0
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return time(h, mi)
    return None


def _parse_cell_as_range(cell_val: str) -> Optional[Tuple[time, time]]:
    cell_val = str(cell_val).strip()
    if cell_val.lower() in OFF_KEYWORDS:
        return None
    m = TIME_RANGE_RE.search(cell_val)
    if m:
        h1, m1, h2, m2 = m.groups()
        h1, h2 = int(h1), int(h2)
        m1 = int(m1) if m1 else 0
        m2 = int(m2) if m2 else 0
        try:
            return time(h1, m1), time(h2, m2)
        except ValueError:
            pass
    return None


def _parse_date(val) -> Optional[date]:
    if isinstance(val, date):
        return val
    if hasattr(val, 'date'):
        return val.date()
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%m/%d/%Y", "%m-%d"):
        try:
            from datetime import datetime as dt
            parsed = dt.strptime(s, fmt)
            if parsed.year == 1900:
                return None
            return parsed.date()
        except ValueError:
            pass
    return None


def _is_date_header(val) -> bool:
    if isinstance(val, (int, float)) and 1 <= val <= 31:
        return True
    s = str(val).strip()
    if re.match(r"^\d{1,2}(일)?$", s):
        return True
    if re.match(r"^\d{1,2}/\d{1,2}$", s):
        return True
    return False


def _find_kal_date_row(df: pd.DataFrame) -> int:
    """KAL 화원 포맷의 날짜 행(1~31) 인덱스 탐색. 못 찾으면 -1."""
    for i in range(min(5, len(df))):
        days_found = set()
        for val in df.iloc[i]:
            if pd.isna(val):
                continue
            try:
                v = int(float(str(val)))
                if 1 <= v <= 31:
                    days_found.add(v)
            except Exception:
                pass
        if len(days_found) >= 20:
            return i
    return -1


def detect_format(df: pd.DataFrame) -> str:
    if df.empty:
        return "list"
    # KAL 커스텀 포맷: 데이터 내부에 날짜 행(1~31)이 있음
    if _find_kal_date_row(df) >= 0:
        return "kal"
    headers = [str(c).strip() for c in df.columns]
    if sum(1 for h in headers if _is_date_header(h)) >= 5:
        return "matrix"
    name_cols = {"이름", "성명", "직원", "name", "employee"}
    date_cols = {"날짜", "date", "일자", "근무일"}
    has_name = any(h.lower() in name_cols for h in headers)
    has_date = any(h.lower() in date_cols for h in headers)
    if has_name and has_date:
        return "list"
    return "matrix"


def parse_list_format(df: pd.DataFrame, year: int, month: int,
                      col_map: Dict[str, str] = None) -> List[Shift]:
    """
    col_map keys: name, date, start, end
    """
    if col_map is None:
        col_map = _auto_detect_list_columns(df)

    shifts = []
    for _, row in df.iterrows():
        try:
            name = str(row[col_map["name"]]).strip()
            if not name or name.lower() == "nan":
                continue
            d = _parse_date(row[col_map["date"]])
            if d is None:
                continue
            start = _parse_time_str(str(row[col_map["start"]]))
            end = _parse_time_str(str(row[col_map["end"]]))
            if start is None or end is None:
                continue
            shifts.append(Shift(
                id=None,
                employee_id=0,
                employee_name=name,
                date=d,
                start_time=start,
                end_time=end,
            ))
        except (KeyError, TypeError, ValueError):
            continue
    return shifts


def parse_matrix_format(df: pd.DataFrame, year: int, month: int,
                        shift_codes: Dict[str, Tuple[str, str]] = None) -> List[Shift]:
    """
    첫 번째 열 = 이름, 나머지 열 = 날짜(1~31)
    셀 값 = "09:00-18:00" | "09-18" | "A" (shift code) | "휴" (off)
    shift_codes = {"A": ("09:00", "18:00"), "B": ("13:00", "22:00")}
    """
    if shift_codes is None:
        shift_codes = {}

    shifts = []
    name_col = df.columns[0]

    for _, row in df.iterrows():
        name = str(row[name_col]).strip()
        if not name or name.lower() == "nan":
            continue

        for col in df.columns[1:]:
            day = _extract_day_number(col)
            if day is None:
                continue
            try:
                target_date = date(year, month, day)
            except ValueError:
                continue

            cell = str(row[col]).strip() if not pd.isna(row[col]) else ""
            if cell.lower() in OFF_KEYWORDS:
                continue

            time_range = _parse_cell_as_range(cell)
            if time_range is None and cell in shift_codes:
                code = shift_codes[cell]
                s = _parse_time_str(code[0])
                e = _parse_time_str(code[1])
                if s and e:
                    time_range = (s, e)

            if time_range:
                shifts.append(Shift(
                    id=None,
                    employee_id=0,
                    employee_name=name,
                    date=target_date,
                    start_time=time_range[0],
                    end_time=time_range[1],
                ))
    return shifts


def _extract_day_number(col_val) -> Optional[int]:
    if isinstance(col_val, (int, float)):
        v = int(col_val)
        return v if 1 <= v <= 31 else None
    s = str(col_val).strip()
    m = re.match(r"^(\d{1,2})", s)
    if m:
        v = int(m.group(1))
        return v if 1 <= v <= 31 else None
    return None


def _auto_detect_list_columns(df: pd.DataFrame) -> Dict[str, str]:
    mapping = {}
    name_kw = ["이름", "성명", "직원명", "name", "employee"]
    date_kw = ["날짜", "일자", "근무일", "date"]
    start_kw = ["출근", "시작", "start", "출근시간", "시작시간", "from"]
    end_kw = ["퇴근", "종료", "end", "퇴근시간", "종료시간", "to"]

    for col in df.columns:
        c = str(col).lower().strip()
        if not mapping.get("name") and any(k in c for k in name_kw):
            mapping["name"] = col
        elif not mapping.get("date") and any(k in c for k in date_kw):
            mapping["date"] = col
        elif not mapping.get("start") and any(k in c for k in start_kw):
            mapping["start"] = col
        elif not mapping.get("end") and any(k in c for k in end_kw):
            mapping["end"] = col

    return mapping


def load_excel_preview(filepath: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(filepath, header=0, nrows=20)
        df = df.dropna(how="all")
        return df
    except Exception as e:
        raise ValueError(f"엑셀 파일을 읽을 수 없습니다: {e}")


def parse_kal_format(df: pd.DataFrame, year: int, month: int) -> List[Shift]:
    """KAL 화원 근무표 커스텀 포맷 파싱.

    구조 (header=0 기준):
      - 헤더행: 타이틀
      - iloc[date_row_idx]: 날짜 1~31
      - iloc[date_row_idx+1]: 요일 (건너뜀)
      - iloc[date_row_idx+2+]: 번호 | 이름 | 근무코드(숫자=시작시간, 9h 근무)
    """
    date_row_idx = _find_kal_date_row(df)
    if date_row_idx < 0:
        return []

    date_row = df.iloc[date_row_idx]
    col_to_day: Dict[int, int] = {}
    for col_idx, val in enumerate(date_row):
        if pd.isna(val):
            continue
        try:
            day = int(float(str(val)))
            if 1 <= day <= 31:
                col_to_day[col_idx] = day
        except Exception:
            pass

    shifts = []
    for i in range(date_row_idx + 2, len(df)):
        row = df.iloc[i]
        try:
            emp_num = float(str(row.iloc[0]))
            if not (1 <= emp_num <= 200):
                continue
        except Exception:
            continue
        name = str(row.iloc[1]).strip()
        if not name or name.lower() == "nan":
            continue
        for col_idx, day in col_to_day.items():
            if col_idx >= len(row):
                continue
            val = row.iloc[col_idx]
            if pd.isna(val):
                continue
            s = str(val).strip()
            try:
                h = int(float(s))
                if 0 <= h <= 23:
                    try:
                        d = date(year, month, day)
                    except ValueError:
                        continue
                    shifts.append(Shift(
                        id=None, employee_id=0, employee_name=name,
                        date=d,
                        start_time=time(h, 0),
                        end_time=time((h + 9) % 24, 0),
                    ))
            except Exception:
                pass
    return shifts


def parse_excel_file(filepath: str, year: int, month: int,
                     fmt: str = "auto",
                     col_map: Dict[str, str] = None,
                     shift_codes: Dict[str, Tuple[str, str]] = None) -> List[Shift]:
    df = pd.read_excel(filepath, header=0)
    df = df.dropna(how="all").reset_index(drop=True)

    if fmt == "auto":
        fmt = detect_format(df)

    if fmt == "kal":
        return parse_kal_format(df, year, month)
    elif fmt == "list":
        return parse_list_format(df, year, month, col_map)
    else:
        return parse_matrix_format(df, year, month, shift_codes)
