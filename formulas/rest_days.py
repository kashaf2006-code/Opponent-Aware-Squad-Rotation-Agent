
"""Rest-day calculation for OACSRA."""

from datetime import date, datetime
from typing import Optional, Union


DateInput = Union[str, date, datetime]


def _parse_date(value: DateInput, field_name: str) -> date:
    """Convert a string or date object into a calendar date."""

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            raise ValueError(
                f"{field_name} must be a valid ISO date (YYYY-MM-DD)."
            )

    raise ValueError(
        f"{field_name} must be a date, datetime, or YYYY-MM-DD string."
    )


def calculate_rest_days(
    previous_appearance_date: Optional[DateInput],
    upcoming_match_date: DateInput,
) -> Optional[int]:
    """
    Calculate full calendar days between a player's previous appearance
    and an upcoming fixture.

    Returns:
        Number of rest days, or None if no previous appearance is recorded.

    Example:
        Previous appearance: 2026-10-10
        Upcoming match:      2026-10-14
        Rest days:           4
    """

    upcoming_date = _parse_date(
        upcoming_match_date, "upcoming_match_date"
    )

    if previous_appearance_date is None:
        return None

    previous_date = _parse_date(
        previous_appearance_date, "previous_appearance_date"
    )

    if upcoming_date < previous_date:
        raise ValueError(
            "upcoming_match_date cannot be earlier than "
            "previous_appearance_date."
        )

    return (upcoming_date - previous_date).days
