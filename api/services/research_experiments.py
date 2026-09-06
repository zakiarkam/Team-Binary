"""Every module's research results — the E1–E11 experiment layer.

`research/run_all.py` writes one `results.json` holding each experiment's
headline metrics, result tables and the caveats that must travel with them,
plus a figure per experiment under `research/figures/`. This module reads
those files and nothing else: the dashboard shows exactly the numbers the
report cites and can never drift from them.

Grouping is read from the experiment's own title ("Module 4 — ..."), which the
experiment authors, so adding an experiment needs no change here.

Distinct from api/services/research_m2.py, which reads Module 2's own
simulation pipeline output (modules/m2_automation/outputs).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_PATH = REPO_ROOT / "research" / "results" / "results.json"
FIGURES_DIR = REPO_ROOT / "research" / "figures"

# E8's qini curves alone are ~250 rows: enough to stall a page and far more
# than anyone reads on screen. Truncated tables report their true length so
# the view never implies it is showing everything.
MAX_TABLE_ROWS = 60

_MODULE_IN_TITLE = re.compile(r"^Module\s+(\d+)\s*[—–-]\s*(.*)$")

MODULE_NAMES = {
    1: "Audience Segmentation",
    2: "Marketing Automation",
    3: "Analytics & Decision Support",
    4: "Content Refinery",
}


def _load() -> dict[str, Any] | None:
    """The whole results file, or None if the experiments have never been run
    on this machine (or the file is unreadable)."""
    if not RESULTS_PATH.is_file():
        return None
    try:
        with RESULTS_PATH.open() as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _split_title(title: str) -> tuple[int | None, str]:
    """("Module 4 — goal and tone…") -> (4, "goal and tone…").

    An experiment whose title carries no module prefix belongs to no page; it
    still appears in results.json and in the report, just not in a module tab.
    """
    match = _MODULE_IN_TITLE.match(title or "")
    if not match:
        return None, title or ""
    return int(match.group(1)), match.group(2).strip()


def _figure_names() -> set[str]:
    """Every figure on disk — also the allowlist the figure route validates
    against, so that route can never read an arbitrary path."""
    if not FIGURES_DIR.is_dir():
        return set()
    return {p.name for p in FIGURES_DIR.glob("fig_e*.png")}


def figure_path(name: str) -> Path | None:
    """Resolve a figure filename to its file, or None if it is not one of the
    figures the experiment run produced."""
    if name not in _figure_names():
        return None
    path = FIGURES_DIR / name
    return path if path.is_file() else None


def _figures_for(exp_id: str) -> list[str]:
    """Figures belonging to one experiment.

    Matched on the `fig_e6_` prefix including the trailing underscore — without
    it, E1's prefix would also swallow E10's and E11's figures.
    """
    prefix = f"fig_{exp_id.lower()}_"
    return sorted(n for n in _figure_names() if n.startswith(prefix))


def _table(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """One result table, with its columns in the order the experiment wrote
    them and its length preserved even when the rows are cut."""
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return {
        "name": name,
        "columns": columns,
        "rows": rows[:MAX_TABLE_ROWS],
        "row_count": len(rows),
        "truncated": len(rows) > MAX_TABLE_ROWS,
    }


def _experiment(exp: dict[str, Any], short_title: str) -> dict[str, Any]:
    return {
        "id": exp.get("id", ""),
        "title": exp.get("title", ""),
        "short_title": short_title,
        "status": exp.get("status", "unknown"),
        "reason": exp.get("reason"),
        # Metrics stay raw — a confidence interval arrives as [low, high] and is
        # formatted for display by the caller, not flattened into a string here.
        "metrics": exp.get("metrics", {}),
        "tables": [
            _table(name, rows)
            for name, rows in (exp.get("tables") or {}).items()
            if isinstance(rows, list)
        ],
        "notes": exp.get("notes", []),
        "figures": _figures_for(exp.get("id", "")),
    }


def module_results(module: int) -> dict[str, Any]:
    """Every experiment belonging to one module, in E-number order.

    Returns available=False rather than raising when the experiments have not
    been run, so the page degrades to a hint instead of an error — the same
    pattern the live views use for "no data yet".
    """
    data = _load()
    empty = {
        "available": False,
        "module": module,
        "module_name": MODULE_NAMES.get(module),
        "experiments": [],
        "meta": None,
    }
    if data is None:
        return empty

    experiments = []
    for exp in (data.get("experiments") or {}).values():
        owner, short_title = _split_title(exp.get("title", ""))
        if owner == module:
            experiments.append(_experiment(exp, short_title))

    if not experiments:
        return empty

    experiments.sort(key=lambda e: int(e["id"][1:] or 0) if e["id"][1:].isdigit() else 0)

    return {
        "available": True,
        "module": module,
        "module_name": MODULE_NAMES.get(module),
        "experiments": experiments,
        "meta": {
            "generated_by": data.get("generated_by"),
            "seed": data.get("seed"),
            "n_bootstrap": data.get("n_bootstrap"),
            "n_seeds": data.get("n_seeds"),
        },
    }
