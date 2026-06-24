import os
from datetime import datetime, timedelta
import db_manager  # 조원이 만든 DB 매니저 임포트

def create_and_insert_dummies():
    print("=== [ON-ADD] 테스트용 더미 데이터 삽입 시작 ===")
    
    # 1. 혹시 테이블이 없다면 자동 생성
    db_manager.create_table()
    
    # 안전한 날짜 계산을 위해 오늘 날짜 기준점 설정
    today = datetime.now()
    
    # 2. 다양한 상태(신선, 임박, 만료)를 테스트할 수 있는 7가지 더미 데이터 정의
    # 구조: (품명, 카테고리명, 유통기한(YYYY-MM-DD), 메모)
    dummy_ingredients = [
        # [신선 제품들 - 유통기한이 많이 남음]
        (
            "서울우유 1L", 
            "유제품", 
            (today + timedelta(days=10)).strftime('%Y-%m-%d'), 
            "개봉 후 빨리 마실 것"
        ),
        (
            "제주 감귤", 
            "자연 신선식품", 
            (today + timedelta(days=14)).strftime('%Y-%m-%d'), 
            "냉장 보관 신선함 유지"
        ),
        (
            "시베리아산 연어", 
            "자연 신선식품", 
            (today + timedelta(days=5)).strftime('%Y-%m-%d'), 
            "회로 먹거나 구이용"
        ),
        
        # [임박 제품들 - 유통기한이 1~3일 남음]
        (
            "찌개용 두부", 
            "신선 가공식품", 
            (today + timedelta(days=2)).strftime('%Y-%m-%d'), 
            "내일 저녁 된장찌개 재료"
        ),
        (
            "흙당근", 
            "자연 신선식품", 
            (today + timedelta(days=1)).strftime('%Y-%m-%d'), 
            "카레용 볶음 대기 중"
        ),
        
        # [만료 제품들 - 유통기한이 이미 지남]
        (
            "한우 등심", 
            "냉장 육류", 
            (today - timedelta(days=3)).strftime('%Y-%m-%d'), 
            "아끼다 똥됐다 확인 필요"
        ),
        (
            "체다 슬라이스 치즈", 
            "신선 가공식품", 
            (today - timedelta(days=10)).strftime('%Y-%m-%d'), 
            "유통기한 만료 곰팡이 체크"
        )
    ]
    
    # 3. DB에 차례대로 삽입 실행
    success_count = 0
    for name, category, exp_date, memo in dummy_ingredients:
        # 조원이 만든 insert_ingredient 함수 활용
        success = db_manager.insert_item(
            name=name, 
            category_name=category, 
            exp_date=exp_date, 
            memo=memo
        )
        if success:
            success_count += 1
            
    print("\n========================================")
    print(f"🎉 더미 데이터 삽입 완료! (성공: {success_count}/{len(dummy_ingredients)}개)")
    print("========================================")

if __name__ == "__main__":
    create_and_insert_dummies()