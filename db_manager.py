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
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,  
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

# 초기 실행 테스트
if __name__ == "__main__":
    create_table()