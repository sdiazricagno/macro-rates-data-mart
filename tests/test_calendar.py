from datetime import date
from pathlib import Path

from macro_rates.calendar import (
    EXTRA_CLOSURES,
    SEED_END_YEAR,
    SEED_START_YEAR,
    easter_sunday,
    holiday_rows,
    holidays_for_year,
    observed_weekday,
    render_extra_closure_csv,
    render_holiday_csv,
)


def test_easter_and_good_friday_known_dates() -> None:
    assert easter_sunday(2024) == date(2024, 3, 31)
    assert easter_sunday(2026) == date(2026, 4, 5)
    assert dict(holidays_for_year(2024))[date(2024, 3, 29)] == "Good Friday"
    assert date(2026, 4, 3) not in dict(holidays_for_year(2026))


def test_observed_weekday_shifts_weekends() -> None:
    assert observed_weekday(date(2022, 1, 1)) == date(2021, 12, 31)
    assert observed_weekday(date(2023, 1, 1)) == date(2023, 1, 2)
    assert observed_weekday(date(2024, 1, 1)) == date(2024, 1, 1)


def test_scheduled_closes_are_weekdays_and_include_thanksgiving() -> None:
    rows = holiday_rows()
    assert rows
    assert all(day.weekday() < 5 for day, _name in rows)
    names_2026 = dict(holidays_for_year(2026))
    assert names_2026[date(2026, 11, 26)] == "Thanksgiving Day"
    assert date(2026, 1, 19) in names_2026
    assert "Juneteenth" in names_2026[date(2026, 6, 19)]


def test_saturday_new_year_does_not_close_friday() -> None:
    names = dict(holiday_rows(2021, 2023))
    assert date(2021, 12, 31) not in names
    assert names[date(2023, 1, 2)] == "New Year's Day"


def test_committed_seeds_match_the_calendar_rules() -> None:
    root = Path(__file__).resolve().parents[1]
    holiday_seed = (root / "seeds" / "us_market_holidays.csv").read_text(encoding="utf-8")
    closure_seed = (root / "seeds" / "us_market_extra_closures.csv").read_text(encoding="utf-8")
    assert holiday_seed == render_holiday_csv(holiday_rows(SEED_START_YEAR, SEED_END_YEAR))
    assert closure_seed == render_extra_closure_csv(EXTRA_CLOSURES)
    assert all(day.weekday() < 5 for day, _reason in EXTRA_CLOSURES)
