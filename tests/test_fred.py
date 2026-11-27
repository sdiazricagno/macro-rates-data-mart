from datetime import date

import pytest

from macro_rates.fred import (
    TransientFetchError,
    fetch_with_retries,
    parse_fred_csv,
    series_url,
)


def test_series_url_rejects_unknown_characters() -> None:
    with pytest.raises(ValueError):
        series_url("DGS10;drop")


def test_series_url_includes_id_and_window() -> None:
    url = series_url("dgs10", date(2020, 1, 1), date(2020, 12, 31))
    assert url.startswith("https://fred.stlouisfed.org/graph/fredgraph.csv?")
    assert "id=DGS10" in url
    assert "cosd=2020-01-01" in url
    assert "coed=2020-12-31" in url


def test_parse_fred_csv_keeps_missing_and_numeric_tokens() -> None:
    text = "observation_date,DGS10\n2024-01-02,4.10\n2024-01-03,.\n2024-01-04,\n"
    rows = parse_fred_csv(text, "DGS10")
    assert [(row.observation_date, row.value) for row in rows] == [
        (date(2024, 1, 2), "4.10"),
        (date(2024, 1, 3), None),
        (date(2024, 1, 4), None),
    ]


def test_parse_fred_csv_rejects_a_bad_value() -> None:
    text = "DATE,VALUE\n2024-01-02,n/a\n"
    with pytest.raises(ValueError, match="bad value"):
        parse_fred_csv(text, "DGS10")


def test_fetch_with_retries_returns_after_transient_failures() -> None:
    calls = {"count": 0}

    def getter(_url: str) -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise TransientFetchError("temporary")
        return "ok"

    assert (
        fetch_with_retries("https://example.test", getter, attempts=4, base_delay_seconds=0) == "ok"
    )
    assert calls["count"] == 3


def test_fetch_with_retries_raises_when_the_budget_is_spent() -> None:
    def getter(_url: str) -> str:
        raise TransientFetchError("down")

    with pytest.raises(RuntimeError):
        fetch_with_retries("https://example.test", getter, attempts=2, base_delay_seconds=0)
