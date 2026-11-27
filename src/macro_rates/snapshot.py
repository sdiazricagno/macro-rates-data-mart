"""Write a dated FRED snapshot and a manifest the mart can rebuild from."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from macro_rates.catalog import SERIES, SeriesSpec
from macro_rates.fred import (
    FRED_GRAPH_ENDPOINT,
    Observation,
    fetch_with_retries,
    parse_fred_csv,
    series_url,
    urlopen_text,
)

Getter = Callable[[str], str]


def year_windows(start: date, end: date, years: int) -> list[tuple[date, date]]:
    """Split an inclusive date span into non-overlapping windows of `years`."""
    if years < 1:
        raise ValueError("years must be at least 1")
    if end < start:
        raise ValueError("end is before start")
    windows: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        window_end = min(date(cursor.year + years - 1, 12, 31), end)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return windows


def stitch_observations(chunks: list[list[Observation]]) -> list[Observation]:
    """Merge windowed downloads. Conflicting values for one date are an error."""
    by_date: dict[date, Observation] = {}
    for chunk in chunks:
        for row in chunk:
            existing = by_date.get(row.observation_date)
            if existing is not None and existing.value != row.value:
                raise ValueError(
                    "conflicting values for "
                    f"{row.observation_date.isoformat()}: {existing.value} and {row.value}"
                )
            by_date[row.observation_date] = row
    return [by_date[day] for day in sorted(by_date)]


def write_observation_csv(path: Path, rows: list[Observation]) -> None:
    """Write the normalized snapshot CSV. Blank value means a missing print."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["observation_date", "value"])
        for row in rows:
            writer.writerow(
                [row.observation_date.isoformat(), "" if row.value is None else row.value]
            )


def file_sha256(path: Path) -> str:
    """Hex digest of a snapshot file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def series_manifest_entry(
    spec: SeriesSpec,
    rows: list[Observation],
    source_url: str,
    request_urls: list[str],
    sha256: str,
) -> dict[str, object]:
    """Manifest fields for one series."""
    if not rows:
        raise ValueError(f"{spec.series_id}: no observations")
    dates = [row.observation_date for row in rows]
    null_count = sum(1 for row in rows if row.value is None)
    return {
        "series_id": spec.series_id,
        "title": spec.title,
        "file_name": spec.filename,
        "source_url": source_url,
        "request_urls": request_urls,
        "frequency": spec.frequency,
        "unit": spec.unit,
        "seasonal_adjustment": spec.seasonal_adjustment,
        "row_count": len(rows),
        "null_count": null_count,
        "non_null_count": len(rows) - null_count,
        "min_observation_date": min(dates).isoformat(),
        "max_observation_date": max(dates).isoformat(),
        "sha256": sha256,
    }


def download_series(
    spec: SeriesSpec,
    end: date,
    getter: Getter,
    window_years: int,
    attempts: int = 4,
    base_delay_seconds: float = 1.0,
) -> tuple[list[Observation], list[str]]:
    """Download one series in year windows and stitch the observations."""
    if end < spec.history_start:
        raise ValueError(f"{spec.series_id}: end date is before history start")
    windows = year_windows(spec.history_start, end, window_years)
    request_urls = [series_url(spec.series_id, start, stop) for start, stop in windows]
    chunks: list[list[Observation]] = []
    for url in request_urls:
        text = fetch_with_retries(
            url,
            getter,
            attempts=attempts,
            base_delay_seconds=base_delay_seconds,
        )
        chunks.append(parse_fred_csv(text, spec.series_id))
    return stitch_observations(chunks), request_urls


def build_snapshot(
    output_dir: Path,
    snapshot_date: date,
    end: date,
    getter: Getter,
    window_years: int = 5,
    retrieved_at: datetime | None = None,
) -> dict[str, object]:
    """Download every catalog series and write the snapshot directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, object]] = []
    for spec in SERIES:
        rows, request_urls = download_series(spec, end, getter, window_years)
        csv_path = output_dir / spec.filename
        write_observation_csv(csv_path, rows)
        entries.append(
            series_manifest_entry(
                spec,
                rows,
                series_url(spec.series_id),
                request_urls,
                file_sha256(csv_path),
            )
        )
        print(
            f"{spec.series_id}: {len(rows)} rows "
            f"({entries[-1]['min_observation_date']} to {entries[-1]['max_observation_date']})"
        )
    stamp = retrieved_at or datetime.now(UTC).replace(microsecond=0)
    manifest: dict[str, object] = {
        "snapshot_date": snapshot_date.isoformat(),
        "retrieved_at": stamp.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endpoint": FRED_GRAPH_ENDPOINT,
        "series": entries,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main(argv: list[str] | None = None) -> None:
    """CLI: download a dated snapshot under data/raw."""
    parser = argparse.ArgumentParser(description="Download a public FRED snapshot.")
    parser.add_argument("--snapshot-date", type=_parse_date, default=None)
    parser.add_argument("--end-date", type=_parse_date, default=None)
    parser.add_argument("--output-root", type=Path, default=Path("data/raw"))
    parser.add_argument("--window-years", type=int, default=5)
    args = parser.parse_args(argv)
    snapshot_date = args.snapshot_date or date.today()
    end = args.end_date or snapshot_date
    output_dir = args.output_root / snapshot_date.isoformat()

    def getter(url: str) -> str:
        text = urlopen_text(url, timeout=90.0)
        time.sleep(0.25)
        return text

    build_snapshot(
        output_dir=output_dir,
        snapshot_date=snapshot_date,
        end=end,
        getter=getter,
        window_years=args.window_years,
    )


if __name__ == "__main__":
    main()
