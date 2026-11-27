"""Public FRED series used by the macro and rates mart."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SeriesSpec:
    """One FRED series in the committed snapshot."""

    series_id: str
    filename: str
    title: str
    frequency: str
    unit: str
    seasonal_adjustment: str
    history_start: date
    measure_name: str


SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec(
        series_id="DGS3MO",
        filename="dgs3mo.csv",
        title=(
            "Market Yield on U.S. Treasury Securities at 3-Month Constant Maturity, "
            "Quoted on an Investment Basis"
        ),
        frequency="daily",
        unit="percent",
        seasonal_adjustment="not seasonally adjusted",
        history_start=date(1981, 9, 1),
        measure_name="yield_3m",
    ),
    SeriesSpec(
        series_id="DGS2",
        filename="dgs2.csv",
        title=(
            "Market Yield on U.S. Treasury Securities at 2-Year Constant Maturity, "
            "Quoted on an Investment Basis"
        ),
        frequency="daily",
        unit="percent",
        seasonal_adjustment="not seasonally adjusted",
        history_start=date(1976, 6, 1),
        measure_name="yield_2y",
    ),
    SeriesSpec(
        series_id="DGS5",
        filename="dgs5.csv",
        title=(
            "Market Yield on U.S. Treasury Securities at 5-Year Constant Maturity, "
            "Quoted on an Investment Basis"
        ),
        frequency="daily",
        unit="percent",
        seasonal_adjustment="not seasonally adjusted",
        history_start=date(1962, 1, 2),
        measure_name="yield_5y",
    ),
    SeriesSpec(
        series_id="DGS10",
        filename="dgs10.csv",
        title=(
            "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, "
            "Quoted on an Investment Basis"
        ),
        frequency="daily",
        unit="percent",
        seasonal_adjustment="not seasonally adjusted",
        history_start=date(1962, 1, 2),
        measure_name="yield_10y",
    ),
    SeriesSpec(
        series_id="DGS30",
        filename="dgs30.csv",
        title=(
            "Market Yield on U.S. Treasury Securities at 30-Year Constant Maturity, "
            "Quoted on an Investment Basis"
        ),
        frequency="daily",
        unit="percent",
        seasonal_adjustment="not seasonally adjusted",
        history_start=date(1977, 2, 15),
        measure_name="yield_30y",
    ),
    SeriesSpec(
        series_id="DFF",
        filename="dff.csv",
        title="Federal Funds Effective Rate",
        frequency="daily",
        unit="percent",
        seasonal_adjustment="not seasonally adjusted",
        history_start=date(1954, 7, 1),
        measure_name="fed_funds_effective",
    ),
    SeriesSpec(
        series_id="CPIAUCSL",
        filename="cpiaucsl.csv",
        title="Consumer Price Index for All Urban Consumers: All Items in U.S. City Average",
        frequency="monthly",
        unit="index",
        seasonal_adjustment="seasonally adjusted",
        history_start=date(1947, 1, 1),
        measure_name="cpi_index",
    ),
    SeriesSpec(
        series_id="UNRATE",
        filename="unrate.csv",
        title="Unemployment Rate",
        frequency="monthly",
        unit="percent",
        seasonal_adjustment="seasonally adjusted",
        history_start=date(1948, 1, 1),
        measure_name="unemployment_rate",
    ),
    SeriesSpec(
        series_id="NFCI",
        filename="nfci.csv",
        title="Chicago Fed National Financial Conditions Index",
        frequency="weekly",
        unit="index",
        seasonal_adjustment="not seasonally adjusted",
        history_start=date(1971, 1, 8),
        measure_name="nfci",
    ),
)

SERIES_BY_ID: dict[str, SeriesSpec] = {spec.series_id: spec for spec in SERIES}


def get_series(series_id: str) -> SeriesSpec:
    """Return the catalog entry for a FRED series id."""
    try:
        return SERIES_BY_ID[series_id]
    except KeyError as exc:
        known = ", ".join(spec.series_id for spec in SERIES)
        raise KeyError(f"unknown series {series_id}; known series: {known}") from exc
