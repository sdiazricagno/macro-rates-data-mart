"""Summarize a dbt run_results.json payload."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestOutcome:
    """One dbt test result."""

    name: str
    status: str
    category: str


def classify_test(name: str) -> str:
    """Group a dbt test name into a coverage category."""
    if "zscore_anomaly" in name:
        return "z-score"
    if "accepted_range" in name:
        return "accepted range"
    if name.startswith("not_null") or ".not_null" in name:
        return "not null"
    if name.startswith("unique") or ".unique_" in name:
        return "unique"
    if "accepted_values" in name:
        return "accepted values"
    return "singular"


def result_name(unique_id: str) -> str:
    """Return the test node name from a dbt unique id."""
    parts = unique_id.split(".")
    if len(parts) >= 3:
        return parts[2]
    return unique_id


def summarize_run_results(payload: dict[str, object]) -> list[TestOutcome]:
    """Keep test nodes from a dbt run_results document."""
    results = payload.get("results", [])
    if not isinstance(results, list):
        raise ValueError("run_results.results must be a list")
    outcomes: list[TestOutcome] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        unique_id = str(row.get("unique_id", ""))
        if not unique_id.startswith("test."):
            continue
        name = result_name(unique_id)
        status = str(row.get("status", "error"))
        outcomes.append(TestOutcome(name=name, status=status, category=classify_test(name)))
    return outcomes


def counts_by_category(outcomes: list[TestOutcome]) -> dict[str, dict[str, int]]:
    """Count statuses inside each category. Categories stay in a stable order."""
    order = ["not null", "unique", "accepted range", "accepted values", "singular", "z-score"]
    buckets: dict[str, dict[str, int]] = {name: defaultdict(int) for name in order}
    for outcome in outcomes:
        buckets.setdefault(outcome.category, defaultdict(int))
        status = "pass" if outcome.status in {"pass", "success"} else outcome.status
        buckets[outcome.category][status] += 1
    return {name: dict(counts) for name, counts in buckets.items() if counts}


def status_totals(outcomes: list[TestOutcome]) -> dict[str, int]:
    """Count outcomes by dbt status. `success` and `pass` are both passes."""
    totals: dict[str, int] = defaultdict(int)
    for outcome in outcomes:
        status = "pass" if outcome.status in {"pass", "success"} else outcome.status
        totals[status] += 1
    return dict(totals)


def load_run_results(path: Path) -> dict[str, object]:
    """Read run_results.json."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("run_results.json must be an object")
    return payload
