import sqlite3
import pandas as pd

db_path = "database/cricket_agent.db"
conn = sqlite3.connect(db_path)
df = pd.read_sql("SELECT * FROM players LIMIT 1", conn)
conn.close()

print("Available columns in players table:", df.columns.tolist())