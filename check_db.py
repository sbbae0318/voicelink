"""sessions.db 구조와 내용 확인."""
import json
import sqlite3

db_path = "test_recordings/sessions.db"

conn = sqlite3.connect(db_path)

print("=" * 60)
print("  sessions.db 구조 분석")
print("=" * 60)
print()

# 테이블 스키마
print("📋 테이블 스키마:")
cursor = conn.execute("PRAGMA table_info(sessions)")
for col in cursor.fetchall():
    print(f"  {col[1]:25} {col[2]:10} {'PK' if col[5] else ''}")

print()
print("-" * 60)

# 저장된 세션들
cursor = conn.execute("SELECT * FROM sessions")
rows = cursor.fetchall()
columns = [col[0] for col in cursor.description]

print(f"\n📊 저장된 세션: {len(rows)}개\n")

for row in rows:
    print("=" * 60)
    print(f"📁 Session ID: {row[0]}")
    print("-" * 60)
    print(f"  start_time:          {row[1]}")
    print(f"  end_time:            {row[2]}")
    print(f"  status:              {row[3]}")
    print(f"  tags:                {row[4]}")
    print(f"  transcription_status:{row[5]}")
    print(f"  transcription_path:  {row[6]}")
    print(f"  notes:               {row[7]}")
    
    # JSON data 파싱
    print()
    print("📦 전체 데이터 (data 컬럼):")
    data = json.loads(row[8])
    
    print(f"  session_id:      {data['session_id']}")
    print(f"  start_time:      {data['start_time']}")
    print(f"  end_time:        {data['end_time']}")
    print(f"  duration_seconds:{data['duration_seconds']}")
    print(f"  total_chunks:    {data['total_chunks']}")
    print(f"  avg_rms:         {data['avg_rms']:.6f}")
    print(f"  status:          {data['status']}")
    
    print()
    print("  🎵 청크 목록:")
    for i, chunk in enumerate(data['chunks']):
        status = "🔇" if chunk['is_silent'] else "🔊"
        print(f"    [{i+1}] {status} {chunk['file_path']}")
        print(f"        timestamp: {chunk['timestamp']}")
        print(f"        duration:  {chunk['duration_seconds']:.1f}초")
        print(f"        RMS:       {chunk['rms_level']:.6f}")

conn.close()
print()
print("=" * 60)
