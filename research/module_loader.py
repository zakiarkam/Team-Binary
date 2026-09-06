"""Import Module 2's and Module 3's code in the same process.

Both were written as standalone projects, and both put their code in a
top-level package called `src`. Importing one and then the other in a single
interpreter silently returns the *first* one, because `sys.modules["src"]` is
already populated — so `from src import attribution` inside a Module 3 helper
happily hands back Module 2's package and fails with a confusing ImportError
several frames later.

The production API never hits this: it only ever loads Module 3. The research
runner loads both, so it needs to say which `src` it means.

Rewriting either module to use a distinct package name would be the tidier fix,
but it would touch code that is already written up in the report. Evicting the
cached package before each load is contained entirely within the research layer,
which is the right place for a problem that only the research layer has.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def load(root: Path, dotted: str):
    """Import `src.<dotted>` from a specific module root.

    Any previously cached `src` package is dropped first, so the import resolves
    against `root` and not against whichever module happened to be loaded
    earlier in the run.
    """
    for name in [k for k in sys.modules if k == "src" or k.startswith("src.")]:
        del sys.modules[name]

    root_str = str(root)
    while root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)

    return importlib.import_module(f"src.{dotted}")
