"""Prevent a macOS segmentation fault caused by two copies of OpenMP.

The problem
-----------
On macOS, both PyTorch and XGBoost ship their own `libomp`. Whichever loads
first wins, and the second one crashes the interpreter outright:

    import xgboost                      # loads xgboost's libomp
    from sentence_transformers import SentenceTransformer
    SentenceTransformer("all-MiniLM-L6-v2")   # → exit code 139 (SIGSEGV)

Reverse the order and both coexist happily. `KMP_DUPLICATE_LIB_OK=TRUE`, the
usual advice for this class of problem, does **not** help here.

This bites the content module (Module 4), which legitimately needs XGBoost for
the goal/tone classifiers *and* PyTorch for Sentence-BERT and Phi-3. Symptom:
`goal_tone.train()` dies silently with no traceback, so the label encoders are
never written and content generation fails later with a confusing
"Missing label encoder" error a long way from the real cause.

What was measured
-----------------
On this project (torch 2.13, xgboost 3.2, macOS arm64), against a process that
loads Sentence-BERT and then uses an XGBoost model:

    KMP_DUPLICATE_LIB_OK=TRUE ........... still segfaults
    XGBoost estimator n_jobs/nthread=1 .. still segfaults
    torch on CPU rather than MPS ........ still segfaults
    correct import order alone .......... still segfaults (on predict/fit)
    OMP_NUM_THREADS=1 ................... works

Both XGBoost `.fit()` and `.predict()` are affected, so restricting this to
training is not enough — anything that scores an XGBoost model alongside torch
needs it, which includes the analytics recommender in Module 3.

The fix
-------
Import this module **before** anything numeric. It pins the OpenMP runtime to a
single thread and loads torch ahead of xgboost.

The single thread is a real cost, but a small one here: Phi-3 and Sentence-BERT
run on MPS rather than through OpenMP, and the tabular datasets are at most tens
of thousands of rows. A slower pipeline beats one that dies with no traceback.

Override when you know torch is not involved:

    PIPELINE_NUM_THREADS=8 python <script>
"""

from __future__ import annotations

import os
import sys


def apply() -> bool:
    """Pin OpenMP to one thread, then load torch ahead of xgboost.

    Returns True if torch is now importable.
    """
    if sys.platform == "darwin":
        # An explicit PIPELINE_NUM_THREADS wins — this only supplies the default.
        threads = os.environ.get("PIPELINE_NUM_THREADS", "1")
        for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            os.environ.setdefault(var, threads)
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

    if "xgboost" in sys.modules and "torch" not in sys.modules:
        # Too late to reorder in this process — warn rather than crash later.
        print(
            "[openmp_guard] warning: xgboost was imported before torch. "
            "Loading a PyTorch model in this process may segfault. "
            "Import openmp_guard earlier.",
            file=sys.stderr,
        )

    try:
        import torch  # noqa: F401  (imported purely for load order)
        return True
    except ImportError:
        # torch is optional for the analytics-only paths.
        return False


# Applied on import so a single `import openmp_guard` is enough.
apply()
