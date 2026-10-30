
import pandas as pd

file_path = "data/processed/limited_overs_performance.csv"
df = pd.read_csv(file_path)

players = {
    "Fakhar Zaman": "Batter",
    "Shadab Khan": "All-rounder",
    "Naseem Shah": "Bowler",
}

# Standardize text fields
df["player"] = df["player"].astype(str).str.strip()
df["match_type"] = df["match_type"].astype(str).str.strip().str.upper()
df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")

# Keep T20 records for the three players
filtered = df[
    df["player"].str.casefold().isin(
        [name.casefold() for name in players]
    )
    & (df["match_type"] == "T20")
].copy()

columns = [
    "match_id",
    "start_date",
    "match_type",
    "player",
    "runs",
    "balls_faced",
    "wickets",
    "runs_conceded",
    "balls_bowled",
]

for player, role in players.items():
    player_data = filtered[
        filtered["player"].str.casefold() == player.casefold()
    ].copy()

    # Newest first; match_id breaks ties when dates match
    player_data = player_data.sort_values(
        ["start_date", "match_id"],
        ascending=[False, False],
        na_position="last",
    )

    last_five = player_data.head(5)

    print("\n" + "=" * 65)
    print(f"{player} — {role} — Last Five T20 Records")
    print("=" * 65)

    if last_five.empty:
        print("No matching T20 records found.")
    else:
        print(last_five[columns].to_string(index=False))

    print(f"Total T20 records in dataset: {len(player_data)}")
    print(f"Records extracted: {len(last_five)}")

print("\nExtraction complete.")
