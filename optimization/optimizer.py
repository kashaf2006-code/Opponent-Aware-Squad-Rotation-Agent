"""
OACSRA - simplified multi-fixture selection and rotation engine.

Workflow:
1. Coach supplies a 15-player squad and roles.
2. Coach supplies fixtures and priority (1-5).
3. OACSRA scores players using performance and workload.
4. It selects the highest-scoring valid XI for each fixture.
5. It explains PLAY/REST decisions and updates simulated workload.

Priority affects only the performance/workload balance.
Opponent-based weight adjustment and the separate rest penalty have been removed.

Run from the project root:
    python optimization/optimizer.py
"""

import itertools
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from formulas.performance import calculate_player_performance  # noqa: E402
from formulas.rest_days import calculate_rest_days  # noqa: E402
from formulas.workload import (  # noqa: E402
    ACTIVITY_REFERENCES,
    RECENCY_WEIGHTS,
    RECENT_APPEARANCES,
    calculate_appearance_workload,
)

# ---------------------------------------------------------------------
# Project settings
# ---------------------------------------------------------------------

DB_PATH = ROOT / "database" / "cricket_agent.db"

# These are the three processed files created by the data-extraction stage.
PERFORMANCE_CSV = ROOT / "data" / "processed" / "limited_overs_performance.csv"

HOME_TEAM = "Pakistan"
SUPPORTED_FORMATS = ("ODI", "T20")

SQUAD_SIZE = 15
XI_SIZE = 11

MIN_WICKETKEEPERS = 1
MIN_BATTING_OPTIONS = 5
MIN_BOWLING_OPTIONS = 4
MAX_ALL_ROUNDERS = 3

# (performance weight, workload weight)
# Priority is the coach's input; no opponent-based adjustment is applied.
PRIORITY_WEIGHTS = {
    1: (0.50, 0.50),
    2: (0.60, 0.40),
    3: (0.70, 0.30),
    4: (0.80, 0.20),
    5: (0.90, 0.10),
}
PRIORITY_LABELS = {"low": 1, "medium": 3, "high": 5}

# A small opportunity bonus for players with fewer than this many
# historical appearances. It is only applied to low-priority fixtures.
EMERGING_MAX_APPEARANCES = 5
EMERGING_PLAYER_BONUS = 5.0
EMERGING_PRIORITY_LIMIT = 2

# Neutral fallback when a player has no usable historical performance data.
# This is deliberately visible in the explanation; it is not real performance.
NEUTRAL_PERFORMANCE = 50.0


# ---------------------------------------------------------------------
# Sample inputs
# Replace these with values collected by the coach-facing UI.
# Each squad row is: (player_name, team, role).
# ---------------------------------------------------------------------

def default_squad():
    return [
        ("Mohammad Rizwan", HOME_TEAM, "Wicketkeeper"),
        ("Mohammad Haris", HOME_TEAM, "Wicketkeeper"),
        ("Babar Azam", HOME_TEAM, "Batter"),
        ("Fakhar Zaman", HOME_TEAM, "Batter"),
        ("Saim Ayub", HOME_TEAM, "Batter"),
        ("Sahibzada Farhan", HOME_TEAM, "Batter"),
        ("Hassan Nawaz", HOME_TEAM, "Batter"),
        ("Agha Salman", HOME_TEAM, "All-rounder"),
        ("Mohammad Nawaz", HOME_TEAM, "All-rounder"),
        ("Faheem Ashraf", HOME_TEAM, "Bowler"),
        ("Shadab Khan", HOME_TEAM, "All-rounder"),
        ("Shaheen Shah Afridi", HOME_TEAM, "Bowler"),
        ("Naseem Shah", HOME_TEAM, "Bowler"),
        ("Haris Rauf", HOME_TEAM, "Bowler"),
        ("Abrar Ahmed", HOME_TEAM, "Bowler"),
    ]


def default_fixtures():
    return [
        ("Australia", "ODI", "2026-11-01", 4),
        ("India", "T20", "2026-11-05", 5),
        ("England", "ODI", "2026-11-10", 3),
        ("South Africa", "T20", "2026-11-15", 1),
        ("New Zealand", "ODI", "2026-11-20", 2),
    ]


# ---------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------

def normalise_role(role):
    value = str(role).strip().casefold().replace("-", " ")
    aliases = {
        "wicketkeeper": "wicketkeeper",
        "wicket keeper": "wicketkeeper",
        "wk": "wicketkeeper",
        "wicketkeeper batter": "wicketkeeper",
        "wicket keeper batter": "wicketkeeper",
        "batter": "batter",
        "batsman": "batter",
        "bowler": "bowler",
        "all rounder": "all-rounder",
        "allrounder": "all-rounder",
    }
    if value not in aliases:
        raise ValueError(
            f"Unknown role {role!r}. Use Wicketkeeper, Batter, All-rounder or Bowler."
        )
    return aliases[value]


def normalise_format(fmt):
    value = str(fmt).strip().upper()
    if value == "T20I":
        value = "T20"
    if value not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format {fmt!r}. Use ODI or T20.")
    return value


def parse_priority(value):
    text = str(value).strip().casefold()
    if text in PRIORITY_LABELS:
        return PRIORITY_LABELS[text]

    try:
        priority = int(float(text))
    except ValueError as exc:
        raise ValueError("Priority must be 1-5, Low, Medium or High.") from exc

    if priority not in PRIORITY_WEIGHTS:
        raise ValueError("Priority must be between 1 and 5.")
    return priority


def validate_squad_input(squad_rows):
    if len(squad_rows) != SQUAD_SIZE:
        raise ValueError(f"The coach must provide exactly {SQUAD_SIZE} players.")

    names = [str(row[0]).strip().casefold() for row in squad_rows]
    if len(set(names)) != len(names):
        raise ValueError("The squad contains duplicate player names.")

    roles = [normalise_role(row[2]) for row in squad_rows]
    if roles.count("wicketkeeper") < MIN_WICKETKEEPERS:
        raise ValueError("The squad must contain at least one wicketkeeper.")
    if roles.count("all-rounder") > MAX_ALL_ROUNDERS:
        raise ValueError(
            f"The squad can contain at most {MAX_ALL_ROUNDERS} all-rounders."
        )


def validate_fixture_input(fixture_rows):
    if not fixture_rows:
        raise ValueError("Please provide at least one fixture.")

    for opponent, fmt, match_date, priority in fixture_rows:
        if not str(opponent).strip():
            raise ValueError("Every fixture needs an opponent.")
        normalise_format(fmt)
        date.fromisoformat(str(match_date).strip())
        parse_priority(priority)


# ---------------------------------------------------------------------
# Team composition rules
# ---------------------------------------------------------------------

def is_wicketkeeper(player):
    return player["kind"] == "wicketkeeper"


def is_batting_option(player):
    return player["kind"] in ("batter", "wicketkeeper", "all-rounder")


def is_bowling_option(player):
    return player["kind"] in ("bowler", "all-rounder")


def validate_lineup(xi, captain_name=None):
    if len(xi) != XI_SIZE:
        return False, f"Playing XI must contain exactly {XI_SIZE} players."

    if sum(is_wicketkeeper(p) for p in xi) < MIN_WICKETKEEPERS:
        return False, "The XI must include at least one wicketkeeper."

    if sum(is_batting_option(p) for p in xi) < MIN_BATTING_OPTIONS:
        return False, f"The XI needs at least {MIN_BATTING_OPTIONS} batting options."

    if sum(is_bowling_option(p) for p in xi) < MIN_BOWLING_OPTIONS:
        return False, f"The XI needs at least {MIN_BOWLING_OPTIONS} bowling options."

    if sum(p["kind"] == "all-rounder" for p in xi) > MAX_ALL_ROUNDERS:
        return False, f"The XI can contain at most {MAX_ALL_ROUNDERS} all-rounders."

    if captain_name and not any(
        p["name"].casefold() == captain_name.strip().casefold() for p in xi
    ):
        return False, "The coach-designated captain must be included in the XI."

    return True, "Lineup is valid."


# ---------------------------------------------------------------------
# SQLite storage
# ---------------------------------------------------------------------

def initialize_database_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS simulation_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            description TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS squad_players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            person_name TEXT,
            team TEXT,
            role TEXT,
            is_wicketkeeper INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS fixtures (
            fixture_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            opponent TEXT,
            format TEXT,
            match_date TEXT,
            priority TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            rec_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            fixture_id INTEGER,
            person_name TEXT,
            team TEXT,
            role TEXT,
            decision TEXT,
            reason TEXT,
            net_score REAL,
            performance_score REAL,
            played INTEGER,
            rest_days INTEGER,
            workload_before REAL,
            workload_after REAL
        )
    """)
    conn.commit()


def create_run(conn, squad_rows, fixture_rows, description):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO simulation_runs (timestamp, description) VALUES (?, ?)",
        (datetime.now().isoformat(timespec="seconds"), description),
    )
    run_id = cursor.lastrowid

    for name, team, role in squad_rows:
        clean_role = normalise_role(role)
        cursor.execute(
            """
            INSERT INTO squad_players
                (run_id, person_name, team, role, is_wicketkeeper)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, name, team, role, int(clean_role == "wicketkeeper")),
        )

    for opponent, fmt, match_date, priority in fixture_rows:
        cursor.execute(
            """
            INSERT INTO fixtures (run_id, opponent, format, match_date, priority)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, opponent, normalise_format(fmt), str(match_date), str(priority)),
        )

    conn.commit()
    return run_id


def load_fixtures(conn, run_id):
    rows = conn.execute(
        """
        SELECT fixture_id, opponent, format, match_date, priority
        FROM fixtures
        WHERE run_id = ?
        ORDER BY match_date, fixture_id
        """,
        (run_id,),
    ).fetchall()

    fixtures = []
    for fixture_id, opponent, fmt, match_date, priority in rows:
        fixtures.append({
            "id": fixture_id,
            "opponent": opponent,
            "format": normalise_format(fmt),
            "date": date.fromisoformat(str(match_date).strip()),
            "priority": parse_priority(priority),
        })
    return fixtures


# ---------------------------------------------------------------------
# Historical data and player state
# ---------------------------------------------------------------------

def load_history():
    if not PERFORMANCE_CSV.exists():
        raise FileNotFoundError(
            f"Performance file not found: {PERFORMANCE_CSV}\n"
            "Check that pakistan_performance_2021_2026.csv exists in data/processed."
        )

    data = pd.read_csv(PERFORMANCE_CSV)

    required = {
        "match_id", "start_date", "match_type", "player",
        "runs", "balls_faced", "wickets", "runs_conceded", "balls_bowled",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(
            "Performance CSV is missing required columns: "
            + ", ".join(sorted(missing))
        )

    data["start_date"] = pd.to_datetime(data["start_date"], errors="coerce")
    data = data.dropna(subset=["start_date", "player"])
    data["match_type"] = data["match_type"].astype(str).str.strip().str.upper()
    data["_key"] = data["player"].astype(str).str.strip().str.casefold()
    data = data[data["match_type"].isin(SUPPORTED_FORMATS)]

    return data.sort_values(
        ["start_date", "match_id"],
        ascending=[False, False],
        kind="stable",
    )


def load_players(conn, run_id, history):
    rows = conn.execute(
        """
        SELECT player_id, person_name, team, role
        FROM squad_players
        WHERE run_id = ?
        ORDER BY player_id
        """,
        (run_id,),
    ).fetchall()

    players = []
    for player_id, name, team, role in rows:
        kind = normalise_role(role)
        player_history = history[
            history["_key"] == str(name).strip().casefold()
        ].copy()

        history_workload = {}
        for fmt in SUPPORTED_FORMATS:
            recent = player_history[
                player_history["match_type"] == fmt
            ].head(RECENT_APPEARANCES)

            history_workload[fmt] = [
                calculate_appearance_workload(
                    row.balls_faced or 0,
                    row.balls_bowled or 0,
                    fmt,
                    kind,
                )
                for row in recent.itertuples()
            ]

        last_played = (
            player_history["start_date"].iloc[0].date()
            if not player_history.empty
            else None
        )

        players.append({
            "id": player_id,
            "name": name,
            "team": team,
            "role": role,
            "kind": kind,
            "rows": player_history,
            "history_workload": history_workload,
            "simulated_fixture_loads": [],
            "last_played": last_played,
            "appearances": 0,
        })

    return players


def current_workload(player, fmt):
    """
    Recent fixture activity: simulated fixtures first, then real history.
    A rested simulated fixture contributes zero activity.
    """
    values = (
        player["simulated_fixture_loads"] + player["history_workload"][fmt]
    )[:RECENT_APPEARANCES]

    if not values:
        return 0.0

    weights = RECENCY_WEIGHTS[:len(values)]
    return sum(value * weight for value, weight in zip(values, weights)) / sum(weights)


def typical_play_workload(player, fmt):
    recent = player["rows"][
        player["rows"]["match_type"] == fmt
    ].head(RECENT_APPEARANCES)

    if recent.empty:
        recent = player["rows"].head(RECENT_APPEARANCES)

    if recent.empty:
        references = ACTIVITY_REFERENCES[fmt]
        return calculate_appearance_workload(
            references["balls_faced"] / 2,
            references["balls_bowled"] / 2,
            fmt,
            player["kind"],
        )

    return calculate_appearance_workload(
        recent["balls_faced"].fillna(0).mean(),
        recent["balls_bowled"].fillna(0).mean(),
        fmt,
        player["kind"],
    )


_performance_cache = {}


def get_performance(player, fmt):
    """
    Use the requested format first, then the other limited-overs format.
    If neither has data, use a neutral 50 and clearly flag the fallback.
    """
    cache_key = (player["name"].casefold(), fmt, player["kind"])
    if cache_key in _performance_cache:
        return _performance_cache[cache_key]

    other_format = "ODI" if fmt == "T20" else "T20"

    for candidate_format in (fmt, other_format):
        try:
            score = calculate_player_performance(
                player["name"],
                candidate_format,
                player["kind"],
                str(PERFORMANCE_CSV),
            )
            note = (
                ""
                if candidate_format == fmt
                else f"No {fmt} history; used {candidate_format} performance."
            )
            result = (float(score), note)
            _performance_cache[cache_key] = result
            return result
        except ValueError:
            continue

    result = (
        NEUTRAL_PERFORMANCE,
        "No historical performance data; neutral score used.",
    )
    _performance_cache[cache_key] = result
    return result


def emerging_player_bonus(player, priority):
    """
    Give a small opportunity bonus to players with fewer than five
    historical player-match records, only in low-priority fixtures.
    """
    appearances = len(player["rows"])
    is_emerging = appearances < EMERGING_MAX_APPEARANCES
    if is_emerging and priority <= EMERGING_PRIORITY_LIMIT:
        return EMERGING_PLAYER_BONUS, True
    return 0.0, is_emerging


# ---------------------------------------------------------------------
# XI selection
# ---------------------------------------------------------------------

def select_best_xi(players, scores, captain_name=None):
    """
    Test all possible XIs from the coach's 15-player squad.
    Keep valid combinations and choose the one with the highest total score.
    """
    best_combination = None
    best_total = float("-inf")

    if captain_name:
        matching = [
            i for i, player in enumerate(players)
            if player["name"].strip().casefold() == captain_name.strip().casefold()
        ]
        if len(matching) != 1:
            raise ValueError("The coach-designated captain must be in the 15-player squad.")

    for combination in itertools.combinations(range(len(players)), XI_SIZE):
        xi = [players[i] for i in combination]

        valid, _ = validate_lineup(xi, captain_name)
        if not valid:
            continue

        total_score = sum(scores[i] for i in combination)
        if total_score > best_total:
            best_combination = combination
            best_total = total_score

    if best_combination is None:
        raise ValueError(
            "No valid Playing XI can be formed. Check the squad's roles, "
            "wicketkeeper, batting, bowling and all-rounder requirements."
        )

    return set(best_combination)


# ---------------------------------------------------------------------
# Fixture decision process
# ---------------------------------------------------------------------

def process_fixture(players, fixture, captain_name=None):
    if len(players) != SQUAD_SIZE:
        raise ValueError(f"Expected {SQUAD_SIZE} squad players; found {len(players)}.")

    fmt = fixture["format"]
    performance_weight, workload_weight = PRIORITY_WEIGHTS[fixture["priority"]]

    player_details = []

    for player in players:
        performance, performance_note = get_performance(player, fmt)
        workload = current_workload(player, fmt)
        try:
            rest_days = calculate_rest_days(player["last_played"], fixture["date"])
        except (TypeError, ValueError):
            rest_days = None

        bonus, is_emerging = emerging_player_bonus(
            player, fixture["priority"]
        )

        score = (
            performance_weight * performance
            + workload_weight * (100 - workload)
            + bonus
        )

        player_details.append({
            "performance": performance,
            "performance_note": performance_note,
            "workload": workload,
            "rest_days": rest_days,
            "emerging_bonus": bonus,
            "is_emerging": is_emerging,
            "score": score,
        })

    chosen = select_best_xi(
        players,
        [detail["score"] for detail in player_details],
        captain_name,
    )

    xi = [players[index] for index in sorted(chosen)]
    valid, message = validate_lineup(xi, captain_name)
    if not valid:
        raise ValueError(message)

    decisions = []

    for index, (player, detail) in enumerate(zip(players, player_details)):
        plays = index in chosen

        if plays:
            reason = (
                f"Selected with score {detail['score']:.1f}; "
                f"performance {detail['performance']:.1f}, "
                f"workload {detail['workload']:.1f}."
            )
            if detail["emerging_bonus"] > 0:
                reason += (
                    f" Includes {detail['emerging_bonus']:.1f} emerging-player "
                    "opportunity bonus."
                )
        else:
            reason = (
                f"Not selected in the highest-scoring valid XI "
                f"(score {detail['score']:.1f})."
            )
            if detail["workload"] >= 50:
                reason += f" Recent workload is high ({detail['workload']:.1f})."

        if detail["performance_note"]:
            reason += " " + detail["performance_note"]

        # Update the simulated state for the next fixture.
        if plays:
            simulated_load = typical_play_workload(player, fmt)
            player["simulated_fixture_loads"].insert(0, simulated_load)
            player["last_played"] = fixture["date"]
            player["appearances"] += 1
        else:
            player["simulated_fixture_loads"].insert(0, 0.0)

        player["simulated_fixture_loads"] = (
            player["simulated_fixture_loads"][:RECENT_APPEARANCES]
        )

        workload_after = current_workload(player, fmt)

        decisions.append({
            "player": player,
            "decision": "PLAY" if plays else "REST",
            "reason": reason,
            "score": detail["score"],
            "performance": detail["performance"],
            "workload_before": detail["workload"],
            "workload_after": workload_after,
            "rest_days": detail["rest_days"],
            "emerging_bonus": detail["emerging_bonus"],
        })

    return decisions, (performance_weight, workload_weight)


def save_fixture_recommendations(conn, run_id, fixture, decisions):
    conn.executemany(
        """
        INSERT INTO recommendations
            (run_id, fixture_id, person_name, team, role, decision, reason,
             net_score, performance_score, played, rest_days,
             workload_before, workload_after)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                fixture["id"],
                item["player"]["name"],
                item["player"]["team"],
                item["player"]["role"],
                item["decision"],
                item["reason"],
                round(item["score"], 2),
                round(item["performance"], 2),
                int(item["decision"] == "PLAY"),
                item["rest_days"],  # Informational only; no separate score penalty.
                round(item["workload_before"], 2),
                round(item["workload_after"], 2),
            )
            for item in decisions
        ],
    )
    conn.commit()


# ---------------------------------------------------------------------
# Run the multi-fixture simulation
# ---------------------------------------------------------------------

def run_multi_fixture_simulation(
    squad_rows=None,
    fixture_rows=None,
    captain_name=None,
):
    if squad_rows is None:
        squad_rows = default_squad()
    if fixture_rows is None:
        fixture_rows = default_fixtures()

    validate_squad_input(squad_rows)
    validate_fixture_input(fixture_rows)

    if captain_name and not any(
        str(row[0]).strip().casefold() == captain_name.strip().casefold()
        for row in squad_rows
    ):
        raise ValueError("The captain must be one of the 15 selected squad players.")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _performance_cache.clear()

    conn = sqlite3.connect(DB_PATH)

    try:
        initialize_database_tables(conn)
        history = load_history()

        run_id = create_run(
            conn,
            squad_rows,
            fixture_rows,
            description="OACSRA multi-fixture planning run",
        )

        players = load_players(conn, run_id, history)
        fixtures = load_fixtures(conn, run_id)

        print(
            f"Simulation run #{run_id}: "
            f"{len(players)} players, {len(fixtures)} fixtures\n"
        )

        for number, fixture in enumerate(fixtures, start=1):
            decisions, weights = process_fixture(
                players, fixture, captain_name
            )
            save_fixture_recommendations(
                conn, run_id, fixture, decisions
            )

            performance_weight, workload_weight = weights

            print(
                f"=== Fixture {number}: {fixture['format']} vs "
                f"{fixture['opponent']} on {fixture['date']} "
                f"(priority {fixture['priority']}) ==="
            )
            print(
                f"Weights: performance {performance_weight:.0%}, "
                f"workload {workload_weight:.0%}"
            )
            print(
                "PLAY:",
                ", ".join(
                    item["player"]["name"]
                    for item in decisions if item["decision"] == "PLAY"
                ),
            )
            print(
                "REST:",
                ", ".join(
                    item["player"]["name"]
                    for item in decisions if item["decision"] == "REST"
                ),
            )

            for item in decisions:
                print(
                    f"- {item['player']['name']}: "
                    f"{item['decision']} — {item['reason']}"
                )
            print()

        print(
            f"All {len(fixtures)} fixtures processed and saved "
            f"(run #{run_id})."
        )
        print("Note: these are recommendations for coach review, not automatic final selections.")

    finally:
        conn.close()


if __name__ == "__main__":
    run_multi_fixture_simulation()
