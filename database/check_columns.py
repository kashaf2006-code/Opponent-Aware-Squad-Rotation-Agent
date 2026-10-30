import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent / "cricket_agent.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("DATABASE TABLES:")

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
""")

for table in cursor.fetchall():
    print(table[0])

print("\nRECORD COUNTS:")

for table in ["simulation_runs", "fixtures", "recommendations"]:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    print(f"{table}: {cursor.fetchone()[0]}")

conn.close()