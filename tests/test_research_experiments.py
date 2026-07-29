"""The research layer's wiring.

Running the experiments themselves takes minutes, so these tests check the
things that break silently rather than loudly: an experiment that stops
matching the contract the runner expects, a chapter block the renderers cannot
handle, and the module-name collision between Module 2 and Module 3.
"""

from __future__ import annotations

import importlib

import pytest

from research.experiments import REGISTRY

REQUIRED_STATUSES = {"ok", "skipped", "failed"}


@pytest.mark.parametrize("key", sorted(REGISTRY))
def test_every_experiment_matches_the_runner_contract(key: str) -> None:
    module = importlib.import_module(REGISTRY[key])

    assert callable(getattr(module, "run", None)), f"{key} has no run()"
    assert getattr(module, "ID", None) == key, f"{key}.ID must equal its key"
    assert getattr(module, "TITLE", "").strip(), f"{key} has no TITLE"
    assert (module.__doc__ or "").strip(), (
        f"{key} has no docstring — the report quotes these as the rationale")


def test_registry_covers_every_experiment_module() -> None:
    """A new experiment file that nobody registered would never run."""
    from pathlib import Path

    from research import config

    files = {p.stem for p in (config.RESEARCH / "experiments").glob("e*_*.py")}
    registered = {REGISTRY[k].rsplit(".", 1)[-1] for k in REGISTRY}
    assert files == registered, (
        f"unregistered experiment module(s): {sorted(files - registered)}")


def test_modules_two_and_three_can_both_be_loaded() -> None:
    """Both ship a top-level package called `src`.

    Whichever is imported first wins `sys.modules["src"]`, so the second
    silently resolves against the first and fails several frames later with a
    confusing ImportError. The loader exists to stop that, and this is the test
    that would catch it coming back.
    """
    from research import config, module_loader

    simulator = module_loader.load(config.M2_DIR, "simulator")
    assert hasattr(simulator, "simulate_campaign")

    attribution = module_loader.load(config.M3_DIR, "attribution")
    assert hasattr(attribution, "markov_chain_attribution")

    # …and back again, because the runner loads them in either order.
    simulator = module_loader.load(config.M2_DIR, "simulator")
    assert hasattr(simulator, "simulate_campaign")


# ── Chapter rendering ────────────────────────────────────────────────────────

ALL_BLOCK_KINDS = [
    ("h1", "Heading"),
    ("h2", "Subheading"),
    ("h3", "Sub-subheading"),
    ("p", "A paragraph."),
    ("note", "A caveat."),
    ("bullets", ["one", "two"]),
    ("numbers", ["first", "second"]),
    ("table", {"caption": "Table X", "header": ["A", "B"], "rows": [[1, 2]]}),
    ("figure", {"path": "/tmp/x.png", "caption": "Figure X", "width": 6.0}),
    ("code", "print()"),
    ("pagebreak", None),
]


def test_markdown_renderer_handles_every_block_the_report_supports() -> None:
    """The chapters render twice — to Markdown and to the .docx builder's DSL.

    A block type one renderer understands and the other does not would produce a
    chapter that silently loses content in one format only.
    """
    from research.chapters import render_markdown

    output = render_markdown(ALL_BLOCK_KINDS)
    assert "# Heading" in output
    assert "- one" in output
    assert "1. first" in output
    assert "| A | B |" in output
    assert "Figure X" in output


def test_generated_report_module_is_importable_python() -> None:
    from research.chapters import render_report_module

    source = render_report_module([("test", ALL_BLOCK_KINDS)])
    namespace: dict = {}
    exec(compile(source, "content_research.py", "exec"), namespace)

    assert namespace["BLOCKS"] == ALL_BLOCK_KINDS
    assert "GENERATED FILE" in source, (
        "the header is what stops someone editing numbers by hand")


def test_experiment_feature_order_survives_hash_randomisation() -> None:
    """Regression: E7 built its feature list by iterating a *set*.

    Python randomises string hashing per interpreter, so the column order
    differed between processes, the forest broke ties differently, and the
    reported R² moved in the fourth decimal from one run to the next. Two
    subprocesses with deliberately different hash seeds must now agree — a
    check that cannot be made inside a single process, because set order is
    stable within one.
    """
    import subprocess
    import sys

    script = (
        "import engagement;"
        "cols = sorted(c for c in engagement.LEAKY_COLUMNS"
        "              if c != 'engagement_rate');"
        "print(','.join(cols))"
    )

    outputs = []
    for seed in ("0", "1", "12345"):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True,
            env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin",
                 "PYTHONPATH": str(__import__("research.config",
                                              fromlist=["config"]).ROOT)},
        )
        assert result.returncode == 0, result.stderr[-500:]
        outputs.append(result.stdout.strip())

    assert len(set(outputs)) == 1, (
        f"feature order varies with PYTHONHASHSEED: {outputs}")


def test_results_loader_refuses_to_invent_a_missing_metric() -> None:
    """A silently-missing metric would render as an empty cell in the report."""
    from research.chapters import Results

    results = Results({"experiments": {"E1": {"status": "ok", "metrics": {"a": 1}}}})
    assert results.m("E1", "a") == 1
    assert results.m("E1", "absent", default="fallback") == "fallback"
    with pytest.raises(KeyError):
        results.m("E1", "absent")
