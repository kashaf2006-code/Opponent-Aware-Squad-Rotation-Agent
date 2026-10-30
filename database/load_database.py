
from pathlib import Path
import sqlite3

# Project database location
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cricket_agent.db"


def initialize_database():
    """Create the application database and required tables."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Simulation runs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Squad players
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS squad_players (
                player_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                player_name TEXT NOT NULL,
                role TEXT,
                FOREIGN KEY (run_id)
                    REFERENCES simulation_runs(run_id)
            )
        """)

        # 3. Fixtures
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fixtures (
                fixture_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                opponent TEXT,
                match_type TEXT,
                match_date TEXT,
                priority INTEGER,
                FOREIGN KEY (run_id)
                    REFERENCES simulation_runs(run_id)
            )
        """)

        # 4. Recommendations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendations (
                recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                fixture_id INTEGER,
                player_name TEXT NOT NULL,
                decision TEXT,
                score REAL,
                performance_score REAL,
                workload_score REAL,
                explanation TEXT,
                FOREIGN KEY (run_id)
                    REFERENCES simulation_runs(run_id),
                FOREIGN KEY (fixture_id)
                    REFERENCES fixtures(fixture_id)
            )
        """)

        conn.commit()

        print("\nDatabase initialized successfully!")
        print("Database location:", DB_PATH)

        print("\nDatabase tables:")

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
        """)

        for row in cursor.fetchall():
            print("-", row[0])

    except sqlite3.Error as error:
        conn.rollback()
        print("Database initialization failed:", error)
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    initialize_database()
