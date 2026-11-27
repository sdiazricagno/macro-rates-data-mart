"""Charts rendered from mart rows. Matplotlib only, Agg backend."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

TENOR_COLORS = {
    "3-month": "#0072B2",
    "2-year": "#E69F00",
    "5-year": "#009E73",
    "10-year": "#D55E00",
    "30-year": "#CC79A7",
}
SPREAD_COLORS = {"2s10s": "#0072B2", "3m10y": "#D55E00"}
SHADE_COLOR = "#F4C7C3"
STRESS_COLOR = "#F4A261"
PASS_COLOR = "#2A9D8F"
WARN_COLOR = "#E9C46A"
FAIL_COLOR = "#E76F51"


def _as_float(values: Sequence[float | None]) -> list[float]:
    return [float("nan") if value is None else float(value) for value in values]


def contiguous_spans(
    dates: Sequence[date],
    flags: Sequence[bool | None],
) -> list[tuple[date, date]]:
    """Collapse a daily boolean mask into inclusive [start, end] spans."""
    if len(dates) != len(flags):
        raise ValueError("dates and flags must have the same length")
    spans: list[tuple[date, date]] = []
    start: date | None = None
    previous: date | None = None
    for day, flag in zip(dates, flags, strict=True):
        if flag:
            if start is None:
                start = day
            previous = day
        elif start is not None and previous is not None:
            spans.append((start, previous))
            start = None
            previous = None
    if start is not None and previous is not None:
        spans.append((start, previous))
    return spans


def _shade(ax: plt.Axes, spans: Sequence[tuple[date, date]], color: str) -> None:
    labeled = False
    for start, end in spans:
        ax.axvspan(
            start,
            end + timedelta(days=1),
            color=color,
            alpha=0.45,
            linewidth=0,
            label="inversion" if not labeled else None,
        )
        labeled = True


def _finish(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#E6E6E6",
            "grid.linewidth": 0.6,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.titlesize": 13,
            "axes.labelsize": 10,
        }
    )


def save_yield_curve(
    path: Path,
    dates: Sequence[date],
    tenors: Mapping[str, Sequence[float | None]],
    *,
    snapshot_date: str,
) -> None:
    """Treasury yields in percent, one line per tenor."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(11, 6.2), layout="constrained")
    for name, values in tenors.items():
        ax.plot(
            dates,
            _as_float(values),
            label=name,
            color=TENOR_COLORS.get(name, "#333333"),
            linewidth=1.1,
        )
    ax.set_title("Treasury yield curve")
    ax.set_ylabel("Yield (percent)")
    ax.set_xlabel("Date")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.legend(frameon=False, ncol=5, loc="upper right")
    ax.annotate(
        f"FRED public data, snapshot {snapshot_date}",
        xy=(0, -0.16),
        xycoords="axes fraction",
        fontsize=8,
        color="#555555",
    )
    _finish(fig, path)


def save_spread_chart(
    path: Path,
    dates: Sequence[date],
    spread_2s10s: Sequence[float | None],
    spread_3m10y: Sequence[float | None],
    inversions_2s10s: Sequence[tuple[date, date]],
    inversions_3m10y: Sequence[tuple[date, date]],
    *,
    snapshot_date: str,
) -> None:
    """2s10s and 3m10y with inversion spells shaded."""
    _apply_style()
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True, layout="constrained")
    panels = (
        (
            axes[0],
            "2s10s (10-year minus 2-year)",
            spread_2s10s,
            inversions_2s10s,
            SPREAD_COLORS["2s10s"],
        ),
        (
            axes[1],
            "3m10y (10-year minus 3-month)",
            spread_3m10y,
            inversions_3m10y,
            SPREAD_COLORS["3m10y"],
        ),
    )
    for ax, title, values, spans, color in panels:
        _shade(ax, spans, SHADE_COLOR)
        ax.plot(dates, _as_float(values), color=color, linewidth=1.05, label=title)
        ax.axhline(0, color="#444444", linewidth=0.8)
        ax.set_ylabel("Percentage points")
        ax.set_title(title)
        ax.legend(frameon=False, loc="upper right")
    axes[1].set_xlabel("Date")
    axes[1].xaxis.set_major_locator(mdates.AutoDateLocator())
    axes[1].annotate(
        f"Shaded spans are negative spreads. FRED public data, snapshot {snapshot_date}.",
        xy=(0, -0.22),
        xycoords="axes fraction",
        fontsize=8,
        color="#555555",
    )
    _finish(fig, path)


def save_stress_chart(
    path: Path,
    dates: Sequence[date],
    nfci: Sequence[float | None],
    stress: Sequence[bool | None],
    *,
    snapshot_date: str,
) -> None:
    """NFCI with the documented stress regime shaded."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(11, 6.2), layout="constrained")
    spans = contiguous_spans(dates, stress)
    labeled = False
    for start, end in spans:
        ax.axvspan(
            start,
            end + timedelta(days=1),
            color=STRESS_COLOR,
            alpha=0.45,
            linewidth=0,
            label="stress regime" if not labeled else None,
        )
        labeled = True
    ax.plot(dates, _as_float(nfci), color="#1D3557", linewidth=1.1, label="NFCI")
    ax.axhline(0, color="#444444", linewidth=0.8, label="NFCI = 0")
    ax.set_title("Stress regime and financial conditions")
    ax.set_ylabel("NFCI (index)")
    ax.set_xlabel("Date")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.legend(frameon=False, loc="upper right")
    ax.annotate(
        "Stress means 2s10s is negative and NFCI is above zero. "
        f"FRED public data, snapshot {snapshot_date}.",
        xy=(0, -0.18),
        xycoords="axes fraction",
        fontsize=8,
        color="#555555",
    )
    _finish(fig, path)


def save_coverage_chart(
    path: Path,
    counts_by_category: Mapping[str, Mapping[str, int]],
    *,
    snapshot_date: str,
) -> None:
    """Pass, warn, and fail counts by dbt test category."""
    _apply_style()
    categories = list(counts_by_category)
    passed = [counts_by_category[name].get("pass", 0) for name in categories]
    warned = [counts_by_category[name].get("warn", 0) for name in categories]
    failed = [
        counts_by_category[name].get("fail", 0) + counts_by_category[name].get("error", 0)
        for name in categories
    ]
    fig, ax = plt.subplots(figsize=(11, 5.6), layout="constrained")
    positions = list(range(len(categories)))
    ax.barh(positions, passed, color=PASS_COLOR, label="pass")
    ax.barh(positions, warned, left=passed, color=WARN_COLOR, label="warn")
    left_fail = [p + w for p, w in zip(passed, warned, strict=True)]
    ax.barh(positions, failed, left=left_fail, color=FAIL_COLOR, label="fail")
    ax.set_yticks(positions, categories)
    ax.set_xlabel("Tests")
    ax.set_title("dbt test results")
    ax.legend(frameon=False, loc="upper right")
    ax.annotate(
        f"Built on the committed FRED snapshot {snapshot_date}.",
        xy=(0, -0.16),
        xycoords="axes fraction",
        fontsize=8,
        color="#555555",
    )
    _finish(fig, path)
