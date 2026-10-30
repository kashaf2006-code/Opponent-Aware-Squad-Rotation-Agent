
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# ============================================================
# OACSRA - BATTING FORMULA VALIDATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from formulas.performance import (  # noqa: E402
    BENCHMARKS,
    calculate_batting_scores,
)

DATA_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "limited_overs_performance.csv"
)

def find_column(df, possible_names):
    """Find a column without depending on capitalization."""
    lookup = {str(c).strip().lower(): c for c in df.columns}

    for name in possible_names:
        if name.lower() in lookup:
            return lookup[name.lower()]

    raise ValueError(
        f"Could not find any of these columns: {possible_names}\n"
        f"Available columns: {list(df.columns)}"
    )


def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_FILE}\n"
            "Check that limited_overs_performance.csv exists "
            "inside data/processed."
        )

    df = pd.read_csv(DATA_FILE)

    # Identify dataset columns
    player_col = find_column(
        df, ["player", "player_name", "batter", "name"]
    )
    format_col = find_column(
        df, ["match_type", "format", "match_format"]
    )
    runs_col = find_column(
        df, ["runs", "runs_scored", "batter_runs"]
    )
    balls_col = find_column(
        df, ["balls_faced", "balls", "bf"]
    )

    df[format_col] = (
        df[format_col].astype(str).str.strip().str.upper()
    )

    # Convert numeric data safely
    for col in [runs_col, balls_col]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Use valid T20 and ODI records only
    df = df[df[format_col].isin(["T20", "ODI"])].copy()
    print("Formats found:", df[format_col].value_counts().to_dict())
    print("Benchmarks:", list(BENCHMARKS.keys()))

    # Exclude invalid or missing runs and balls
    valid = (
        df[runs_col].notna()
        & df[balls_col].notna()
        & np.isfinite(df[runs_col])
        & np.isfinite(df[balls_col])
        & (df[runs_col] >= 0)
        & (df[balls_col] > 0)
    )

    invalid_count = int((~valid).sum())
    df = df[valid].copy()

    df[runs_col] = df[runs_col].astype(float)
    df[balls_col] = df[balls_col].astype(float)

    scores = [
        calculate_batting_scores(runs, balls, fmt)
        for runs, balls, fmt in zip(
            df[runs_col], df[balls_col], df[format_col]
        )
    ]
    df["actual_strike_rate"] = [
        score.actual_strike_rate for score in scores
    ]
    df["runs_score"] = [score.run_score for score in scores]
    df["sr_score"] = [score.strike_rate_score for score in scores]
    df["base_batting_score"] = [score.base_score for score in scores]

    # --------------------------------------------------------
    # 1. DATA AND FORMULA SUMMARY
    # --------------------------------------------------------
    print("\n" + "=" * 65)
    print("OACSRA BATTING FORMULA VALIDATION")
    print("=" * 65)

    print(f"Dataset: {DATA_FILE}")
    print(f"Valid innings scored: {len(df)}")
    print(f"Invalid/excluded rows: {invalid_count}")

    print("\nBenchmarks:")
    for fmt, values in BENCHMARKS.items():
        print(
            f"{fmt}: runs={values['runs']}, "
            f"strike rate={values['strike_rate']}"
        )

    print("\nBatting formula:")
    print("BP = 0.60 * runs_score + 0.40 * sr_score")

    print("\nScore range:")
    print(f"Minimum: {df['base_batting_score'].min():.2f}")
    print(f"Maximum: {df['base_batting_score'].max():.2f}")

    out_of_range = (
        (df["base_batting_score"] < 0)
        | (df["base_batting_score"] > 100)
    ).sum()

    print(f"Scores outside 0-100: {out_of_range}")

    print("\nFormat summary:")
    summary = df.groupby(format_col).agg(
        innings=("base_batting_score", "count"),
        average_batting_score=("base_batting_score", "mean"),
    )

    print(summary.round(2).to_string())

    # --------------------------------------------------------
    # 2. PLAYER VALIDATION
    # --------------------------------------------------------
    print("\n" + "=" * 65)
    print("PLAYER VALIDATION")
    print("=" * 65)

    for player_name in ["Mohammad Rizwan", "Saim Ayub"]:
        player_mask = (
            df[player_col].astype(str).str.contains(
                player_name, case=False, regex=False
            )
        )

        player_df = df[player_mask].copy()

        if player_df.empty:
            print(f"\n{player_name}: no matching records found.")
            continue

        for fmt in ["T20", "ODI"]:
            records = player_df[player_df[format_col] == fmt]

            if records.empty:
                continue

            print(f"\n{player_name} - {fmt}")
            print(f"Innings found: {len(records)}")

            display_cols = [
                player_col,
                runs_col,
                balls_col,
                "actual_strike_rate",
                "runs_score",
                "sr_score",
                "base_batting_score",
            ]

            print(
                records[display_cols]
                .round(2)
                .to_string(index=False)
            )

            print(
                f"Average batting score: "
                f"{records['base_batting_score'].mean():.2f}"
            )

    # --------------------------------------------------------
    # 3. AUTOMATED CHECKS
    # --------------------------------------------------------
    print("\n" + "=" * 65)
    print("AUTOMATED CHECKS")
    print("=" * 65)

    checks = {
        "Base batting scores are between 0 and 100":
            df["base_batting_score"].between(0, 100).all(),

        "Configured benchmarks match the agreed format values":
            BENCHMARKS == {
                "T20": {"runs": 42.0, "strike_rate": 146.51},
                "ODI": {"runs": 64.0, "strike_rate": 101.71},
            },

        "Base scores equal the weighted normalized components":
            np.allclose(
                df["base_batting_score"],
                0.60 * df["runs_score"] + 0.40 * df["sr_score"],
            ),
    }

    for description, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {description}")

    failed_checks = [
        description for description, passed in checks.items() if not passed
    ]
    print("\nValidation run complete.")
    print(
        "Note: automated checks verify implementation, "
        "not whether the formula is cricket-statistically optimal."
    )
    if failed_checks:
        raise SystemExit(
            f"{len(failed_checks)} required validation check(s) failed: "
            + "; ".join(failed_checks)
        )


if __name__ == "__main__":
    main()
