import sqlite3
import pandas as pd
from pathlib import Path


DATABASE_PATH = "data/raw_data/cricket_all_tables.sqlite/cricket_all_tables.sqlite"

OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


connection = sqlite3.connect(DATABASE_PATH)


query = """
WITH batting AS (
    SELECT
        match_id,
        start_date,
        match_type,
        striker AS player,
        SUM(runs_off_bat) AS runs,
        COUNT(*) AS balls_faced
    FROM ball_by_ball
    WHERE gender = 'male'
    AND start_date >= '2021-01-01'
    AND start_date <= '2026-12-31'
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
        SUM(runs_off_bat + extras) AS runs_conceded,
        COUNT(*) AS balls_bowled,
        SUM(
            CASE
                WHEN wicket_type IS NOT NULL
                AND wicket_type NOT IN (
                    'run out',
                    'retired hurt',
                    'retired not out',
                    'obstructing the field'
                )
                THEN 1
                ELSE 0
            END
        ) AS wickets
    FROM ball_by_ball
    WHERE gender = 'male'
    AND start_date >= '2021-01-01'
    AND start_date <= '2026-12-31'
    AND bowling_team = 'Pakistan'
    GROUP BY
        match_id,
        start_date,
        match_type,
        bowler
)

SELECT
    COALESCE(batting.match_id, bowling.match_id) AS match_id,
    COALESCE(batting.start_date, bowling.start_date) AS start_date,
    COALESCE(batting.match_type, bowling.match_type) AS match_type,
    COALESCE(batting.player, bowling.player) AS player,

    COALESCE(batting.runs, 0) AS runs,
    COALESCE(batting.balls_faced, 0) AS balls_faced,

    COALESCE(bowling.wickets, 0) AS wickets,
    COALESCE(bowling.runs_conceded, 0) AS runs_conceded,
    COALESCE(bowling.balls_bowled, 0) AS balls_bowled

FROM batting

FULL OUTER JOIN bowling
    ON batting.match_id = bowling.match_id
    AND batting.player = bowling.player

ORDER BY
    start_date,
    match_id,
    player;
"""


player_performance = pd.read_sql_query(query, connection)

connection.close()


output_path = OUTPUT_DIR / "player_match_performance_2021_2026.csv"

player_performance.to_csv(output_path, index=False)


print("Player-match performance records:", len(player_performance))
print("Unique players:", player_performance["player"].nunique())

print()
print("Saved to:", output_path)


if output_path.exists():
    print("Player batting and bowling performance data successfully created.")