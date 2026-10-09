import sqlite3
import pandas as pd
import os

# Define paths
db_path = "database/cricket_agent.db"
processed_data_dir = "data/processed"

# Connect to SQLite database (creates it if it doesn't exist)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Connected to SQLite database successfully.")

# Dictionary of CSV files and their target table names
csv_tables = {
    "limited_overs_matches.csv": "matches",
    "limited_overs_performance.csv": "performance",
    "limited_overs_players.csv": "players",
    "pakistan_matches.csv": "pakistan_matches",
    "pakistan_players_2021_2026.csv": "pakistan_players",
    "player_match_performance_2021_2026.csv": "match_performance"
}

# Load each CSV into SQLite
for filename, table_name in csv_tables.items():
    file_path = os.path.join(processed_data_dir, filename)
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"Loaded {filename} into table '{table_name}' successfully.")
    else:
        print(f"Warning: {filename} not found in {processed_data_dir}.")

# Close connection
conn.close()
print("Database setup complete!")