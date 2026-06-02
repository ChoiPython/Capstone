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

# 3. 카테고리 ID 조회 (없으면 자동 생성)
def get_or_create_category(name: str) -> int:
    """
    카테고리 이름으로 ID 반환.
    DB에 없는 카테고리면 자동 등록 후 ID 반환.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM categories WHERE name = ?", (name,))
    row = cur.fetchone()

    if row:
        category_id = row[0]
    else:
        cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        category_id = cur.lastrowid
        print(f"[카테고리 자동 등록] '{name}' (id={category_id})")

    conn.close()
    return category_id

# 4. 데이터 추가 (식재료 등록) - category_id FK 방식으로 수정
def insert_item(name: str, category_name: str, exp_date: str, memo: str = "") -> bool:
    """
    식재료를 DB에 저장.
    category_name → categories 테이블에서 id 조회 후 FK로 저장.
    반환값: 성공 True / 실패 False
    """
    try:
        category_id = get_or_create_category(category_name)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ingredients (name, category_id, exp_date, memo) VALUES (?, ?, ?, ?)",
            (name, category_id, exp_date, memo)
        )
        conn.commit()
        conn.close()
        print(f"[DB 저장 완료] 이름={name} | 카테고리={category_name}(id={category_id}) | 유통기한={exp_date}")
        return True

    except Exception as e:
        print(f"[DB 저장 실패] {e}")
        return False

# 5. 데이터 조회 (전체 목록 - 카테고리 이름 JOIN)
def select_all():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT i.id, i.name, c.name, i.exp_date, i.reg_date, i.memo
        FROM ingredients i
        LEFT JOIN categories c ON i.category_id = c.id
        ORDER BY i.exp_date ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

# 6. 테이블 삭제
def drop_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS ingredients")
    cur.execute("DROP TABLE IF EXISTS categories")
    conn.commit()
    conn.close()
    print("테이블 삭제 완료!")

# 초기 실행 테스트
if __name__ == "__main__":
    '''
    drop_table()
    create_table()
    '''

    print("\n현재 냉장고 재료 목록:")
    for item in select_all():
        print(f"  ID:{item[0]} | 이름:{item[1]} | 카테고리:{item[2]} | 유통기한:{item[3]} | 등록일:{item[4]} | 메모:{item[5]}")