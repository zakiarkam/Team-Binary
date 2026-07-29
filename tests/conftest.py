"""Shared pytest setup.

pytest imports conftest before any test module, which makes this the only place
that can reliably fix process-wide native library settings — by the time a test
module runs, numpy and friends are already loaded and the setting is ignored.

Why it matters here: the suite exercises Module 3 (XGBoost) and Module 4
(PyTorch) in a single process. On macOS those two libraries each bundle their
own OpenMP runtime, and using both crashes the interpreter with a bare
`Fatal Python error: Segmentation fault` and no traceback pointing at a test.

Running the suite in one process is worth keeping — it is what catches
cross-module integration problems — so the guard is applied here instead.
See openmp_guard.py for the measurements behind this.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Must happen before numpy / torch / xgboost are imported anywhere.
import openmp_guard  # noqa: E402, F401  (import order matters)
