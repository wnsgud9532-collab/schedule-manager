# ========================================================
# 구글 시트 데이터 가져오기 테스트
# ========================================================

import gspread
from google.oauth2.service_account import Credentials

# 설정 ----------------------------------------------------
키파일 = 'service-account.json'
시트ID = '1FkApqvnGIjdD7iRRs933YPNGQHZlhZ2Uw8ytUYS53uI'
# --------------------------------------------------------

print("🔑 구글에 인증 중...")
인증범위 = ['https://www.googleapis.com/auth/spreadsheets.readonly']
credentials = Credentials.from_service_account_file(키파일, scopes=인증범위)
gc = gspread.authorize(credentials)
print("✅ 인증 성공!\n")

print("📊 시트 여는 중...")
스프레드시트 = gc.open_by_key(시트ID)
print(f"✅ 시트 이름: {스프레드시트.title}\n")

print("📋 시트 탭 목록:")
for 탭 in 스프레드시트.worksheets():
    print(f"  - {탭.title}")
print()

print("🎯 대시보드 데이터 가져오는 중...")
대시보드 = 스프레드시트.worksheet('대시보드')
모든데이터 = 대시보드.get_all_values()

print("=" * 70)
print("📊 대시보드 내용")
print("=" * 70)
for 행 in 모든데이터:
    if all(셀 == '' for 셀 in 행):
        continue
    print(f"  {' | '.join(str(셀) for 셀 in 행 if 셀 != '')}")

print("=" * 70)
print(f"\n✅ 총 {len(모든데이터)}개 행 가져옴")