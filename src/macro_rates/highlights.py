"""Numbers taken from the built marts for the docs summary."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from macro_rates.coverage import TestOutcome, counts_by_category, status_totals

JsonObject = dict[str, Any]


def _ready(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, float):
        return round(value, 4)
    return value


def _row(connection: duckdb.DuckDBPyConnection, sql: str) -> JsonObject:
    cursor = connection.execute(sql)
    columns = [item[0] for item in cursor.description]
    fetched = cursor.fetchone()
    if fetched is None:
        raise ValueError("query returned no row")
    return {column: _ready(value) for column, value in zip(columns, fetched, strict=True)}


def _rows(connection: duckdb.DuckDBPyConnection, sql: str) -> list[JsonObject]:
    cursor = connection.execute(sql)
    columns = [item[0] for item in cursor.description]
    return [
        {column: _ready(value) for column, value in zip(columns, row, strict=True)}
        for row in cursor.fetchall()
    ]


def build_highlights(
    connection: duckdb.DuckDBPyConnection,
    *,
    snapshot_date: str,
    retrieved_at: str,
    outcomes: list[TestOutcome],
) -> JsonObject:
    """Assemble the published summary from mart queries."""
    panel = _row(
        connection,
        """
        select
            min(curve_date) as panel_start,
            max(curve_date) as panel_end,
            count(*) as business_days
        from marts.fct_yield_curve_daily
        """,
    )
    latest = _row(
        connection,
        """
        with latest as (
            select max(curve_date) as curve_date
            from marts.fct_yield_curve_daily
            where yield_10y is not null
        )
        select
            y.curve_date,
            y.yield_3m,
            y.yield_2y,
            y.yield_5y,
            y.yield_10y,
            y.yield_30y,
            y.fed_funds_effective,
            s.spread_2s10s,
            s.spread_3m10y,
            s.is_inverted_2s10s,
            s.is_inverted_3m10y,
            r.cpi_yoy_pct,
            r.real_yield_2y,
            r.real_yield_10y,
            r.real_fed_funds,
            t.nfci,
            t.nfci_above_zero,
            t.stress_regime,
            t.unemployment_rate
        from latest
        inner join marts.fct_yield_curve_daily as y using (curve_date)
        inner join marts.fct_curve_spreads as s using (curve_date)
        inner join marts.fct_real_rates as r using (curve_date)
        inner join marts.fct_stress_regime as t using (curve_date)
        """,
    )
    fill = _row(
        connection,
        """
        select
            count(*) filter (where yield_10y_days_carried > 0) as yield_10y_carried_days,
            count(*) filter (
                where yield_30y is null
                  and curve_date >= (
                      select min(curve_date)
                      from marts.fct_yield_curve_daily
                      where yield_30y is not null
                  )
            ) as yield_30y_null_days_after_first_print
        from marts.fct_yield_curve_daily
        """,
    )
    inversion_totals = _rows(
        connection,
        """
        select
            spread_code,
            count(*) as episode_count,
            count(*) filter (where is_open) as open_count,
            min(length_business_days) as shortest_business_days,
            max(length_business_days) as longest_business_days,
            cast(median(length_business_days) as double) as median_business_days
        from marts.dim_inversion_episodes
        group by spread_code
        order by spread_code
        """,
    )
    longest_rows = _rows(
        connection,
        """
        select
            spread_code,
            episode_id,
            start_date,
            end_date,
            length_business_days,
            length_calendar_days,
            depth_bps,
            trough_spread_pp,
            trough_date,
            is_open
        from (
            select
                *,
                row_number() over (
                    partition by spread_code
                    order by length_business_days desc, start_date
                ) as episode_rank
            from marts.dim_inversion_episodes
        )
        where episode_rank = 1
        order by spread_code
        """,
    )
    longest_by_code = {row["spread_code"]: row for row in longest_rows}
    inversions: dict[str, JsonObject] = {}
    for row in inversion_totals:
        code = str(row["spread_code"])
        longest = dict(longest_by_code[code])
        longest.pop("spread_code", None)
        inversions[code] = {
            "episode_count": row["episode_count"],
            "open_count": row["open_count"],
            "shortest_business_days": row["shortest_business_days"],
            "longest_business_days": row["longest_business_days"],
            "median_business_days": row["median_business_days"],
            "longest": longest,
        }
    stress = _row(
        connection,
        """
        with flagged as (
            select
                curve_date,
                stress_regime,
                case when stress_regime is true then 0 else 1 end as breaker
            from marts.fct_stress_regime
        ),
        grouped as (
            select
                stress_regime,
                sum(breaker) over (order by curve_date) as episode_group
            from flagged
        ),
        episodes as (
            select episode_group
            from grouped
            where stress_regime is true
            group by episode_group
        )
        select
            (select count(*) from marts.fct_stress_regime) as business_days,
            (
                select count(*)
                from marts.fct_stress_regime
                where stress_regime is true
            ) as stress_days,
            (
                select count(*)
                from marts.fct_stress_regime
                where stress_regime is false
            ) as not_stress_days,
            (
                select count(*)
                from marts.fct_stress_regime
                where stress_regime is null
            ) as unknown_days,
            (select count(*) from episodes) as stress_episode_count
        """,
    )
    totals = status_totals(outcomes)
    return {
        "snapshot_date": snapshot_date,
        "retrieved_at": retrieved_at,
        "panel": panel,
        "latest_curve": latest,
        "fill": fill,
        "inversions": inversions,
        "stress": stress,
        "dbt_tests": {
            "pass": totals.get("pass", 0),
            "warn": totals.get("warn", 0),
            "fail": totals.get("fail", 0),
            "error": totals.get("error", 0),
            "by_category": counts_by_category(outcomes),
        },
    }


def write_highlights(path: Path, payload: JsonObject) -> None:
    """Write the summary JSON used by the README."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
