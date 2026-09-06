"""Adapter: Module 3 (analytics) outputs -> Module 4 (content) priorities.

Closes the loop. Module 3 tells the content engine *what worked*:
  - which platforms earn the most conversion credit  -> prioritise those
  - which automation strategy converts best          -> campaign context
  - the dominant recommended next-best-action        -> content intent

Module 4 already infers goal + tone from the product website; this adapter adds
an analytics-driven *platform emphasis* and *campaign context* on top, so future
content is generated for the platforms the data says convert.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


def _aggregate_platform_credits(analytics_records: list[dict]) -> dict[str, float]:
    """Sum per-user platform_credits into a normalised platform ranking."""
    totals: Counter = Counter()
    for rec in analytics_records:
        for plat, credit in (rec.get("platform_credits") or {}).items():
            totals[plat] += float(credit)
    s = sum(totals.values()) or 1.0
    return {p: round(v / s, 4) for p, v in totals.most_common()}


def build_content_priorities(
    reports_dir: str | Path,
    max_records: int = 4000,
) -> dict[str, Any]:
    """Derive content-generation priorities from Module 3's committed artifacts.

    Reads (all optional, degrades gracefully):
      - analytics_output.json      (per-user predictions + credits + rec)
      - strategy_comparison.csv    (which strategy converts best)
      - insights.md                (human-readable system insights)
    """
    reports_dir = Path(reports_dir)
    out: dict[str, Any] = {
        "platform_ranking": {},
        "top_platforms": [],
        "best_strategy": None,
        "recommendation_mix": {},
        "insights": [],
        "source": str(reports_dir),
    }

    # --- platform ranking + recommendation mix (from analytics_output.json) ---
    aout = reports_dir / "analytics_output.json"
    if aout.exists():
        records = json.loads(aout.read_text())[:max_records]
        ranking = _aggregate_platform_credits(records)
        out["platform_ranking"] = ranking
        out["top_platforms"] = list(ranking.keys())[:3]
        rec_counts = Counter(r.get("recommendation") for r in records if r.get("recommendation"))
        total = sum(rec_counts.values()) or 1
        out["recommendation_mix"] = {k: round(v / total, 3) for k, v in rec_counts.most_common()}

    # --- best strategy (highest conversion_rate) ---
    scmp = reports_dir / "strategy_comparison.csv"
    if scmp.exists():
        df = pd.read_csv(scmp)
        rate_col = next((c for c in ("conversion_rate", "conv_rate") if c in df.columns), None)
        strat_col = "strategy" if "strategy" in df.columns else df.columns[0]
        if rate_col:
            best = df.sort_values(rate_col, ascending=False).iloc[0]
            out["best_strategy"] = {
                "strategy": str(best[strat_col]),
                "conversion_rate": float(best[rate_col]),
            }

    # --- narrative insights ---
    ins = reports_dir / "insights.md"
    if ins.exists():
        out["insights"] = [
            line.lstrip("- ").strip()
            for line in ins.read_text().splitlines()
            if line.strip().startswith("-")
        ]

    return out


def apply_to_platforms(
    requested_platforms: list[str],
    priorities: dict[str, Any],
) -> list[str]:
    """Re-order the user's requested platforms so analytics-favoured ones come first.

    Never drops a user-requested platform; only reorders by conversion credit.
    """
    ranking = priorities.get("platform_ranking", {}) or {}
    if not ranking:
        return requested_platforms
    return sorted(
        requested_platforms,
        key=lambda p: ranking.get(p.lower(), 0.0),
        reverse=True,
    )
