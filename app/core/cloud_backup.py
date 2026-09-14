"""
로컬 SQLite DB(엑셀로 가져온 근무 데이터)를 구글 시트에 자동 백업/복원.

Streamlit Community Cloud는 앱이 잠들었다 깨어나거나 재배포될 때 컨테이너가
새로 생성되면서 로컬 파일 시스템(data/schedule.db)이 초기화된다. 이를 보완하기
위해 DB 전체 내용을 기존 구글 시트의 숨은 탭에 JSON으로 저장해두고, 앱이 새로
시작될 때(로컬 DB가 비어있을 때) 자동으로 복원한다.

네트워크/권한 문제로 실패해도 앱 동작에는 영향이 없도록 호출하는 쪽에서
예외를 흡수한다 (database.py 참고).
"""
import json
import gspread
from app.core.sheets_client import _get_credentials, SHEET_ID

_BACKUP_TAB = "DB백업(자동)"
_CHUNK_SIZE = 40000  # 구글 시트 셀 문자 제한(50,000) 이내로 여유있게 분할


def _get_worksheet():
    creds = _get_credentials()
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    try:
        return sh.worksheet(_BACKUP_TAB)
    except gspread.WorksheetNotFound:
        return sh.add_worksheet(title=_BACKUP_TAB, rows=20, cols=1)


def save_backup(data: dict):
    """DB 스냅샷을 구글 시트에 저장."""
    payload = json.dumps(data, ensure_ascii=False)
    chunks = [payload[i:i + _CHUNK_SIZE] for i in range(0, len(payload), _CHUNK_SIZE)] or [""]
    ws = _get_worksheet()
    ws.clear()
    ws.update(values=[[c] for c in chunks], range_name="A1")


def load_backup():
    """구글 시트에 저장된 DB 스냅샷을 불러옴. 백업이 없으면 None."""
    ws = _get_worksheet()
    rows = ws.get_all_values()
    payload = "".join(r[0] for r in rows if r and r[0])
    if not payload:
        return None
    return json.loads(payload)
