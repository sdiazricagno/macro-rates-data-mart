import json
from datetime import date
from pathlib import Path

from macro_rates.catalog import get_series
from macro_rates.fred import Observation, parse_fred_csv
from macro_rates.snapshot import (
    series_manifest_entry,
    stitch_observations,
    write_observation_csv,
    year_windows,
)


def test_year_windows_cover_the_span_without_overlap() -> None:
    windows = year_windows(date(2020, 6, 1), date(2022, 2, 1), years=2)
    assert windows == [
        (date(2020, 6, 1), date(2021, 12, 31)),
        (date(2022, 1, 1), date(2022, 2, 1)),
    ]
    flat = [day for start, end in windows for day in (start, end)]
    assert flat[0] == date(2020, 6, 1)
    assert flat[-1] == date(2022, 2, 1)


def test_stitch_observations_sorts_and_rejects_conflicts() -> None:
    first = [Observation(date(2024, 1, 3), "2"), Observation(date(2024, 1, 2), "1")]
    second = [Observation(date(2024, 1, 2), "1"), Observation(date(2024, 1, 4), None)]
    stitched = stitch_observations([first, second])
    assert [row.observation_date for row in stitched] == [
        date(2024, 1, 2),
        date(2024, 1, 3),
        date(2024, 1, 4),
    ]


def test_observation_csv_round_trip(tmp_path: Path) -> None:
    rows = [Observation(date(2024, 1, 2), "4.10"), Observation(date(2024, 1, 3), None)]
    path = tmp_path / "dgs10.csv"
    write_observation_csv(path, rows)
    parsed = parse_fred_csv(path.read_text(encoding="utf-8"), "DGS10")
    assert parsed == rows


def test_manifest_entry_counts() -> None:
    spec = get_series("DGS10")
    rows = [Observation(date(2024, 1, 2), "4.10"), Observation(date(2024, 1, 3), None)]
    entry = series_manifest_entry(
        spec, rows, "https://example.test", ["https://example.test"], "abc"
    )
    assert entry["row_count"] == 2
    assert entry["null_count"] == 1
    assert entry["non_null_count"] == 1
    assert entry["min_observation_date"] == "2024-01-02"
    assert entry["max_observation_date"] == "2024-01-03"


def test_committed_snapshot_matches_its_manifest() -> None:
    root = Path(__file__).resolve().parents[1]
    snapshots = sorted((root / "data" / "raw").glob("*/manifest.json"))
    assert len(snapshots) == 1
    manifest_path = snapshots[0]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_path.parent.name == manifest["snapshot_date"]
    assert manifest["endpoint"] == "https://fred.stlouisfed.org/graph/fredgraph.csv"
    assert manifest["retrieved_at"].endswith("Z")
    series = manifest["series"]
    assert [row["series_id"] for row in series] == [
        "DGS3MO",
        "DGS2",
        "DGS5",
        "DGS10",
        "DGS30",
        "DFF",
        "CPIAUCSL",
        "UNRATE",
        "NFCI",
    ]
    for entry in series:
        csv_path = manifest_path.parent / entry["file_name"]
        text = csv_path.read_text(encoding="utf-8")
        parsed = parse_fred_csv(text, entry["series_id"])
        assert len(parsed) == entry["row_count"]
        assert sum(1 for row in parsed if row.value is None) == entry["null_count"]
        assert (
            min(row.observation_date for row in parsed).isoformat() == entry["min_observation_date"]
        )
        assert (
            max(row.observation_date for row in parsed).isoformat() == entry["max_observation_date"]
        )
        assert entry["source_url"] == (
            f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={entry['series_id']}"
        )
        digest = __import__("hashlib").sha256(csv_path.read_bytes()).hexdigest()
        assert digest == entry["sha256"]
