#cretaing this file to help us sepearte the data of test matches from our files
import pandas as pd
from pathlib import Path

# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = BASE_DIR / "data" / "processed"

MATCHES_FILE = PROCESSED_DIR / "pakistan_matches.csv"
PLAYERS_FILE = PROCESSED_DIR / "pakistan_players_2021_2026.csv"
PERFORMANCE_FILE = PROCESSED_DIR / "player_match_performance_2021_2026.csv"

# Output files
LIMITED_MATCHES_FILE = PROCESSED_DIR / "limited_overs_matches.csv"
LIMITED_PLAYERS_FILE = PROCESSED_DIR / "limited_overs_players.csv"
LIMITED_PERFORMANCE_FILE = PROCESSED_DIR / "limited_overs_performance.csv"


# --------------------------------------------------
# Load data
# --------------------------------------------------

matches = pd.read_csv(MATCHES_FILE)
players = pd.read_csv(PLAYERS_FILE)
performance = pd.read_csv(PERFORMANCE_FILE)


print("\n" + "=" * 60)#it is use for formating the output in the console
print("OACSRA LIMITED-OVERS DATA FILTER")
print("=" * 60)


# --------------------------------------------------
# Filter ODI + T20 matches
# --------------------------------------------------

allowed_formats = ["ODI", "T20"]

limited_matches = matches[
    matches["match_type"].isin(allowed_formats)
].copy()#this code is alowing only those matches which are either ODI or T20 and creating a new dataframe called limited_matches


# --------------------------------------------------
# Get valid match IDs
# --------------------------------------------------

limited_match_ids = set(limited_matches["match_id"])


# --------------------------------------------------
# Filter players
# --------------------------------------------------

limited_players = players[
    players["match_id"].isin(limited_match_ids)
].copy()


# --------------------------------------------------
# Filter performance
# --------------------------------------------------

limited_performance = performance[
    performance["match_id"].isin(limited_match_ids)
].copy()


# --------------------------------------------------
# Save
# --------------------------------------------------

limited_matches.to_csv(
    LIMITED_MATCHES_FILE,
    index=False
)

limited_players.to_csv(
    LIMITED_PLAYERS_FILE,
    index=False
)

limited_performance.to_csv(
    LIMITED_PERFORMANCE_FILE,
    index=False
)


# --------------------------------------------------
# Summary
# --------------------------------------------------

print("\nOriginal matches:", len(matches))
print("Limited-overs matches:", len(limited_matches))

print("\nFormats:")
print(limited_matches["match_type"].value_counts())

print("\nPlayers:")
print(len(limited_players))

print("\nPerformance records:")
print(len(limited_performance))

print("\nOutput files created:")

print(LIMITED_MATCHES_FILE)
print(LIMITED_PLAYERS_FILE)
print(LIMITED_PERFORMANCE_FILE)

print("\n" + "=" * 60)
print("FILTER COMPLETE")
print("=" * 60)