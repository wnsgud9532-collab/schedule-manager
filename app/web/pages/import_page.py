import os
import re
import tempfile
from datetime import date
import streamlit as st
from app.core.schedule_manager import get_manager
from app.core.excel_parser import parse_excel_file
from app.core.timeutil import today_kst


def _detect_year_month(filename: str):
    m = re.search(r"(\d{2,4})[년\-_\. ]?\s*(\d{1,2})[월]?", filename)
    if m:
        year  = int(m.group(1))
        month = int(m.group(2))
        if year < 100:
            year += 2000
        if 1 <= month <= 12:
            return year, month
    return None, None


FORMAT_OPTIONS = {
    "자동 감지":                      "auto",
    "목록형 (이름/날짜/시작/종료)":    "list",
    "매트릭스형 (행=직원, 열=날짜)":  "matrix",
    "KAL 화원 포맷":                  "kal",
}


def render():
    st.markdown("## 📂 엑셀 가져오기")

    today = today_kst()

    uploaded = st.file_uploader(
        "엑셀 파일 선택 (.xlsx / .xls)",
        type=["xlsx", "xls"],
        key="excel_uploader",
    )

    if not uploaded:
        st.info("엑셀 파일을 드래그하거나 [Browse files] 버튼으로 선택하세요.")
        return

    det_year, det_month = _detect_year_month(uploaded.name)

    c1, c2 = st.columns(2)
    with c1:
        year = st.number_input(
            "년도", min_value=2000, max_value=2100,
            value=det_year if det_year else today.year,
            key="import_year",
        )
    with c2:
        month = st.number_input(
            "월", min_value=1, max_value=12,
            value=det_month if det_month else today.month,
            key="import_month",
        )

    if det_year and det_month:
        st.success(f"파일명 자동 감지: **{det_year}년 {det_month}월**")

    fmt_label = st.selectbox("파일 형식", list(FORMAT_OPTIONS.keys()), key="import_format")
    fmt       = FORMAT_OPTIONS[fmt_label]

    replace = st.radio(
        "가져오기 방식",
        ["기존 데이터 대체 (replace)", "기존 데이터에 추가 (append)"],
        key="import_mode",
    ).startswith("기존 데이터 대체")

    # Preview
    with st.expander("미리보기 (처음 20행)"):
        try:
            import pandas as pd
            uploaded.seek(0)
            df_preview = pd.read_excel(uploaded, header=None, nrows=20)
            st.dataframe(df_preview, use_container_width=True)
        except Exception as e:
            st.error(f"미리보기 오류: {e}")
        finally:
            uploaded.seek(0)

    if st.button("가져오기 실행", type="primary", key="import_run"):
        suffix = os.path.splitext(uploaded.name)[1]
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = tmp.name

            shifts = parse_excel_file(tmp_path, int(year), int(month), fmt=fmt)
            os.unlink(tmp_path)

            if not shifts:
                st.warning("파싱된 근무 데이터가 없습니다. 파일 형식을 확인하세요.")
            else:
                get_manager().import_shifts(shifts, int(year), int(month), replace=replace)
                n_emp = len({s.employee_name for s in shifts})
                st.success(
                    f"✅ **{len(shifts)}개** 근무 데이터 가져오기 완료!  \n"
                    f"직원 **{n_emp}명** / {year}년 {month}월"
                )
        except Exception as e:
            st.error(f"가져오기 실패: {e}")
            import traceback
            with st.expander("오류 상세"):
                st.code(traceback.format_exc())
