#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run_person3.sh — Run ONLY Module 3 (Marketing Analytics & Decision Support)
# end-to-end, in isolation from the other modules.
#
# What it does:
#   1. Picks a Python interpreter (prefers the repo venv if present).
#   2. Installs this module's requirements (skip with --no-install).
#   3. Runs the full analytics pipeline (simulate → features → train models →
#      evaluation studies → recommendations → bootstrap CIs → learned
#      recommender → SHAP). This REGENERATES outputs/models/*.pkl, which are
#      not committed to git.
#   4. Runs the smoke-test suite.
#   5. Prints how to launch the Streamlit dashboard.
#
# Usage:
#   bash run_person3.sh                # full run (install + pipeline + tests)
#   bash run_person3.sh --no-install   # skip pip install (deps already present)
#   bash run_person3.sh --regenerate   # re-simulate data from scratch
#   bash run_person3.sh --dashboard    # after a run, also launch the dashboard
# ---------------------------------------------------------------------------
set -euo pipefail

# Always run from this module's directory, no matter where invoked from.
cd "$(dirname "$0")"
MODULE_DIR="$(pwd)"
echo "Module dir: ${MODULE_DIR}"

# ---- flags ----------------------------------------------------------------
DO_INSTALL=1
REGENERATE=""
LAUNCH_DASHBOARD=0
for arg in "$@"; do
  case "$arg" in
    --no-install)  DO_INSTALL=0 ;;
    --regenerate)  REGENERATE="--regenerate" ;;
    --dashboard)   LAUNCH_DASHBOARD=1 ;;
    *) echo "Unknown flag: $arg"; exit 2 ;;
  esac
done

# ---- pick a Python interpreter --------------------------------------------
# Prefer the repo-root venv (has all deps), else module venv, else system python3.
if   [ -x "../../venv/bin/python" ];      then PY="../../venv/bin/python"
elif [ -x "../../.venv/bin/python" ];     then PY="../../.venv/bin/python"
elif [ -x "./venv/bin/python" ];          then PY="./venv/bin/python"
else PY="python3"; fi
echo "Using Python: ${PY}  ($(${PY} --version 2>&1))"

# ---- install requirements -------------------------------------------------
if [ "$DO_INSTALL" -eq 1 ]; then
  echo "== Installing requirements (use --no-install to skip) =="
  "${PY}" -m pip install -q -r requirements.txt
fi

# ---- run the full analytics pipeline --------------------------------------
echo "== Running full analytics pipeline =="
"${PY}" -m src.pipeline --full ${REGENERATE}

# ---- run tests ------------------------------------------------------------
# The bank-marketing calibration test self-skips when its git-ignored data
# file is absent, so the whole suite runs cleanly here.
echo "== Running smoke tests =="
"${PY}" -m pytest tests/ -q || { echo "TESTS FAILED"; exit 1; }

echo ""
echo "== Module 3 run complete. Key artifacts =="
echo "  Per-user analytics : outputs/reports/analytics_output.json"
echo "  Model metrics       : outputs/reports/model_metrics.csv"
echo "  System insights     : outputs/reports/insights.md"
echo "  Figures             : outputs/figures/"
echo "  Trained models      : outputs/models/  (regenerated, not committed)"
echo ""

# ---- optionally launch the dashboard --------------------------------------
if [ "$LAUNCH_DASHBOARD" -eq 1 ]; then
  echo "== Launching Streamlit dashboard (Ctrl-C to stop) =="
  "${PY}" -m streamlit run dashboard/app.py
else
  echo "To launch the dashboard:"
  echo "  ${PY} -m streamlit run dashboard/app.py"
  echo "(or re-run:  bash run_person3.sh --no-install --dashboard )"
fi
