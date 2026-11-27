from datetime import date
from pathlib import Path

from macro_rates.charts import (
    contiguous_spans,
    save_coverage_chart,
    save_spread_chart,
    save_stress_chart,
    save_yield_curve,
)


def test_contiguous_spans_merge_true_runs() -> None:
    dates = [date(2024, 1, d) for d in range(1, 6)]
    flags = [False, True, True, None, True]
    assert contiguous_spans(dates, flags) == [
        (date(2024, 1, 2), date(2024, 1, 3)),
        (date(2024, 1, 5), date(2024, 1, 5)),
    ]


def test_charts_write_pngs(tmp_path: Path) -> None:
    dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]
    save_yield_curve(
        tmp_path / "yield_curve.png",
        dates,
        {"10-year": [4.0, None, 4.2], "2-year": [4.5, 4.4, 4.1]},
        snapshot_date="2026-11-27",
    )
    save_spread_chart(
        tmp_path / "spreads_inversions.png",
        dates,
        [-0.5, -0.1, 0.1],
        [0.2, -0.2, -0.3],
        [(date(2024, 1, 2), date(2024, 1, 3))],
        [(date(2024, 1, 3), date(2024, 1, 4))],
        snapshot_date="2026-11-27",
    )
    save_stress_chart(
        tmp_path / "stress_regime.png",
        dates,
        [-0.2, 0.4, 0.1],
        [False, True, False],
        snapshot_date="2026-11-27",
    )
    save_coverage_chart(
        tmp_path / "test_coverage.png",
        {"not null": {"pass": 4}, "z-score": {"pass": 1, "warn": 2}},
        snapshot_date="2026-11-27",
    )
    for name in (
        "yield_curve.png",
        "spreads_inversions.png",
        "stress_regime.png",
        "test_coverage.png",
    ):
        payload = (tmp_path / name).read_bytes()
        assert payload.startswith(b"\x89PNG")
