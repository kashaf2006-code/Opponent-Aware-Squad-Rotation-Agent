import sqlite3

# Location of our raw cricket database
DATABASE_PATH = "data/raw_data/cricket_all_tables.sqlite/cricket_all_tables.sqlite"

# Connect Python to the SQLite database
connection = sqlite3.connect(DATABASE_PATH)

# Create a cursor so we can send SQL commands
cursor = connection.cursor()

# Ask SQLite for all tables
cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table';
""")

# Get the results
tables = cursor.fetchall()

print("Tables in the OACSRA cricket database:")

for table in tables:

    table_name = table[0]

    print("\n" + "=" * 60)
    print(f"Columns in table: {table_name}")
    print("=" * 60)

    cursor.execute(f"PRAGMA table_info({table_name});")

    columns = cursor.fetchall()

    for column in columns:
        column_id = column[0]
        column_name = column[1]
        data_type = column[2]

        print(f"{column_id}: {column_name} ({data_type})")
        tables_to_inspect = [
    "match_info",
    "match_players",
    "people",
    "ball_by_ball"
]

for table_name in tables_to_inspect:

    print("\n" + "=" * 60)
    print(f"Sample rows from: {table_name}")
    print("=" * 60)

    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")

    rows = cursor.fetchall()

    for row in rows:
        print(row)

# Close the database connection
connection.close()