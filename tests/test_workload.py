import csv
from pathlib import Path
import tempfile
import unittest

from formulas.workload import calculate_player_workload


DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "limited_overs_performance.csv"
)
DATASET_COLUMNS = (
    "player",
    "match_id",
    "start_date",
    "match_type",
    "balls_faced",
    "balls_bowled",
)


class PlayerWorkloadTests(unittest.TestCase):
    def test_babar_azam_t20_workload_uses_real_recent_appearances(self):
        """The five newest T20 appearances produce Batter workload 78.75."""
        # Newest-first batting activity normalizes to 100, 50, 100, 100, 100.
        # Weighted batting is 87.5; bowling is 0. The Batter formula yields
        # 0.90 * 87.5 + 0.10 * 0 = 78.75.
        workload = calculate_player_workload(
            "Babar Azam", "T20", "Batter", dataset_path=DATASET_PATH
        )

        self.assertEqual(workload, 78.75)

    def test_haris_rauf_t20_workload_uses_real_recent_appearances(self):
        """The five newest T20 appearances produce Bowler workload 88.28."""
        # From the five recent rows, the weighted batting component is 13.9375
        # and bowling is 96.5416667. The Bowler formula yields 88.28125,
        # rounded by the production function to 88.28.
        workload = calculate_player_workload(
            "Haris Rauf", "T20", "Bowler", dataset_path=DATASET_PATH
        )

        self.assertEqual(workload, 88.28)

    def test_shahid_afridi_without_t20_appearances_raises_value_error(self):
        """Confirm the player is absent before checking the no-appearances error."""
        with DATASET_PATH.open(newline="", encoding="utf-8") as dataset_file:
            rows = list(csv.DictReader(dataset_file))

        shahid_t20_rows = [
            row
            for row in rows
            if row["player"].strip().casefold() == "shahid afridi"
            and row["match_type"].strip().upper() == "T20"
        ]
        self.assertEqual(shahid_t20_rows, [])

        with self.assertRaisesRegex(ValueError, "No T20 appearances found"):
            calculate_player_workload(
                "Shahid Afridi", "T20", "Batter", dataset_path=DATASET_PATH
            )

    def test_player_resting_for_all_five_appearances_has_zero_workload(self):
        """Five dated appearances with no activity have zero recency-weighted load."""
        rows = [
            {
                "player": "Resting Player",
                "match_id": 100 + day,
                "start_date": f"2025-01-{day:02d}",
                "match_type": "T20",
                "balls_faced": 0,
                "balls_bowled": 0,
            }
            for day in range(1, 6)
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            dataset_path = Path(temporary_directory) / "resting.csv"
            with dataset_path.open(
                "w", newline="", encoding="utf-8"
            ) as dataset_file:
                writer = csv.DictWriter(dataset_file, fieldnames=DATASET_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)

            workload = calculate_player_workload(
                "Resting Player",
                "T20",
                "All-rounder",
                dataset_path=dataset_path,
            )

        self.assertEqual(workload, 0.0)

    def test_player_resting_for_three_of_five_uses_recency_weights(self):
        """Two active newest appearances and three rests yield workload 45.0."""
        # Newest batting scores are 100, 50, 0, 0, 0; newest bowling scores
        # are 50, 100, 0, 0, 0. With weights .35, .25, .20, .12, .08,
        # weighted batting is 47.5 and weighted bowling is 42.5.
        # All-rounder workload is (47.5 + 42.5) / 2 = 45.0, not 47.0.
        rows = [
            {
                "player": "Partially Resting Player",
                "match_id": 205,
                "start_date": "2025-01-05",
                "match_type": "T20",
                "balls_faced": 16,
                "balls_bowled": 12,
            },
            {
                "player": "Partially Resting Player",
                "match_id": 204,
                "start_date": "2025-01-04",
                "match_type": "T20",
                "balls_faced": 8,
                "balls_bowled": 24,
            },
            *[
                {
                    "player": "Partially Resting Player",
                    "match_id": match_id,
                    "start_date": f"2025-01-{day:02d}",
                    "match_type": "T20",
                    "balls_faced": 0,
                    "balls_bowled": 0,
                }
                for match_id, day in ((203, 3), (202, 2), (201, 1))
            ],
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            dataset_path = Path(temporary_directory) / "partial_rest.csv"
            with dataset_path.open(
                "w", newline="", encoding="utf-8"
            ) as dataset_file:
                writer = csv.DictWriter(dataset_file, fieldnames=DATASET_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)

            workload = calculate_player_workload(
                "Partially Resting Player",
                "T20",
                "All-rounder",
                dataset_path=dataset_path,
            )

        self.assertEqual(workload, 45.0)


if __name__ == "__main__":
    unittest.main()
