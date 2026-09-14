"""
로컬 SQLite DB(엑셀로 가져온 근무 데이터)를 GitHub 비공개 Gist에 자동 백업/복원.

Streamlit Cloud는 앱이 잠들었다 깨어나거나 재배포될 때 컨테이너가 새로
생성되면서 로컬 파일 시스템(data/schedule.db)이 초기화된다. 이를 보완하기
위해 DB 전체 내용을 GitHub 비공개 Gist에 JSON으로 저장해두고, 앱이 새로
시작될 때(로컬 DB가 비어있을 때) 자동으로 복원한다.

* 구글 시트는 이 프로젝트에서 쓰지 않기로 했으므로 사용하지 않는다.
* 별도 서비스 가입 없이, 기존 GitHub 계정의 개인 액세스 토큰(PAT, gist 권한)만 있으면 된다.
* 네트워크/권한 문제로 실패해도 앱 동작에는 영향이 없도록 호출하는 쪽(database.py)에서
  예외를 흡수한다.
"""
import json
import os
import requests

_GIST_DESC = "schedule-manager-db-backup (자동 생성 — 삭제하지 마세요)"
_GIST_FILENAME = "schedule_backup.json"
_API = "https://api.github.com"


def _get_token() -> str:
    """
    GitHub PAT(gist 권한)을 가져옵니다.
      - 로컬: 환경변수 GITHUB_BACKUP_TOKEN
      - 배포(Streamlit Cloud): st.secrets["github_backup_token"]
    """
    token = os.environ.get("GITHUB_BACKUP_TOKEN")
    if token:
        return token
    import streamlit as st
    return st.secrets["github_backup_token"]


def _headers() -> dict:
    return {
        "Authorization": f"token {_get_token()}",
        "Accept": "application/vnd.github+json",
    }


def _find_gist_id() -> str | None:
    """설명(description)으로 백업용 Gist를 찾아 id 반환. 없으면 None."""
    page = 1
    while True:
        resp = requests.get(
            f"{_API}/gists",
            headers=_headers(),
            params={"per_page": 100, "page": page},
            timeout=10,
        )
        resp.raise_for_status()
        gists = resp.json()
        if not gists:
            return None
        for g in gists:
            if g.get("description") == _GIST_DESC:
                return g["id"]
        if len(gists) < 100:
            return None
        page += 1


def save_backup(data: dict):
    """DB 스냅샷을 GitHub 비공개 Gist에 저장 (있으면 갱신, 없으면 새로 생성)."""
    payload = json.dumps(data, ensure_ascii=False)
    body = {
        "description": _GIST_DESC,
        "public": False,
        "files": {_GIST_FILENAME: {"content": payload or "{}"}},
    }
    gist_id = _find_gist_id()
    if gist_id:
        resp = requests.patch(f"{_API}/gists/{gist_id}", headers=_headers(), json=body, timeout=10)
    else:
        resp = requests.post(f"{_API}/gists", headers=_headers(), json=body, timeout=10)
    resp.raise_for_status()


def load_backup():
    """Gist에 저장된 DB 스냅샷을 불러옴. 백업이 없으면 None."""
    gist_id = _find_gist_id()
    if not gist_id:
        return None
    resp = requests.get(f"{_API}/gists/{gist_id}", headers=_headers(), timeout=10)
    resp.raise_for_status()
    file_info = resp.json().get("files", {}).get(_GIST_FILENAME)
    if not file_info:
        return None

    content = file_info.get("content")
    if file_info.get("truncated"):
        # 응답이 1MB 넘게 잘렸으면 raw_url에서 전체 내용을 받아옴
        raw = requests.get(file_info["raw_url"], headers=_headers(), timeout=10)
        raw.raise_for_status()
        content = raw.text

    if not content:
        return None
    return json.loads(content)
