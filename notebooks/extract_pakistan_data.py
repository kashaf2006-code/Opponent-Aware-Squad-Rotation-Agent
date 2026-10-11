
import sqlite3
import pandas as pd
from pathlib import Path


# ----------------------------------------
# 1. File paths
# ----------------------------------------

DATABASE_PATH = (
    "data/raw_data/cricket_all_tables.sqlite/"
    "cricket_all_tables.sqlite"
)

OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = OUTPUT_DIR / "player_match_performance_2021_2026.csv"


# ----------------------------------------
# 2. SQL query
# ----------------------------------------

query = """
WITH batting AS (
    SELECT
        match_id,
        start_date,
        match_type,
        striker AS player,

        SUM(COALESCE(runs_off_bat, 0)) AS runs,

        SUM(
            CASE
                WHEN COALESCE(wides, 0) = 0 THEN 1
                ELSE 0
            END
        ) AS balls_faced

    FROM ball_by_ball

    WHERE gender = 'male'
      AND start_date >= '2021-01-01'
      AND start_date < '2027-01-01'
      AND batting_team = 'Pakistan'

    GROUP BY
        match_id,
        start_date,
        match_type,
        striker
),

bowling AS (
    SELECT
        match_id,
        start_date,
        match_type,
        bowler AS player,

        SUM(
            COALESCE(runs_off_bat, 0)
            + COALESCE(wides, 0)
            + COALESCE(noballs, 0)
        ) AS runs_conceded,

        SUM(
            CASE
                WHEN COALESCE(wides, 0) = 0
                 AND COALESCE(noballs, 0) = 0
                THEN 1
                ELSE 0
            END
        ) AS balls_bowled,

        SUM(
            CASE
                WHEN LOWER(TRIM(wicket_type)) IN (
                    'bowled',
                    'caught',
                    'caught and bowled',
                    'lbw',
                    'stumped',
                    'hit wicket'
                )
                THEN 1
                ELSE 0
            END
        ) AS wickets

    FROM ball_by_ball

    WHERE gender = 'male'
      AND start_date >= '2021-01-01'
      AND start_date < '2027-01-01'
      AND bowling_team = 'Pakistan'
      AND bowler IS NOT NULL

    GROUP BY
        match_id,
        start_date,
        match_type,
        bowler
)

SELECT
    COALESCE(b.match_id, l.match_id) AS match_id,
    COALESCE(b.start_date, l.start_date) AS start_date,
    COALESCE(b.match_type, l.match_type) AS match_type,
    COALESCE(b.player, l.player) AS player,

    COALESCE(b.runs, 0) AS runs,
    COALESCE(b.balls_faced, 0) AS balls_faced,

    COALESCE(l.wickets, 0) AS wickets,
    COALESCE(l.runs_conceded, 0) AS runs_conceded,
    COALESCE(l.balls_bowled, 0) AS balls_bowled

FROM batting b

FULL OUTER JOIN bowling l
    ON b.match_id = l.match_id
   AND b.player = l.player

ORDER BY
    start_date,
    match_id,
    player;
"""


# ----------------------------------------
# 3. Extract data from SQLite
# ----------------------------------------

try:
    with sqlite3.connect(DATABASE_PATH) as connection:
        player_performance = pd.read_sql_query(
            query,
            connection
        )

    # ------------------------------------
    # 4. Save CSV file
    # ------------------------------------

    player_performance.to_csv(
        OUTPUT_PATH,
        index=False
    )

    # ------------------------------------
    # 5. Display extraction summary
    # ------------------------------------

    print("Player performance data created successfully.")
    print()
    print("Total records:", len(player_performance))
    print(
        "Unique players:",
        player_performance["player"].nunique()
    )
    print(
        "Unique matches:",
        player_performance["match_id"].nunique()
    )

    print()
    print("Match types:")
    print(
        player_performance["match_type"].value_counts(
            dropna=False
        )
    )

    print()
    print("Date range:")
    print("First match:", player_performance["start_date"].min())
    print("Last match:", player_performance["start_date"].max())

    print()
    print("Missing values:")
    print(player_performance.isnull().sum())

    print()
    print("Sample records:")
    print(player_performance.head())

    print()
    print("Saved to:", OUTPUT_PATH)

except (sqlite3.Error, pd.errors.DatabaseError, OSError) as error:
    print("Error while extracting player performance data:")
    print(error)
