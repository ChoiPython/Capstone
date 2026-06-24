import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# 1. 인증 및 초기화
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://final-d005b-default-rtdb.asia-southeast1.firebasedatabase.app/' # 콘솔에 적힌 URL 복사
})

# 2. 클라우드에 데이터 전송 (업데이트)
def sync_to_cloud(items):
    ref = db.reference('fridge_status') # 클라우드의 'fridge_status' 경로
    
    # SQLite 데이터를 딕셔너리 형태로 가공
    cloud_data = {}
    for item in items:
        # item[0]은 ID, item[1]은 이름... (SQLite 구조에 맞춤)
        cloud_data[f"item_{item[0]}"] = {
            "name": item[1],
            "category": item[2],
            "exp_date": item[3],
            "last_sync": str(item[4])
        }
    
    ref.set(cloud_data) # 전체 덮어쓰기 (또는 update 가능)
    print("클라우드 동기화 완료!")

# 테스트용 코드
if __name__ == "__main__":
    test_data = [(1, "우유", "유제품", "2026-04-15", "2026-03-23")]
    sync_to_cloud(test_data)