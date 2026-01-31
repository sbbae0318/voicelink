import json
import os
import sqlite3
from pathlib import Path

# DB 경로
db_path = Path("recordings/sessions.db")

print(f"📂 DB 경로: {db_path.absolute()}")

if not db_path.exists():
    print("❌ DB 파일이 존재하지 않습니다!")
    exit(1)

try:
    with sqlite3.connect(db_path) as conn:
        print("\n📊 1. 테이블 스키마 확인 (`sessions` 테이블)")
        try:
            cursor = conn.execute("PRAGMA table_info(sessions)")
            columns = cursor.fetchall()
            for col in columns:
                print(f"   - {col[1]} ({col[2]})")
        except Exception as e:
            print(f"   스키마 조회 실패: {e}")

        print("\n🕒 2. 최근 5개 세션 데이터 확인")
        try:
            # title 컬럼이 없을 수도 있으므로 * 로 조회 후 인덱스 접근보다는 안전하게
            # 먼저 컬럼 이름 목록을 가져와서 쿼리 구성
            col_names = [col[1] for col in columns]
            
            # 조회할 필드
            target_cols = ['session_id', 'start_time', 'status']
            if 'title' in col_names:
                target_cols.append('title')
            
            query = f"SELECT {', '.join(target_cols)} FROM sessions ORDER BY start_time DESC LIMIT 5"
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            
            if not rows:
                print("   (데이터 없음)")
            else:
                for row in rows:
                    print(f"   - ID: {row[0]}")
                    print(f"     시간: {row[1]}")
                    print(f"     상태: {row[2]}")
                    if len(row) > 3:
                        print(f"     제목: {row[3]}")
                    print("     ---")
        except Exception as e:
            print(f"   데이터 조회 실패: {e}")

except Exception as e:
    print(f"❌ DB 접속 오류: {e}")
