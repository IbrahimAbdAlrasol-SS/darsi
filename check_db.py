import sqlite3
import os

# Check which db file exists
print("=== DB FILE CHECK ===")
# Use the actual file from config
db_path = 'school_bot.db'
print(f"[OK] Using {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check tables
print("\n=== TABLES ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f"  - {table[0]}")

# Check exams if exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exams'")
if cursor.fetchone():
    print("\n=== EXAMS ===")
    cursor.execute('SELECT exam_id, assigned_teacher_id, created_by FROM exams ORDER BY exam_id DESC LIMIT 5')
    print('exam_id | assigned_teacher_id | created_by')
    print('-' * 80)
    for row in cursor.fetchall():
        print(f'{row[0]} | {row[1]} | {row[2]}')
else:
    print("\n[WARNING] exams table does not exist!")

print("\n=== TEACHERS FROM JSON ===")
import json
with open('teachers.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    print(json.dumps(data, indent=2, ensure_ascii=False))

# Test get_teacher_exams
print("\n=== TEST get_teacher_exams FOR TEACHER 7648810060 ===")
teacher_id = 7648810060

# First check columns
cursor.execute("PRAGMA table_info(exams)")
columns = cursor.fetchall()
print("Columns:")
for col in columns:
    print(f"  {col[0]}: {col[1]} ({col[2]})")

# Now test query
cursor.execute("""
    SELECT * FROM exams 
    WHERE assigned_teacher_id = ?
""", (teacher_id,))
teacher_exams = cursor.fetchall()
print(f"\nFound {len(teacher_exams)} exams for teacher {teacher_id}")

conn.close()

