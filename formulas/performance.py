
"""Player performance scoring for OACSRA."""

from dataclasses import dataclass
import math
from numbers import Real
from pathlib import Path
from typing import Optional

import pandas as pd


# Format-specific batting benchmarks.
BENCHMARKS = {
    "T20": {"runs": 42.0, "strike_rate": 146.51},
    "ODI": {"runs": 64.0, "strike_rate": 101.71},
}

RUNS_WEIGHT = 0.60
STRIKE_RATE_WEIGHT = 0.40

# Format-specific bowling benchmarks.
BOWLING_BENCHMARKS = {
    "T20": {"wickets": 2.0, "economy_rate": 5.75},
    "ODI": {"wickets": 2.0, "economy_rate": 4.55},
}

BOWLING_WICKETS_WEIGHT = 0.60
BOWLING_ECONOMY_WEIGHT = 0.40

# Newest appearance first.
RECENCY_WEIGHTS = (0.35, 0.25, 0.20, 0.12, 0.08)
RECENT_APPEARANCES = 5

DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "limited_overs_performance.csv"
)


@dataclass(frozen=True)
class BattingScores:
    actual_strike_rate: float
    run_score: float
    strike_rate_score: float
    base_score: float


@dataclass(frozen=True)
class BowlingScores:
    actual_economy_rate: float
    wicket_score: float
    economy_score: float
    base_score: float


def _non_negative_finite(value: Real, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite, non-negative number.")

    value = float(value)

    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite, non-negative number.")

    return value


def _normalize_format(match_format: str) -> str:
    if not isinstance(match_format, str):
        raise ValueError("match_format must be 'T20' or 'ODI'.")

    normalized = match_format.strip().upper()

    if normalized not in BENCHMARKS:
        raise ValueError("match_format must be 'T20' or 'ODI'.")

    return normalized


def _is_missing(value: object) -> bool:
    if value is None:
        return True

    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _calculate_batting_components(
    runs: Real,
    balls_faced: Real,
    match_format: str,
) -> tuple[float, float, float, float]:
    runs = _non_negative_finite(runs, "runs")
    balls = _non_negative_finite(balls_faced, "balls_faced")

    if balls == 0:
        raise ValueError("balls_faced must be greater than zero.")

    benchmarks = BENCHMARKS[_normalize_format(match_format)]

    run_score = min(runs / benchmarks["runs"], 1.0) * 100
    actual_strike_rate = runs / balls * 100
    strike_rate_score = min(
        actual_strike_rate / benchmarks["strike_rate"], 1.0
    ) * 100

    base_score = (
        RUNS_WEIGHT * run_score
        + STRIKE_RATE_WEIGHT * strike_rate_score
    )

    return actual_strike_rate, run_score, strike_rate_score, base_score


def calculate_base_batting_score(
    runs: Real,
    balls_faced: Real,
    match_format: str,
) -> float:
    """Return the 0-100 batting score for one appearance."""
    return _calculate_batting_components(
        runs, balls_faced, match_format
    )[3]


def calculate_batting_scores(
    runs: Real,
    balls_faced: Real,
    match_format: str,
) -> BattingScores:
    """Return batting components and the score for one appearance."""
    actual_sr, run_score, sr_score, base_score = (
        _calculate_batting_components(runs, balls_faced, match_format)
    )

    return BattingScores(
        actual_strike_rate=actual_sr,
        run_score=run_score,
        strike_rate_score=sr_score,
        base_score=base_score,
    )


def calculate_bowling_scores(
    wickets: Optional[Real],
    runs_conceded: Optional[Real],
    balls_bowled: Optional[Real],
    match_format: str,
) -> Optional[BowlingScores]:
    """Return one appearance's bowling score, or None without a valid record."""
    if any(
        _is_missing(value)
        for value in (wickets, runs_conceded, balls_bowled)
    ):
        return None

    wickets = _non_negative_finite(wickets, "wickets")
    runs_conceded = _non_negative_finite(
        runs_conceded, "runs_conceded"
    )
    balls = _non_negative_finite(balls_bowled, "balls_bowled")

    if balls == 0:
        return None

    benchmarks = BOWLING_BENCHMARKS[_normalize_format(match_format)]

    economy = runs_conceded * 6 / balls
    wicket_score = min(
        wickets / benchmarks["wickets"], 1.0
    ) * 100

    economy_score = (
        min(benchmarks["economy_rate"] / economy, 1.0) * 100
        if economy > 0
        else 100.0
    )

    base_score = (
        BOWLING_WICKETS_WEIGHT * wicket_score
        + BOWLING_ECONOMY_WEIGHT * economy_score
    )

    return BowlingScores(
        actual_economy_rate=economy,
        wicket_score=wicket_score,
        economy_score=economy_score,
        base_score=base_score,
    )


def calculate_base_bowling_score(
    wickets: Optional[Real],
    runs_conceded: Optional[Real],
    balls_bowled: Optional[Real],
    match_format: str,
) -> Optional[float]:
    """Return one appearance's bowling score, or None without a valid record."""
    scores = calculate_bowling_scores(
        wickets, runs_conceded, balls_bowled, match_format
    )
    return None if scores is None else scores.base_score


def _row_score(row: pd.Series, match_format: str, role: str) -> Optional[float]:
    """Calculate the selected role's score for one appearance."""
    batting_score = None
    bowling_score = None

    runs = row["runs"]
    balls_faced = row["balls_faced"]

    if not _is_missing(runs) and not _is_missing(balls_faced):
        if float(balls_faced) > 0:
            batting_score = calculate_base_batting_score(
                runs, balls_faced, match_format
            )

    bowling = calculate_bowling_scores(
        row["wickets"],
        row["runs_conceded"],
        row["balls_bowled"],
        match_format,
    )

    if bowling is not None:
        bowling_score = bowling.base_score

    if role in ("batter", "wicketkeeper"):
        return batting_score

    if role == "bowler":
        return bowling_score

    # All-rounders use both components when available.
    available_scores = [
        score
        for score in (batting_score, bowling_score)
        if score is not None
    ]

    if not available_scores:
        return None

    return sum(available_scores) / len(available_scores)


def calculate_player_performance(
    player_name: str,
    match_format: str,
    role: str,
    dataset_path: Optional[str | Path] = None,
) -> float:
    """
    Return one 0-100 player performance score from the latest five appearances.

    Recency weights are renormalized when selected appearances have no
    valid score for the requested role.
    """
    if not isinstance(player_name, str) or not player_name.strip():
        raise ValueError("player_name must not be empty.")

    match_format = _normalize_format(match_format)

    if not isinstance(role, str):
        raise ValueError("role must be Batter, Bowler, All-rounder, or Wicketkeeper.")

    role = role.strip().lower().replace("-", " ")

    role_aliases = {
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

    if role not in role_aliases:
        raise ValueError(
            "role must be Batter, Bowler, All-rounder, or Wicketkeeper."
        )

    role = role_aliases[role]

    path = Path(dataset_path) if dataset_path else DATASET_PATH

    if not path.exists():
        raise FileNotFoundError(f"Performance dataset not found: {path}")

    data = pd.read_csv(path)

    required_columns = {
        "start_date", "match_type", "player", "runs", "balls_faced",
        "wickets", "runs_conceded", "balls_bowled",
    }

    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        raise ValueError(
            f"Dataset is missing required columns: {sorted(missing_columns)}"
        )

    player_matches = data[
        data["player"].astype(str).str.strip().str.casefold()
        == player_name.strip().casefold()
    ].copy()

    player_matches = player_matches[
        player_matches["match_type"].astype(str).str.strip().str.upper()
        == match_format
    ].copy()

    if player_matches.empty:
        raise ValueError(
            f"No {match_format} appearances found for {player_name!r}."
        )

    player_matches["start_date"] = pd.to_datetime(
        player_matches["start_date"], errors="coerce"
    )
    player_matches = player_matches.dropna(subset=["start_date"])

    # One row represents a player's appearance in a match.
    player_matches = player_matches.sort_values(
        ["start_date", "match_id"],
        ascending=[False, False],
        kind="stable",
    ).head(RECENT_APPEARANCES)

    if player_matches.empty:
        raise ValueError(
            f"No dated {match_format} appearances found for {player_name!r}."
        )

    weighted_scores = []
    total_weight = 0.0

    for index, (_, row) in enumerate(player_matches.iterrows()):
        try:
            performance = _row_score(row, match_format, role)
        except (TypeError, ValueError, OverflowError):
            performance = None

        if performance is None or not math.isfinite(performance):
            continue

        weight = RECENCY_WEIGHTS[index]
        weighted_scores.append(performance * weight)
        total_weight += weight

    if total_weight == 0:
        raise ValueError(
            f"No valid {role} performance scores in the last "
            f"{RECENT_APPEARANCES} {match_format} appearances for {player_name!r}."
        )

    performance = sum(weighted_scores) / total_weight
    return round(performance, 2)
