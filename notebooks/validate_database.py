import pandas as pd
from pathlib import Path

# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

MATCHES_FILE = DATA_DIR / "limited_overs_matches.csv"
PLAYERS_FILE = DATA_DIR / "limited_overs_players.csv"
PERFORMANCE_FILE = DATA_DIR / "limited_overs_performance.csv"


# --------------------------------------------------
# Load data
# --------------------------------------------------

matches = pd.read_csv(MATCHES_FILE)
players = pd.read_csv(PLAYERS_FILE)
performance = pd.read_csv(PERFORMANCE_FILE)


print("\n" + "=" * 60)
print("OACSRA FINAL DATA VALIDATION")
print("=" * 60)


# --------------------------------------------------
# 1. Dataset size
# --------------------------------------------------

print("\n[1] DATASET SIZE")
print("-" * 60)

print("Matches:", len(matches))
print("Player records:", len(players))
print("Performance records:", len(performance))


# --------------------------------------------------
# 2. Match validation
# --------------------------------------------------

print("\n[2] MATCH VALIDATION")
print("-" * 60)

print("\nFormats:")
print(matches["match_type"].value_counts())

print("\nTest matches remaining:",
      (matches["match_type"] == "TEST").sum())

print("\nTeams other than Pakistan-only matches:")

wrong_matches = matches[
    (matches["team1"] != "Pakistan") &
    (matches["team2"] != "Pakistan")
]

print(len(wrong_matches))


# --------------------------------------------------
# 3. Duplicate validation
# --------------------------------------------------

print("\n[3] DUPLICATES")
print("-" * 60)

print("Duplicate matches:",
      matches.duplicated().sum())

print("Duplicate player records:",
      players.duplicated().sum())

print("Duplicate performance records:",
      performance.duplicated().sum())


# --------------------------------------------------
# 4. Match ID consistency
# --------------------------------------------------

print("\n[4] MATCH ID CONSISTENCY")
print("-" * 60)

match_ids = set(matches["match_id"])

player_match_ids = set(players["match_id"])

performance_match_ids = set(performance["match_id"])


print(
    "Player records with unknown match:",
    len(player_match_ids - match_ids)
)

print(
    "Performance records with unknown match:",
    len(performance_match_ids - match_ids)
)


# --------------------------------------------------
# 5. Pakistan player validation
# --------------------------------------------------

print("\n[5] PLAYER VALIDATION")
print("-" * 60)

non_pakistan = players[
    players["team"] != "Pakistan"
]

print(
    "Non-Pakistan player records:",
    len(non_pakistan)
)

print(
    "Unique players:",
    players["person_name"].nunique()
)


# --------------------------------------------------
# 6. Missing values
# --------------------------------------------------

print("\n[6] MISSING VALUES")
print("-" * 60)

print(
    "Missing values in matches:",
    matches.isnull().sum().sum()
)

print(
    "Missing values in players:",
    players.isnull().sum().sum()
)

print(
    "Missing values in performance:",
    performance.isnull().sum().sum()
)


# --------------------------------------------------
# 7. Date validation
# --------------------------------------------------

print("\n[7] DATE VALIDATION")
print("-" * 60)

dates = pd.to_datetime(
    matches["start_date"],
    errors="coerce"
)

print("Earliest match:", dates.min())
print("Latest match:", dates.max())
print("Invalid dates:", dates.isna().sum())


# --------------------------------------------------
# 8. Performance sanity check
# --------------------------------------------------

print("\n[8] PERFORMANCE SANITY CHECK")
print("-" * 60)

numeric_columns = [
    "runs",
    "balls_faced",
    "wickets",
    "runs_conceded",
    "balls_bowled"
]

for column in numeric_columns:
    print(
        f"{column} negative values:",
        (performance[column] < 0).sum()
    )


# --------------------------------------------------
# Final
# --------------------------------------------------

print("\n" + "=" * 60)
print("FINAL VALIDATION COMPLETE")
print("=" * 60)