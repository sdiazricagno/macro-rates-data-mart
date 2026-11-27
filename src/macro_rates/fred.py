"""Download and parse the public FRED fredgraph CSV endpoint."""

from __future__ import annotations

import csv
import io
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode

FRED_GRAPH_ENDPOINT = "https://fred.stlouisfed.org/graph/fredgraph.csv"
USER_AGENT = (
    "macro-rates-data-mart/1.0 "
    "(public-data snapshot; +https://github.com/sdiazricagno/macro-rates-data-mart)"
)
SERIES_ID_RE = re.compile(r"^[A-Z0-9]+$")
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
MISSING_TOKENS = {"", "."}

Getter = Callable[[str], str]


class TransientFetchError(Exception):
    """A retryable failure while calling FRED."""


@dataclass(frozen=True)
class Observation:
    """One FRED observation. `value` keeps the original numeric token."""

    observation_date: date
    value: str | None


def series_url(series_id: str, start: date | None = None, end: date | None = None) -> str:
    """Build a fredgraph CSV URL. No API key is used."""
    token = series_id.strip().upper()
    if SERIES_ID_RE.fullmatch(token) is None:
        raise ValueError(f"invalid FRED series id: {series_id}")
    query: dict[str, str] = {"id": token}
    if start is not None:
        query["cosd"] = start.isoformat()
    if end is not None:
        query["coed"] = end.isoformat()
    return f"{FRED_GRAPH_ENDPOINT}?{urlencode(query)}"


def parse_fred_csv(text: str, series_id: str) -> list[Observation]:
    """Parse a fredgraph CSV body into observations.

    The public file uses `observation_date` and the series id as columns.
    Missing prints are `.` or blank. The numeric token is preserved.
    """
    stripped = text.lstrip("\ufeff").strip()
    if not stripped:
        raise ValueError(f"{series_id}: empty FRED response")
    rows = list(csv.reader(io.StringIO(stripped)))
    if len(rows) < 1:
        raise ValueError(f"{series_id}: empty FRED response")
    header = [cell.strip() for cell in rows[0]]
    if len(header) < 2:
        raise ValueError(f"{series_id}: unexpected header {header}")

    observations: list[Observation] = []
    for cells in rows[1:]:
        if not cells or all(not cell.strip() for cell in cells):
            continue
        if len(cells) < 2:
            raise ValueError(f"{series_id}: short row {cells}")
        raw_date = cells[0].strip()
        raw_value = cells[1].strip()
        try:
            observed_on = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise ValueError(f"{series_id}: bad date {raw_date}") from exc
        if raw_value in MISSING_TOKENS:
            value = None
        elif NUMBER_RE.fullmatch(raw_value):
            value = raw_value
        else:
            raise ValueError(f"{series_id}: bad value {raw_value}")
        observations.append(Observation(observed_on, value))
    return observations


def urlopen_text(url: str, timeout: float = 60.0) -> str:
    """GET a URL and return the decoded body."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/csv,text/plain,*/*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code in {429, 500, 502, 503, 504}:
            raise TransientFetchError(f"HTTP {exc.code} for {url}") from exc
        raise
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        raise TransientFetchError(str(exc)) from exc
    return payload.decode("utf-8-sig")


def fetch_with_retries(
    url: str,
    getter: Getter,
    attempts: int = 4,
    base_delay_seconds: float = 1.0,
) -> str:
    """Call `getter` until it returns text or the attempt budget is spent."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return getter(url)
        except TransientFetchError as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            time.sleep(base_delay_seconds * (2**attempt))
    raise RuntimeError(f"failed to fetch {url}") from last_error
