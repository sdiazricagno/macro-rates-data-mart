"""US Treasury business-day calendar used to build the daily spine.

Constant-maturity yields are published on days the Treasury market is open.
The spine is weekdays minus that close set. Equity-market holidays are not
the same set: Columbus Day and Veterans Day are closes here, and a Saturday
New Year's Day does not move the close back to Friday.

Scheduled closes:

- New Year's Day on the weekday itself, or Monday when it falls on Sunday
- Birthday of Martin Luther King, Jr. (third Monday in January) from 1986
- Washington's Birthday: February 22 through 1970, or Monday when that date
  falls on Sunday; the third Monday in February from 1971
- Lincoln's Birthday (February 12, or Monday when it falls on Sunday) through 1985
- Good Friday, except years the series still publishes a yield
- Memorial Day: May 30 through 1970, or Monday when that date falls on Sunday;
  the last Monday in May from 1971
- Juneteenth, with weekend observance, from 2022
- Independence Day and Christmas Day, with weekend observance
- Labor Day (first Monday in September)
- Columbus Day: October 12, Monday when it falls on Sunday, through 1970;
  the second Monday in October from 1971
- Election Day (first Tuesday after the first Monday in November) through 1984
- Veterans Day: the fourth Monday in October for 1971-1973; otherwise
  November 11, or Monday when it falls on Sunday
- Thanksgiving Day (fourth Thursday in November)

Early closes stay on the spine because a yield is still published. A short
list of extraordinary closes covers mourning days and weather closures where
the series has no print.
"""

from __future__ import annotations

import csv
import io
from datetime import date, timedelta

MLK_START_YEAR = 1986
JUNETEENTH_START_YEAR = 2022
MONDAY_HOLIDAY_START_YEAR = 1971
LINCOLN_END_YEAR = 1985
ELECTION_DAY_END_YEAR = 1984
VETERANS_OCTOBER_YEARS = frozenset({1971, 1972, 1973})
# Years in which the 10-year constant-maturity series still has a print.
GOOD_FRIDAY_OPEN_YEARS = frozenset({1996, 1999, 2007, 2010, 2012, 2015, 2021, 2023, 2026})
SEED_START_YEAR = 1962
SEED_END_YEAR = 2030

EXTRA_CLOSURES: tuple[tuple[date, str], ...] = (
    (date(1963, 11, 25), "National day of mourning for President Kennedy"),
    (date(1964, 2, 21), "No Treasury constant-maturity print"),
    (date(1964, 5, 29), "No Treasury constant-maturity print"),
    (date(1968, 4, 9), "National day of mourning for Martin Luther King Jr."),
    (date(1969, 3, 31), "National day of mourning for President Eisenhower"),
    (date(1969, 7, 21), "No Treasury constant-maturity print"),
    (date(1973, 12, 24), "Christmas Eve full close"),
    (date(1977, 7, 14), "New York City blackout"),
    (date(1978, 5, 30), "No Treasury constant-maturity print"),
    (date(1979, 5, 30), "No Treasury constant-maturity print"),
    (date(1985, 1, 21), "Presidential inauguration day"),
    (date(1985, 9, 27), "Hurricane Gloria"),
    (date(1994, 4, 27), "National day of mourning for President Nixon"),
    (date(2001, 9, 11), "September 11 market closure"),
    (date(2001, 9, 12), "September 11 market closure"),
    (date(2004, 6, 11), "National day of mourning for President Reagan"),
    (date(2012, 10, 30), "Hurricane Sandy"),
    (date(2018, 12, 5), "National day of mourning for President George H. W. Bush"),
)


def observed_weekday(day: date) -> date:
    """Shift a Saturday holiday to Friday and a Sunday holiday to Monday."""
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def fixed_closure(
    year: int,
    month: int,
    day: int,
    *,
    saturday: bool,
    sunday: bool,
) -> date | None:
    """Return the weekday close for a fixed-date holiday, if one is observed."""
    raw = date(year, month, day)
    if raw.weekday() < 5:
        return raw
    if raw.weekday() == 5 and saturday:
        return raw - timedelta(days=1)
    if raw.weekday() == 6 and sunday:
        return raw + timedelta(days=1)
    return None


def election_day(year: int) -> date:
    """First Tuesday after the first Monday in November."""
    day = date(year, 11, 1)
    while day.weekday() != 0:
        day += timedelta(days=1)
    return day + timedelta(days=1)


def nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """Return the nth weekday in a month. Monday is 0."""
    if n < 1:
        raise ValueError("n must be at least 1")
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """Return the last given weekday in a month. Monday is 0."""
    if month == 12:
        cursor = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        cursor = date(year, month + 1, 1) - timedelta(days=1)
    offset = (cursor.weekday() - weekday) % 7
    return cursor - timedelta(days=offset)


def easter_sunday(year: int) -> date:
    """Anonymous Gregorian computus."""
    century, year_in_century = divmod(year, 100)
    century_leap, century_remainder = divmod(century, 4)
    lunar_cycle = year % 19
    epact_century = (century + 8) // 25
    epact_correction = (century - epact_century + 1) // 3
    epact = (19 * lunar_cycle + century - century_leap - epact_correction + 15) % 30
    year_leap, year_remainder = divmod(year_in_century, 4)
    weekday_shift = (32 + 2 * century_remainder + 2 * year_leap - epact - year_remainder) % 7
    correction = (lunar_cycle + 11 * epact + 22 * weekday_shift) // 451
    month, day_index = divmod(epact + weekday_shift - 7 * correction + 114, 31)
    return date(year, month, day_index + 1)


def _add(rows: list[tuple[date, str]], day: date | None, name: str) -> None:
    if day is not None:
        rows.append((day, name))


def holidays_for_year(year: int) -> list[tuple[date, str]]:
    """Treasury full closes whose observed date falls in `year`."""
    rows: list[tuple[date, str]] = []
    _add(rows, fixed_closure(year, 1, 1, saturday=False, sunday=True), "New Year's Day")
    if year >= MLK_START_YEAR:
        rows.append(
            (
                nth_weekday_of_month(year, 1, 0, 3),
                "Birthday of Martin Luther King, Jr.",
            )
        )
    if year >= MONDAY_HOLIDAY_START_YEAR:
        rows.append((nth_weekday_of_month(year, 2, 0, 3), "Washington's Birthday"))
    else:
        _add(
            rows,
            fixed_closure(year, 2, 22, saturday=False, sunday=True),
            "Washington's Birthday",
        )
    if year <= LINCOLN_END_YEAR:
        _add(rows, fixed_closure(year, 2, 12, saturday=False, sunday=True), "Lincoln's Birthday")
    if year not in GOOD_FRIDAY_OPEN_YEARS:
        rows.append((easter_sunday(year) - timedelta(days=2), "Good Friday"))
    if year >= MONDAY_HOLIDAY_START_YEAR:
        rows.append((last_weekday_of_month(year, 5, 0), "Memorial Day"))
    else:
        _add(rows, fixed_closure(year, 5, 30, saturday=False, sunday=True), "Memorial Day")
    if year >= JUNETEENTH_START_YEAR:
        rows.append(
            (
                observed_weekday(date(year, 6, 19)),
                "Juneteenth National Independence Day",
            )
        )
    rows.append((observed_weekday(date(year, 7, 4)), "Independence Day"))
    rows.append((nth_weekday_of_month(year, 9, 0, 1), "Labor Day"))
    if year >= MONDAY_HOLIDAY_START_YEAR:
        rows.append((nth_weekday_of_month(year, 10, 0, 2), "Columbus Day"))
    else:
        _add(rows, fixed_closure(year, 10, 12, saturday=False, sunday=True), "Columbus Day")
    if year in VETERANS_OCTOBER_YEARS:
        rows.append((nth_weekday_of_month(year, 10, 0, 4), "Veterans Day"))
    else:
        _add(rows, fixed_closure(year, 11, 11, saturday=False, sunday=True), "Veterans Day")
    if year <= ELECTION_DAY_END_YEAR:
        rows.append((election_day(year), "Election Day"))
    rows.append((nth_weekday_of_month(year, 11, 3, 4), "Thanksgiving Day"))
    rows.append((observed_weekday(date(year, 12, 25)), "Christmas Day"))
    return rows


def holiday_rows(
    start_year: int = SEED_START_YEAR, end_year: int = SEED_END_YEAR
) -> list[tuple[date, str]]:
    """Scheduled closes for a closed year range, one row per date."""
    if end_year < start_year:
        raise ValueError("end_year is before start_year")
    named: dict[date, list[str]] = {}
    for year in range(start_year, end_year + 1):
        for observed_on, name in holidays_for_year(year):
            names = named.setdefault(observed_on, [])
            if name not in names:
                names.append(name)
    return [(day, "; ".join(names)) for day, names in sorted(named.items())]


def render_holiday_csv(rows: list[tuple[date, str]]) -> str:
    """Serialize holiday rows as a dbt seed."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["holiday_date", "holiday_name"])
    for day, name in rows:
        writer.writerow([day.isoformat(), name])
    return buffer.getvalue()


def render_extra_closure_csv(
    rows: tuple[tuple[date, str], ...] = EXTRA_CLOSURES,
) -> str:
    """Serialize extraordinary closures as a dbt seed."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["closure_date", "reason"])
    for day, reason in rows:
        writer.writerow([day.isoformat(), reason])
    return buffer.getvalue()
