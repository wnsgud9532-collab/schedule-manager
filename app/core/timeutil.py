"""
KST(한국 표준시) 기준 현재 시각.

배포 서버(예: Streamlit Community Cloud)는 보통 UTC로 동작해서, 그냥
datetime.now()/date.today()를 쓰면 한국 시간과 최대 9시간까지 어긋난다.
(예: 실제 KST 14:41인데 서버는 UTC 05:41로 인식 → "13시 근무 중"인 직원이
"출근 예정"으로 잘못 표시됨)

이 모듈은 항상 Asia/Seoul 기준 벽시계 시각을 naive datetime/date로 반환해서,
기존 코드의 naive 날짜/시간 비교 로직과 그대로 호환되게 한다.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

_KST = ZoneInfo("Asia/Seoul")


def now_kst() -> datetime:
    """한국 시간 기준 현재 시각 (tzinfo 없는 naive datetime)."""
    return datetime.now(_KST).replace(tzinfo=None)


def today_kst() -> date:
    """한국 시간 기준 오늘 날짜."""
    return now_kst().date()
