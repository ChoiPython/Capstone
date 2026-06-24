import os
import sqlite3
from datetime import datetime

# db_manager.py 파일이 있는 디렉토리에 DB를 고정
# → 어느 디렉토리에서 실행하든 항상 같은 DB를 바라봄
_DIR    = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DIR, "refrigerator.db")

# 1. DB 연결 (파일이 없으면 자동 생성됨)
def get_connection():
    return sqlite3.connect(DB_PATH)

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
            quantity INTEGER DEFAULT 1,
            unit TEXT DEFAULT '개',
            status TEXT DEFAULT '신선',
            Dday VARCHAR(10) DEFAULT "D-99",
            img_path TEXT DEFAULT "../img/milk.png",
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
#데이터 수정
def update_item(item_id: int, name: str, category_name: str, quantity: float, exp_date: str, status: str, Dday: str, unit: str = "", memo: str = "") -> bool:
    """
    주어진 식재료 ID의 데이터를 새로운 정보로 업데이트합니다.
    카테고리 이름이 바뀌었다면 자동으로 조회 및 생성하여 외래키를 맞춥니다.
    """
    try:
        # 1. 텍스트 카테고리를 ID로 변환 (없으면 자동 등록됨)
        category_id = get_or_create_category(category_name)

        conn = get_connection()
        cur = conn.cursor()
        
        # 2. ingredients 테이블의 정보를 업데이트
        cur.execute("""
            UPDATE ingredients 
            SET name = ?, 
                category_id = ?, 
                quentity = ?, 
                exp_date = ?, 
                status = ?,
                unit = ?,
                memo = ?, 
                Dday = ?
            WHERE id = ?
        """, (name, category_id, quantity, exp_date, status, unit, memo, Dday, item_id))
        
        conn.commit()
        conn.close()
        print(f"[DB 수정 완료]  이름={name} | 카테고리={category_name}(id={category_id})")
        return True

    except Exception as e:
        print(f"[DB 수정 실패] {e}")
        return False

# 4. 데이터 추가 (식재료 등록) - category_id FK 방식
def insert_item(name: str, category_name: str, exp_date: str, reg_date: str = "", Dday: str = "", status: str = "", 
quantity: int = 1, unit: str = "", image_path: str = "", memo: str = "") -> bool:
    print(f'{name} | {category_name} | {exp_date} | {reg_date} | {Dday} | {status} | {quantity} | {unit} | {image_path} | {memo}')
    try:
        category_id = get_or_create_category(category_name)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ingredients (name, category_id, exp_date, reg_date, Dday, status, quantity, unit, img_path, memo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, category_id, exp_date, reg_date, Dday, status, quantity, unit, image_path, memo)
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

def delete_ingredient(ingredient_id):
    """
    주어진 id를 가진 식재료 데이터를 ingredients 테이블에서 영구 삭제합니다.
    반환값: 성공 True / 실패 False
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # SQL의 DELETE 문을 사용해 해당 ID의 식재료만 삭제
        cur.execute("DELETE FROM ingredients WHERE id = ?", (ingredient_id,))
        
        conn.commit()
        conn.close()
        print(f"[DB 삭제 성공] 식재료 ID: {ingredient_id}가 정상적으로 삭제되었습니다.")
        return True

    except Exception as e:
        print(f"[DB 삭제 실패] 오류 발생: {e}")
        return False
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
    print(f"[DB 경로] {DB_PATH}")
    '''
    drop_table()
    create_table()
    '''
    print("\n현재 냉장고 재료 목록:")
    for item in select_all():
        print(f"  ID:{item[0]} | 이름:{item[1]} | 카테고리:{item[2]} | 유통기한:{item[3]} | 등록일:{item[4]} | 메모:{item[5]}")