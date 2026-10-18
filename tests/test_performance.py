import csv
import math
import tempfile
import unittest
from pathlib import Path

from formulas.performance import (
    calculate_base_batting_score,
    calculate_batting_scores,
    calculate_base_bowling_score,
    calculate_bowling_scores,
    calculate_player_performance,
)


DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "limited_overs_performance.csv"
)


class BattingScoreTests(unittest.TestCase):
    def test_t20_scores_match_formula_and_benchmark(self):
        scores = calculate_batting_scores(21, 21, "T20")

        self.assertAlmostEqual(scores.actual_strike_rate, 100.0)
        self.assertAlmostEqual(scores.run_score, 50.0)
        self.assertAlmostEqual(
            scores.strike_rate_score, 100 / 146.51 * 100
        )
        self.assertAlmostEqual(
            scores.base_score,
            0.60 * 50.0 + 0.40 * (100 / 146.51 * 100),
        )
        self.assertAlmostEqual(
            calculate_base_batting_score(21, 21, "T20"),
            scores.base_score,
        )
        self.assertEqual(
            set(scores.__dataclass_fields__),
            {
                "actual_strike_rate",
                "run_score",
                "strike_rate_score",
                "base_score",
            },
        )

    def test_odi_benchmark_and_score_caps(self):
        scores = calculate_batting_scores(100, 50, "ODI")

        self.assertEqual(scores.run_score, 100.0)
        self.assertEqual(scores.strike_rate_score, 100.0)
        self.assertEqual(scores.base_score, 100.0)

    def test_odi_strike_rate_benchmark(self):
        scores = calculate_batting_scores(32, 40, "ODI")

        self.assertEqual(scores.run_score, 50.0)
        self.assertAlmostEqual(scores.actual_strike_rate, 80.0)
        self.assertAlmostEqual(
            scores.strike_rate_score, 80 / 101.71 * 100
        )

    def test_zero_runs_produce_zero_score(self):
        scores = calculate_batting_scores(0, 10, "T20")
        self.assertEqual(scores.base_score, 0.0)

    def test_invalid_inputs_raise_value_error(self):
        invalid_calls = [
            lambda: calculate_base_batting_score(1, 1, "Test"),
            lambda: calculate_batting_scores(1, 1, ""),
            lambda: calculate_batting_scores(None, 1, "T20"),
            lambda: calculate_batting_scores(1, None, "T20"),
            lambda: calculate_batting_scores(-1, 1, "T20"),
            lambda: calculate_batting_scores(1, -1, "T20"),
            lambda: calculate_batting_scores(math.nan, 1, "T20"),
            lambda: calculate_batting_scores(1, math.inf, "T20"),
            lambda: calculate_batting_scores(1, 0, "T20"),
        ]

     



    def test_real_bowler_records_produce_distinct_scores(self):
        naseem_scores = calculate_bowling_scores(3, 52, 68, "ODI")
        shaheen_scores = calculate_bowling_scores(2, 61, 62, "ODI")

        self.assertIsNotNone(naseem_scores)
        self.assertIsNotNone(shaheen_scores)
        self.assertNotEqual(
            naseem_scores.base_score, shaheen_scores.base_score
        )
        self.assertEqual(
            calculate_base_bowling_score(3, 52, 68, "ODI"),
            naseem_scores.base_score,
        )


    def test_missing_values_and_no_bowling_record_return_none(self):
        incomplete_records = [
            (None, 20, 24, "T20"),
            (1, math.nan, 24, "T20"),
            (1, 20, None, "ODI"),
            (0, 0, 0, "T20"),
        ]

        for record in incomplete_records:
            with self.subTest(record=record):
                self.assertIsNone(calculate_bowling_scores(*record))
                self.assertIsNone(calculate_base_bowling_score(*record))

    def test_invalid_inputs_raise_value_error(self):
        invalid_records = [
            (-1, 20, 24, "T20"),
            (1, -1, 24, "T20"),
            (1, 20, -1, "T20"),
            (1, 20, 24, "Test"),
            (True, 20, 24, "T20"),
            (1, math.inf, 24, "T20"),
        ]

        for record in invalid_records:
            with self.subTest(record=record):
                with self.assertRaises(ValueError):
                    calculate_bowling_scores(*record)


class DatasetPlayerPerformanceTests(unittest.TestCase):
    def test_named_players_performance_from_processed_dataset(self):
        players = ("Babar Azam", "Saim Ayub", "Haris Rauf")
        formats = ("T20", "ODI")

        results = {
            player: {
                match_format: {"batting": [], "bowling": []}
                for match_format in formats
            }
            for player in players
        }

        with DATASET_PATH.open(
            newline="", encoding="utf-8"
        ) as dataset_file:
            for row in csv.DictReader(dataset_file):
                player = row["player"]
                match_format = row["match_type"]

                if player not in results or match_format not in formats:
                    continue

                runs = float(row["runs"])
                balls_faced = float(row["balls_faced"])

                if balls_faced > 0:
                    batting = calculate_batting_scores(
                        runs, balls_faced, match_format
                    )
                    results[player][match_format]["batting"].append(
                        batting.base_score
                    )

                bowling = calculate_bowling_scores(
                    float(row["wickets"]) if row["wickets"].strip() else None,
                    (
                        float(row["runs_conceded"])
                        if row["runs_conceded"].strip()
                        else None
                    ),
                    (
                        float(row["balls_bowled"])
                        if row["balls_bowled"].strip()
                        else None
                    ),
                    match_format,
                )

                if bowling is not None:
                    results[player][match_format]["bowling"].append(
                        bowling.base_score
                    )

        expected = {
            "Babar Azam": {
                "T20": (92, 60.42024771, 0, None),
                "ODI": (61, 64.05737508, 0, None),
            },
            "Saim Ayub": {
                "T20": (58, 51.98049800, 32, 55.81016368),
                "ODI": (17, 61.10206176, 14, 52.74223818),
            },
            "Haris Rauf": {
                "T20": (27, 29.05660893, 77, 65.93229280),
                "ODI": (21, 21.87610511, 54, 74.60596536),
            },
        }

        for player, player_formats in expected.items():
            for match_format, expected_values in player_formats.items():
                batting_count, batting_avg, bowling_count, bowling_avg = (
                    expected_values
                )

                with self.subTest(player=player, match_format=match_format):
                    batting = results[player][match_format]["batting"]
                    bowling = results[player][match_format]["bowling"]

                    self.assertEqual(len(batting), batting_count)
                    self.assertAlmostEqual(
                        sum(batting) / len(batting), batting_avg, places=6
                    )
                    self.assertEqual(len(bowling), bowling_count)

                    if bowling_avg is None:
                        self.assertEqual(bowling, [])
                    else:
                        self.assertAlmostEqual(
                            sum(bowling) / len(bowling),
                            bowling_avg,
                            places=6,
                        )
