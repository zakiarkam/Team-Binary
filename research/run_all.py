#!/usr/bin/env python
"""Run every experiment and write the results the report is built from.

    venv/bin/python -m research.run_all              # all seven
    venv/bin/python -m research.run_all --only E1,E4
    venv/bin/python -m research.run_all --no-figures

Outputs, all regenerable and all overwritten on each run:

    research/results/results.json      every metric, note and status
    research/results/<table>.csv       one file per results table
    research/figures/*.png|.pdf        drawn from those results, not by hand

An experiment that cannot run records `status: skipped` with the reason and the
others carry on. A failure is caught, recorded with its traceback, and does not
take the run down — because the most likely reason for one to fail is a missing
optional input, and losing six results to that would be absurd.

Exit code is 1 if anything failed outright, so `make research` fails loudly in
CI while still producing whatever it could.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Module 4 keeps flat internal imports from its own folder.
M4_DIR = ROOT / "modules" / "m4_content"
if str(M4_DIR) not in sys.path:
    sys.path.insert(1, str(M4_DIR))

# Loaded before anything numeric: this process touches XGBoost and, through
# Sentence-BERT, torch. See openmp_guard.py.
import openmp_guard  # noqa: E402, F401  (import order matters)

import argparse  # noqa: E402
import importlib  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
import traceback  # noqa: E402

import pandas as pd  # noqa: E402

from research import config  # noqa: E402
from research.experiments import REGISTRY  # noqa: E402

BOLD, DIM, GREEN, AMBER, RED, RESET = (
    "\033[1m", "\033[2m", "\033[32m", "\033[33m", "\033[31m", "\033[0m")


def _run_one(key: str, module_path: str) -> dict:
    started = time.time()
    try:
        module = importlib.import_module(module_path)
        result = module.run()
    except Exception as exc:
        return {
            "id": key,
            "title": getattr(sys.modules.get(module_path), "TITLE", key),
            "status": "failed",
            "reason": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc()[-2000:],
            "seconds": round(time.time() - started, 1),
        }
    result.setdefault("id", key)
    result.setdefault("status", "ok")
    result["seconds"] = round(time.time() - started, 1)
    return result


def _write_tables(result: dict) -> list[str]:
    written = []
    for name, rows in (result.get("tables") or {}).items():
        if not rows:
            continue
        path = config.RESULTS / f"{name}.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        written.append(path.name)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", default=None,
                        help="Comma-separated experiment ids, e.g. E1,E4")
    parser.add_argument("--no-figures", action="store_true",
                        help="Skip figure generation")
    args = parser.parse_args()

    config.ensure_dirs()

    selected = REGISTRY
    if args.only:
        wanted = {k.strip().upper() for k in args.only.split(",") if k.strip()}
        unknown = wanted - set(REGISTRY)
        if unknown:
            print(f"Unknown experiment id(s): {', '.join(sorted(unknown))}",
                  file=sys.stderr)
            print(f"Available: {', '.join(sorted(REGISTRY))}", file=sys.stderr)
            return 2
        selected = {k: v for k, v in REGISTRY.items() if k in wanted}

    print(f"{BOLD}Research experiments{RESET}  "
          f"({len(selected)} of {len(REGISTRY)})\n")

    results, failures = {}, 0
    for key, module_path in sorted(selected.items()):
        print(f"{BOLD}{key}{RESET} … ", end="", flush=True)
        result = _run_one(key, module_path)
        results[key] = result

        status = result["status"]
        colour = {"ok": GREEN, "skipped": AMBER, "failed": RED}[status]
        print(f"{colour}{status}{RESET} {DIM}({result['seconds']}s){RESET}")
        print(f"   {result.get('title', '')}")

        if status == "ok":
            for name in _write_tables(result):
                print(f"   {DIM}→ results/{name}{RESET}")
            for note in (result.get("notes") or [])[:2]:
                print(f"   {DIM}· {note[:110]}{'…' if len(note) > 110 else ''}{RESET}")
        else:
            print(f"   {colour}{result.get('reason', '')}{RESET}")
            if status == "failed":
                failures += 1
        print()

    out = config.RESULTS / "results.json"

    # A partial run must not delete the results it did not rerun. `--only E1`
    # once wiped six experiments out of results.json, and the chapters silently
    # regenerated without them — so previous results are merged, and only the
    # experiments that actually ran are replaced.
    merged = dict(results)
    if args.only and out.exists():
        try:
            previous = json.loads(out.read_text(encoding="utf-8"))
            merged = {**previous.get("experiments", {}), **results}
        except (OSError, json.JSONDecodeError):
            print(f"{AMBER}   (could not read previous results — writing only "
                  f"this run){RESET}")

    summary = {
        "generated_by": "research/run_all.py",
        "seed": config.SEED,
        "n_bootstrap": config.N_BOOTSTRAP,
        "n_seeds": config.N_SEEDS,
        "experiments": merged,
        "status_counts": {
            s: sum(1 for r in merged.values() if r["status"] == s)
            for s in ("ok", "skipped", "failed")
        },
    }
    out.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"{BOLD}Wrote{RESET} {out.relative_to(ROOT)}")

    if not args.no_figures and any(r["status"] == "ok" for r in results.values()):
        print(f"\n{BOLD}Figures{RESET}")
        try:
            from research import figures

            for name in figures.build_all(summary):
                print(f"   {DIM}→ figures/{name}{RESET}")
        except Exception as exc:
            print(f"   {RED}figure generation failed: "
                  f"{type(exc).__name__}: {exc}{RESET}")
            traceback.print_exc(limit=3)
            failures += 1

    counts = summary["status_counts"]
    print(f"\n{BOLD}Done.{RESET} {counts['ok']} ok · {counts['skipped']} skipped · "
          f"{counts['failed']} failed")
    if counts["skipped"]:
        print(f"{DIM}Skipped experiments need an input that is not present; each "
              f"records its reason in results.json.{RESET}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
