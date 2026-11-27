"""Export mart tables and write the charts under docs/."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import duckdb

from macro_rates.charts import (
    save_coverage_chart,
    save_spread_chart,
    save_stress_chart,
    save_yield_curve,
)
from macro_rates.coverage import load_run_results, summarize_run_results
from macro_rates.highlights import build_highlights, write_highlights

MARTS = (
    "fct_yield_curve_daily",
    "fct_curve_spreads",
    "dim_inversion_episodes",
    "fct_real_rates",
    "fct_stress_regime",
)


def _rows(connection: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    cursor = connection.execute(sql)
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _as_date(value: object) -> date:
    if isinstance(value, date):
        return value
    raise TypeError(f"expected a date, got {type(value).__name__}")


def export_marts(connection: duckdb.DuckDBPyConnection, export_dir: Path) -> None:
    """Write one CSV per mart, ordered by its natural key."""
    export_dir.mkdir(parents=True, exist_ok=True)
    order_by = {
        "dim_inversion_episodes": "spread_code, start_date",
    }
    for name in MARTS:
        destination = (export_dir / f"{name}.csv").as_posix()
        sort_keys = order_by.get(name, "curve_date")
        connection.execute(
            f"copy (select * from marts.{name} order by {sort_keys}) "
            f"to '{destination}' (header true, delim ',')"
        )


def render_charts(
    connection: duckdb.DuckDBPyConnection,
    docs_dir: Path,
    *,
    snapshot_date: str,
    category_counts: dict[str, dict[str, int]],
) -> None:
    """Render the four committed charts."""
    curve_rows = _rows(
        connection,
        """
        select curve_date, yield_3m, yield_2y, yield_5y, yield_10y, yield_30y
        from marts.fct_yield_curve_daily
        order by curve_date
        """,
    )
    dates = [_as_date(row["curve_date"]) for row in curve_rows]
    save_yield_curve(
        docs_dir / "yield_curve.png",
        dates,
        {
            "3-month": [row["yield_3m"] for row in curve_rows],
            "2-year": [row["yield_2y"] for row in curve_rows],
            "5-year": [row["yield_5y"] for row in curve_rows],
            "10-year": [row["yield_10y"] for row in curve_rows],
            "30-year": [row["yield_30y"] for row in curve_rows],
        },
        snapshot_date=snapshot_date,
    )
    spread_rows = _rows(
        connection,
        """
        select curve_date, spread_2s10s, spread_3m10y
        from marts.fct_curve_spreads
        order by curve_date
        """,
    )
    spread_dates = [_as_date(row["curve_date"]) for row in spread_rows]
    episodes = _rows(
        connection,
        """
        select spread_code, start_date, end_date
        from marts.dim_inversion_episodes
        order by spread_code, start_date
        """,
    )
    save_spread_chart(
        docs_dir / "spreads_inversions.png",
        spread_dates,
        [row["spread_2s10s"] for row in spread_rows],
        [row["spread_3m10y"] for row in spread_rows],
        [
            (_as_date(row["start_date"]), _as_date(row["end_date"]))
            for row in episodes
            if row["spread_code"] == "2s10s"
        ],
        [
            (_as_date(row["start_date"]), _as_date(row["end_date"]))
            for row in episodes
            if row["spread_code"] == "3m10y"
        ],
        snapshot_date=snapshot_date,
    )
    stress_rows = _rows(
        connection,
        """
        select curve_date, nfci, stress_regime
        from marts.fct_stress_regime
        order by curve_date
        """,
    )
    save_stress_chart(
        docs_dir / "stress_regime.png",
        [_as_date(row["curve_date"]) for row in stress_rows],
        [row["nfci"] for row in stress_rows],
        [row["stress_regime"] for row in stress_rows],
        snapshot_date=snapshot_date,
    )
    save_coverage_chart(
        docs_dir / "test_coverage.png",
        category_counts,
        snapshot_date=snapshot_date,
    )


def export_docs(
    database: Path,
    docs_dir: Path,
    export_dir: Path,
    run_results: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    """Export marts, charts, and highlights from a built warehouse."""
    if not database.exists():
        raise FileNotFoundError(
            f"warehouse not found at {database}. Run `dbt build --profiles-dir .` first."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    outcomes = summarize_run_results(load_run_results(run_results))
    connection = duckdb.connect(str(database), read_only=True)
    try:
        export_marts(connection, export_dir)
        highlights = build_highlights(
            connection,
            snapshot_date=str(manifest["snapshot_date"]),
            retrieved_at=str(manifest["retrieved_at"]),
            outcomes=outcomes,
        )
        category_counts = highlights["dbt_tests"]["by_category"]
        render_charts(
            connection,
            docs_dir,
            snapshot_date=str(manifest["snapshot_date"]),
            category_counts=category_counts,
        )
    finally:
        connection.close()
    write_highlights(docs_dir / "highlights.json", highlights)
    return highlights


def main(argv: list[str] | None = None) -> None:
    """CLI used after dbt build."""
    parser = argparse.ArgumentParser(description="Export marts and render docs charts.")
    parser.add_argument("--database", type=Path, default=Path("data/macro_rates.duckdb"))
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"))
    parser.add_argument("--export-dir", type=Path, default=Path("data/exports"))
    parser.add_argument("--run-results", type=Path, default=Path("target/run_results.json"))
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--snapshot-date", default="2026-11-27")
    args = parser.parse_args(argv)
    manifest = args.manifest or Path("data/raw") / args.snapshot_date / "manifest.json"
    export_docs(args.database, args.docs_dir, args.export_dir, args.run_results, manifest)


if __name__ == "__main__":
    main()
