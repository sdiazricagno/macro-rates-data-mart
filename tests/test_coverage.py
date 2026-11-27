from macro_rates.coverage import (
    classify_test,
    counts_by_category,
    result_name,
    summarize_run_results,
)


def test_classify_and_name() -> None:
    unique_id = "test.macro_rates.not_null_fct_yield_curve_daily_curve_date.abc"
    assert result_name(unique_id) == "not_null_fct_yield_curve_daily_curve_date"
    assert classify_test(result_name(unique_id)) == "not null"
    assert classify_test("zscore_anomaly_fct_curve_spreads_spread_2s10s") == "z-score"
    assert classify_test("assert_spread_equals_leg_difference") == "singular"


def test_summarize_run_results_keeps_tests_only() -> None:
    payload = {
        "results": [
            {"unique_id": "model.macro_rates.fct_yield_curve_daily", "status": "success"},
            {
                "unique_id": "test.macro_rates.accepted_range_fct_curve_spreads_spread_2s10s.fff",
                "status": "pass",
            },
            {
                "unique_id": "test.macro_rates.zscore_anomaly_fct_stress_regime_nfci.eee",
                "status": "warn",
            },
        ]
    }
    outcomes = summarize_run_results(payload)
    assert [outcome.status for outcome in outcomes] == ["pass", "warn"]
    counts = counts_by_category(outcomes)
    assert counts["accepted range"]["pass"] == 1
    assert counts["z-score"]["warn"] == 1
    success = summarize_run_results(
        {"results": [{"unique_id": "test.macro_rates.not_null_x.abc", "status": "success"}]}
    )
    assert counts_by_category(success)["not null"]["pass"] == 1
