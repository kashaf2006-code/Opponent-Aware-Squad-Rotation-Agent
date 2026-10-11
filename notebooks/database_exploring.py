
import sqlite3

db_path = "data/raw_data/cricket_all_tables.sqlite/cricket_all_tables.sqlite"
con = sqlite3.connect(db_path)

# Print every column with its position
columns = con.execute(
    "PRAGMA table_info(ball_by_ball)"
).fetchall()

print("=== COLUMN NAMES ===")
for col in columns:
    print(col[0], col[1])

print("\n=== EXTRAS EXAMPLES WITH COLUMN NAMES ===")
cur = con.execute("""
    SELECT *
    FROM ball_by_ball
    WHERE extras > 0
    LIMIT 3
""")

names = [description[0] for description in cur.description]
print(names)

for row in cur.fetchall():
    print(dict(zip(names, row)))

con.close()
