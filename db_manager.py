import sqlite3
from datetime import datetime

# 1. DB 연결 (파일이 없으면 자동 생성됨)
def get_connection():
    return sqlite3.connect("refrigerator.db")

# 2. 테이블 생성 (초기 1회 실행)
def create_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER REFERENCES categories(id),
            exp_date TEXT NOT NULL,
            reg_date TEXT DEFAULT (datetime('now', 'localtime')),
            memo TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("테이블 생성 완료!")

# 3. 데이터 추가 (식재료 등록)
def insert_item(name, category, exp_date, memo=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO ingredients (name, category, exp_date, memo) VALUES (?, ?, ?, ?)", 
                (name, category, exp_date, memo))
    conn.commit()
    conn.close()
    print(f"{name} 등록 완료!")

# 4. 데이터 조회 (전체 목록 보기)
def select_all():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ingredients ORDER BY exp_date ASC") # 유통기한 순 정렬
    rows = cur.fetchall()
    conn.close()
    return rows

# 5. 테이블 삭제
def drop_table():
    conn = get_connection()
    cur = conn.cursor()

    # FK 참조 순서 때문에 자식 테이블부터 삭제
    cur.execute("DROP TABLE IF EXISTS ingredients")
    cur.execute("DROP TABLE IF EXISTS categories")

    conn.commit()
    conn.close()
    print("테이블 삭제 완료!")

# 초기 실행 테스트
if __name__ == "__main__":
    drop_table()  # 기존 테이블 삭제 (테스트용)
    create_table()
    # 예시 데이터 추가
    insert_item("우유", "유제품", "2024-07-01", "냉장 보관")
    insert_item("계란", "달걀류", "2024-07-10", "냉장 보관")
    print("현재 냉장고 재료 목록:")
    items = select_all()
    for item in items:
        print(f"ID: {item[0]}, 이름: {item[1]}, 카테고리: {item[2]}, 유통기한: {item[3]}, 등록일: {item[4]}, 메모: {item[5]}")