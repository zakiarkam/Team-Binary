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
    import os
    import subprocess
    import sys

    from research import config as research_config

    script = (
        "import engagement;"
        "cols = sorted(c for c in engagement.LEAKY_COLUMNS"
        "              if c != 'engagement_rate');"
        "print(','.join(cols))"
    )

    # engagement.py lives in Module 4's folder; the child interpreter needs
    # both the repo root and that folder on its path.
    pythonpath = os.pathsep.join([
        str(research_config.ROOT),
        str(research_config.ROOT / "modules" / "m4_content"),
    ])

    outputs = []
    for seed in ("0", "1", "12345"):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True,
            env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin",
                 "PYTHONPATH": pythonpath},
        )
        assert result.returncode == 0, result.stderr[-500:]
        outputs.append(result.stdout.strip())

    assert len(set(outputs)) == 1, (
        f"feature order varies with PYTHONHASHSEED: {outputs}")


# ── Uplift evaluation ────────────────────────────────────────────────────────

def _uplift_population(n: int = 4_000, seed: int = 0):
    """A randomised trial where only the first half of the ranking is persuadable.

    Everyone else responds at the same rate whether treated or not, so a perfect
    targeting rule puts the persuadable half first and a bad one puts them last.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    treated = rng.integers(0, 2, n)
    persuadable = np.zeros(n, dtype=bool)
    persuadable[: n // 2] = True

    base = rng.random(n) < 0.10
    lifted = rng.random(n) < 0.40
    outcome = np.where(persuadable & (treated == 1), lifted, base).astype(int)
    return treated, outcome, persuadable


def test_qini_rewards_a_ranking_that_finds_persuadable_customers_first() -> None:
    import numpy as np

    from research.experiments.e8_uplift import qini_coefficient, qini_curve

    treated, outcome, persuadable = _uplift_population()

    perfect = persuadable.astype(float)          # persuadable ranked first
    inverted = 1.0 - perfect                     # persuadable ranked last
    random_scores = np.random.default_rng(1).random(len(treated))

    scored = {}
    for name, s in (("perfect", perfect), ("inverted", inverted),
                    ("random", random_scores)):
        x, gain = qini_curve(s, treated, outcome)
        scored[name] = qini_coefficient(x, gain)

    assert scored["perfect"] > scored["random"] > scored["inverted"], scored
    assert scored["perfect"] > 0 and scored["inverted"] < 0


def test_qini_of_random_targeting_is_about_zero() -> None:
    """Random targeting is the definition of the baseline the coefficient is
    measured against, so it must sit near zero rather than merely 'low'."""
    import numpy as np

    from research.experiments.e8_uplift import qini_coefficient, qini_curve

    treated, outcome, _ = _uplift_population()
    scores = np.random.default_rng(2).random(len(treated))

    x, gain = qini_curve(scores, treated, outcome)
    coefficient = qini_coefficient(x, gain)

    # Scaled by the total incremental responders, so the tolerance means
    # "within 15% of the whole effect" rather than an arbitrary absolute number.
    assert abs(coefficient) < 0.15 * abs(gain[-1])


def test_incremental_at_budget_recovers_a_known_treatment_effect() -> None:
    """Targeting only persuadable customers must recover their true uplift.

    Built with a 30-point effect among the persuadable half, so a policy that
    selects exactly them should measure roughly 300 per 1,000 — the check that
    the estimator is not quietly biased.
    """
    from research.experiments.e8_uplift import incremental_at_budget

    treated, outcome, persuadable = _uplift_population(n=20_000, seed=5)
    result = incremental_at_budget(persuadable.astype(float), treated, outcome,
                                   budget=0.5)

    assert 250 <= result["uplift_per_1000"] <= 350, result


def test_results_loader_refuses_to_invent_a_missing_metric() -> None:
    """A silently-missing metric would render as an empty cell in the report."""
    from research.chapters import Results

    results = Results({"experiments": {"E1": {"status": "ok", "metrics": {"a": 1}}}})
    assert results.m("E1", "a") == 1
    assert results.m("E1", "absent", default="fallback") == "fallback"
    with pytest.raises(KeyError):
        results.m("E1", "absent")


# ── Capability detection ─────────────────────────────────────────────────────

def test_url_matching_uses_whole_segments_not_substrings() -> None:
    """Regression for the two faults E10 found on real websites.

    Substring matching read `/categories/product-strategy` as a product page and
    a `support.` customer-service subdomain as a donation page. Both invented a
    capability the site did not have — the expensive direction of error, because
    it makes the system recommend something the client cannot do.
    """
    import crawler

    magazine = """<html><body><h1>Articles</h1>
      <a href="/categories/product-strategy">Product strategy</a>
      <a href="/articles/latest">Latest</a></body></html>"""
    assert crawler.extract_page_data(magazine)["capabilities"]["commerce"] is False

    retailer_support = """<html><body><h1>Help</h1>
      <a href="https://support.example.com/article/delivery">Delivery info</a>
      </body></html>"""
    assert crawler.extract_page_data(
        retailer_support)["capabilities"]["donation"] is False

    # …while genuine evidence still registers, including in a subdomain.
    charity_shop = """<html><body>
      <a href="https://shop.example.org">Shop</a>
      <a href="/donate">Donate</a></body></html>"""
    caps = crawler.extract_page_data(charity_shop)["capabilities"]
    assert caps["commerce"] is True and caps["donation"] is True


def test_capabilities_are_independent_flags_not_a_site_type() -> None:
    """What the E10 disagreements actually taught.

    A charity that sells merchandise has both donation and commerce. Treating
    capability as a category would have forced a choice and been wrong.
    """
    import crawler

    html = """<html><body>
      <a href="/donate">Donate now</a>
      <a href="/shop">Shop</a>
      <a href="/newsletter">Newsletter</a></body></html>"""
    caps = crawler.extract_page_data(html)["capabilities"]
    assert caps["donation"] and caps["commerce"] and caps["lead_capture"]


# ── The dashboard's per-module research tabs ─────────────────────────────────
# api/services/research_experiments.py reads results.json and groups it by
# module so each module page can show what that module was measured to do.
# These tests hold the grouping and the figure allowlist, not the numbers.


def _client():
    from fastapi.testclient import TestClient

    from api.main import app

    return TestClient(app)


def test_every_experiment_lands_on_exactly_one_module_page() -> None:
    """Grouping is parsed from the experiment's own title ("Module 4 — …").

    An experiment whose title stops matching that shape would vanish from the
    dashboard without failing anything — nothing else would notice.
    """
    from api.services import research_experiments as service

    results = service._load()
    if results is None:
        pytest.skip("experiments have not been run — no results.json")

    seen: dict[str, int] = {}
    for module in service.MODULE_NAMES:
        for exp in service.module_results(module)["experiments"]:
            assert exp["id"] not in seen, f"{exp['id']} claimed by two modules"
            seen[exp["id"]] = module

    assert set(seen) == set(results["experiments"]), (
        f"experiment(s) on no module page: "
        f"{sorted(set(results['experiments']) - set(seen))}")


def test_figures_are_matched_to_their_own_experiment() -> None:
    """E1's `fig_e1_` prefix must not swallow E10's and E11's figures."""
    from api.services import research_experiments as service

    if service._load() is None:
        pytest.skip("experiments have not been run — no results.json")

    for module in service.MODULE_NAMES:
        for exp in service.module_results(module)["experiments"]:
            for name in exp["figures"]:
                assert name.startswith(f"fig_{exp['id'].lower()}_"), (
                    f"{name} was attached to {exp['id']}")


def test_module_results_endpoint_serves_one_module() -> None:
    response = _client().get("/research/modules/4/results")
    assert response.status_code == 200

    body = response.json()
    assert body["module"] == 4
    if not body["available"]:
        pytest.skip("experiments have not been run — no results.json")

    assert [e["id"] for e in body["experiments"]] == ["E6", "E7", "E10"]
    # The caveats travel with the numbers: several of these results went
    # against the hypothesis, and a tab without them would misreport them.
    assert all(e["notes"] for e in body["experiments"])


def test_unknown_module_is_rejected() -> None:
    assert _client().get("/research/modules/9/results").status_code == 404


def test_figure_route_serves_only_figures_the_run_produced() -> None:
    from api.services import research_experiments as service

    client = _client()
    names = service._figure_names()
    if not names:
        pytest.skip("no figures on disk — run `make research`")

    assert client.get(f"/research/figures/{sorted(names)[0]}").status_code == 200
    assert client.get("/research/figures/not_a_figure.png").status_code == 404
    # The route takes a filename, so a path must never resolve out of the
    # figures directory and read something else.
    assert client.get("/research/figures/../results/results.json").status_code == 404


def test_long_tables_report_their_true_length() -> None:
    """E8's qini curves are 400 rows. Cutting them is fine; implying the tab
    shows all of them is not."""
    from api.services import research_experiments as service

    if service._load() is None:
        pytest.skip("experiments have not been run — no results.json")

    for module in service.MODULE_NAMES:
        for exp in service.module_results(module)["experiments"]:
            for table in exp["tables"]:
                assert len(table["rows"]) <= service.MAX_TABLE_ROWS
                assert table["truncated"] == (
                    table["row_count"] > service.MAX_TABLE_ROWS)
                assert table["row_count"] >= len(table["rows"])
