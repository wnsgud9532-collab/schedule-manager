"""Streamlit Cloud가 기본으로 찾는 진입점 파일명(streamlit_app.py)에 맞추기 위한 래퍼.

실제 앱 코드는 app.py 하나만 유지한다. (예전엔 이 파일에 app.py와 별개로
오래된 사본 코드가 들어있었는데, app.py만 계속 업데이트되고 이 파일은
그대로 방치되면서 로컬(run.bat → app.py)과 실제 배포본(Streamlit Cloud →
streamlit_app.py)이 서로 다른 코드를 실행하는 버그가 있었음 — 주간 근무표
탭 추가, 기본 페이지 변경 등 최근 수정사항이 배포본에 반영되지 않던 원인.)
"""
import runpy

runpy.run_path("app.py", run_name="__main__")
