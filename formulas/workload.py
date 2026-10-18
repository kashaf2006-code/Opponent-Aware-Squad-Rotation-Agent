
"""Role-aware workload calculation for OACSRA."""

import math
from numbers import Real
from pathlib import Path
from typing import Optional

import pandas as pd


# Project-specific workload normalization references.
ACTIVITY_REFERENCES = {
    "T20": {
        "balls_faced": 16.0,
        "balls_bowled": 24.0,
    },
    "ODI": {
        "balls_faced": 36.0,
        "balls_bowled": 53.0,
    },
}

# Weights are ordered from newest to oldest appearance.
RECENCY_WEIGHTS = (0.35, 0.25, 0.20, 0.12, 0.08)
RECENT_APPEARANCES = 5

DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "limited_overs_performance.csv"
)


def _normalize_format(match_format: str) -> str:
    """Validate and normalize the match format."""
    if not isinstance(match_format, str):
        raise ValueError("match_format must be 'T20' or 'ODI'.")

    match_format = match_format.strip().upper()

    if match_format not in ACTIVITY_REFERENCES:
        raise ValueError("match_format must be 'T20' or 'ODI'.")

    return match_format


def _normalize_role(role: str) -> str:
    """Validate and normalize the player's role."""
    if not isinstance(role, str):
        raise ValueError(
            "role must be Batter, Bowler, All-rounder, or Wicketkeeper."
        )

    normalized_role = role.strip().lower().replace("-", " ")

    aliases = {
        "batter": "batter",
        "batsman": "batter",
        "bowler": "bowler",
        "all rounder": "all-rounder",
        "allrounder": "all-rounder",
        "wicketkeeper": "wicketkeeper",
        "wicket keeper": "wicketkeeper",
        "wicketkeeper batter": "wicketkeeper",
        "wicket keeper batter": "wicketkeeper",
    }

    if normalized_role not in aliases:
        raise ValueError(
            "role must be Batter, Bowler, All-rounder, or Wicketkeeper."
        )

    return aliases[normalized_role]


def _activity_value(value: object, name: str) -> float:
    """
    Convert an activity value to a non-negative number.

    Missing values are treated as zero, assuming that they represent
    no recorded activity rather than unknown data.
    """
    if value is None or pd.isna(value):
        return 0.0

    if isinstance(value, bool):
        raise ValueError(f"{name} must be a non-negative number.")

    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a non-negative number.")

    if not math.isfinite(value) or value < 0:
        raise ValueError(
            f"{name} must be a finite, non-negative number."
        )

    return value


def calculate_appearance_workload(
    balls_faced: Optional[Real],
    balls_bowled: Optional[Real],
    match_format: str,
    role: str,
) -> float:
    """
    Calculate the role-based workload score for one appearance.

    Returns a score from 0 to 100.
    """
    match_format = _normalize_format(match_format)
    role = _normalize_role(role)

    references = ACTIVITY_REFERENCES[match_format]

    batting_activity = _activity_value(
        balls_faced, "balls_faced"
    )
    bowling_activity = _activity_value(
        balls_bowled, "balls_bowled"
    )

    batting_score = min(
        batting_activity / references["balls_faced"], 1.0
    ) * 100

    bowling_score = min(
        bowling_activity / references["balls_bowled"], 1.0
    ) * 100

    if role in ("batter", "wicketkeeper"):
        workload = 0.90 * batting_score + 0.10 * bowling_score
    elif role == "bowler":
        workload = 0.10 * batting_score + 0.90 * bowling_score
    else:
        workload = 0.50 * batting_score + 0.50 * bowling_score

    return round(workload, 2)


def calculate_player_workload(
    player_name: str,
    match_format: str,
    role: str,
    dataset_path: Optional[str | Path] = None,
) -> float:
    """
    Calculate recency-weighted workload from up to five recent appearances.

    Batting and bowling activity are weighted separately across appearances.
    The resulting components are then combined according to the player's role.
    """
    if not isinstance(player_name, str) or not player_name.strip():
        raise ValueError("player_name must not be empty.")

    match_format = _normalize_format(match_format)
    role = _normalize_role(role)

    path = Path(dataset_path) if dataset_path else DATASET_PATH

    if not path.exists():
        raise FileNotFoundError(
            f"Workload dataset not found: {path}"
        )

    data = pd.read_csv(path)

    required_columns = {
        "player",
        "match_id",
        "start_date",
        "match_type",
        "balls_faced",
        "balls_bowled",
    }

    missing_columns = required_columns - set(data.columns)

    if missing_columns:
        raise ValueError(
            f"Dataset is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    # Find this player's appearances in the requested format.
    matches = data[
        data["player"].astype(str).str.strip().str.casefold()
        == player_name.strip().casefold()
    ].copy()

    matches = matches[
        matches["match_type"].astype(str).str.strip().str.upper()
        == match_format
    ].copy()

    if matches.empty:
        raise ValueError(
            f"No {match_format} appearances found for {player_name!r}."
        )

    # Sort appearances newest first.
    matches["start_date"] = pd.to_datetime(
        matches["start_date"], errors="coerce"
    )

    matches = matches.dropna(subset=["start_date"])

    matches = matches.sort_values(
        ["start_date", "match_id"],
        ascending=[False, False],
        kind="stable",
    ).head(RECENT_APPEARANCES)

    if matches.empty:
        raise ValueError(
            f"No dated {match_format} appearances found for "
            f"{player_name!r}."
        )

    batting_total = 0.0
    bowling_total = 0.0
    total_weight = 0.0

    references = ACTIVITY_REFERENCES[match_format]

    # Normalize each appearance's activity and apply its recency weight.
    for index, (_, row) in enumerate(matches.iterrows()):
        balls_faced = _activity_value(
            row["balls_faced"], "balls_faced"
        )
        balls_bowled = _activity_value(
            row["balls_bowled"], "balls_bowled"
        )

        batting_score = min(
            balls_faced / references["balls_faced"], 1.0
        ) * 100

        bowling_score = min(
            balls_bowled / references["balls_bowled"], 1.0
        ) * 100

        weight = RECENCY_WEIGHTS[index]

        batting_total += weight * batting_score
        bowling_total += weight * bowling_score
        total_weight += weight

    # Renormalize weights if fewer than five appearances are available.
    batting_total /= total_weight
    bowling_total /= total_weight

    # Combine the weighted components according to the player's role.
    if role in ("batter", "wicketkeeper"):
        workload = 0.90 * batting_total + 0.10 * bowling_total
    elif role == "bowler":
        workload = 0.10 * batting_total + 0.90 * bowling_total
    else:
        workload = 0.50 * batting_total + 0.50 * bowling_total

    return round(workload, 2)
