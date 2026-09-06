"""The research layer: every experiment behind the report, run from one command.

    make research            # everything
    make research E=E1,E4    # selected experiments

The running system in `api/` demonstrates the framework. This package is what
*evaluates* it: each experiment writes a table to `research/results/`, every
headline number carries a confidence interval, and `research/figures/` is
regenerated from those results so a figure can never disagree with the number
it plots.

Nothing here reaches for the network, and nothing here depends on the API being
up except the two experiments that measure the live build — which say so, and
record `status: skipped` with a reason rather than failing the run.
"""
