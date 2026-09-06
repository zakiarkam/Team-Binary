"""E3 — Which automation policy wins, by how much, and at what cost?

Module 2 compares three policies:

    fixed    the whole sequence is committed up front            (1 rule)
    trigger  only the opener is scheduled; the rest reacts       (4 rules)
    hybrid   a fixed backbone adjusted by segment and score      (9 rules)

Three things this experiment insists on that a single run cannot give:

1.  **Many seeds, paired.** One simulation cannot separate "hybrid is better"
    from "hybrid got a good roll". Thirty seeds are run, and every seed puts the
    *same* 8,000 users through all three policies, so the comparison is paired
    and the between-seed variance cancels.

2.  **A volume-controlled metric.** User-level conversion rate rises simply by
    sending more messages, so `fixed` — which always sends its full sequence —
    would win on it by construction. Conversions per 1,000 sends is the metric
    that answers "is this policy better *per message*", and it is the one the
    verdict rests on.

3.  **The cost side.** Operational complexity is counted as the number of
    distinct decision rules each policy needs. A policy that wins by two points
    for nine times the rules is a different recommendation from one that wins by
    two points for free, and the report should be able to say which it is.

A sparsity sweep follows, because it tests the mechanism rather than the
outcome: `trigger` reacts to opens and clicks, so suppressing that signal should
hurt it specifically and leave `fixed` untouched. If suppressing the signal
changed nothing, the policies would not be doing what they claim to.

Finally the live build is read from the database, where the same three policies
ran against the imported research audience — measured, not simulated.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from research import config, module_loader
from research.stats import describe_effect, paired_difference

ID = "E3"
TITLE = "Module 2 — fixed vs trigger vs hybrid, over 30 paired seeds"

MAX_MESSAGES = 4
SPARSITY_LEVELS = [0.0, 0.3, 0.6, 0.9]
SPARSITY_SEEDS = 10


def _load_m2():
    """Import Module 2's simulator and its three policies.

    Goes through module_loader because Module 3 also ships a package called
    `src`; see that module for why the cache has to be cleared first.
    """
    simulator = module_loader.load(config.M2_DIR, "simulator")
    return simulator.simulate_campaign, {
        "fixed": module_loader.load(config.M2_DIR, "strategies.fixed").fixed_strategy,
        "trigger": module_loader.load(config.M2_DIR, "strategies.trigger").trigger_strategy,
        "hybrid": module_loader.load(config.M2_DIR, "strategies.hybrid").hybrid_strategy,
    }


def _metrics(events: pd.DataFrame) -> dict:
    """Outcome of one simulated campaign."""
    sends = len(events)
    converters = events.groupby("user_id")["converted"].any().sum()
    return {
        "messages_sent": int(sends),
        "users": int(events["user_id"].nunique()),
        "open_rate": float(events["opened"].mean()),
        "ctr": float(events["clicked"].mean()),
        "conversions": int(converters),
        "conversions_per_1000_sends": float(converters / sends * 1000) if sends else 0.0,
        "messages_per_user": float(sends / events["user_id"].nunique()),
    }


def _live_comparison() -> tuple[list[dict], str | None]:
    """The same three policies as they ran against the imported audience."""
    try:
        from api import db
        from api.services import campaigns as campaign_svc
    except Exception as exc:                                   # pragma: no cover
        return [], f"API package unavailable ({type(exc).__name__})"

    try:
        site = db.fetch_one(
            "SELECT id FROM sites WHERE name = 'Innov8Smart' ORDER BY id DESC LIMIT 1")
        if site is None:
            return [], "no Innov8Smart site in the database — run `make demo` first"
        rows = [c for c in campaign_svc.compare_strategies(int(site["id"]))
                # Action-Plan campaigns share the strategy names but were never
                # delivered; including them would add empty rows to the table.
                if str(c.get("name", "")).startswith("Launch sequence")]
    except Exception as exc:
        return [], f"database not reachable ({type(exc).__name__})"

    if not rows:
        return [], "no strategy-comparison campaigns found — run `make demo` first"

    return [{
        "strategy": r["strategy"],
        "recipients": r["recipients"],
        "sent": r["sent"],
        "opens": r["opens"],
        "clicks": r["clicks"],
        "conversions": r["conversions"],
        "click_through_rate": r["click_through_rate"],
        "conversions_per_1000_sends": r["conversions_per_1000_sends"],
        "operational_complexity": r["operational_complexity"],
        "data_basis": r["data_basis"],
    } for r in rows], None


def run() -> dict:
    if not config.M2_USERS.exists():
        return {"id": ID, "title": TITLE, "status": "skipped",
                "reason": f"Module 2 user table not found at {config.M2_USERS}"}

    simulate_campaign, strategies = _load_m2()
    users = pd.read_csv(config.M2_USERS)

    complexity = {"fixed": 1, "trigger": 4, "hybrid": 9}

    # ── Multi-seed paired comparison ────────────────────────────────────────
    per_seed: list[dict] = []
    for seed in range(config.SEED, config.SEED + config.N_SEEDS):
        for name, fn in strategies.items():
            events = simulate_campaign(users, fn, max_messages_per_user=MAX_MESSAGES,
                                       seed=seed)
            per_seed.append({"seed": seed, "strategy": name, **_metrics(events)})

    seeds_df = pd.DataFrame(per_seed)

    summary = []
    for name in strategies:
        sub = seeds_df[seeds_df["strategy"] == name]
        eff = sub["conversions_per_1000_sends"]
        summary.append({
            "strategy": name,
            "seeds": int(len(sub)),
            "conversions_per_1000_sends": round(float(eff.mean()), 2),
            "sd": round(float(eff.std(ddof=1)), 2),
            "ci_low": round(float(np.quantile(eff, 0.025)), 2),
            "ci_high": round(float(np.quantile(eff, 0.975)), 2),
            "open_rate": round(float(sub["open_rate"].mean()), 4),
            "ctr": round(float(sub["ctr"].mean()), 4),
            "messages_per_user": round(float(sub["messages_per_user"].mean()), 2),
            "operational_complexity": complexity[name],
        })

    # ── Head-to-head, paired by seed ────────────────────────────────────────
    pivot = seeds_df.pivot(index="seed", columns="strategy",
                           values="conversions_per_1000_sends")
    contests = []
    for left, right in [("hybrid", "fixed"), ("hybrid", "trigger"), ("trigger", "fixed")]:
        test = paired_difference(pivot[left].to_numpy(), pivot[right].to_numpy())
        contests.append({
            "comparison": f"{left} − {right}",
            "mean_difference": round(test["mean_difference"], 3),
            "ci_low": round(test["ci_low"], 3),
            "ci_high": round(test["ci_high"], 3),
            "wilcoxon_p": test["wilcoxon_p"],
            "cliffs_delta": round(test["cliffs_delta"], 3),
            "effect_size": describe_effect(test["cliffs_delta"]),
            "significant": test["significant"],
            "extra_rules": complexity[left] - complexity[right],
        })

    # ── Sparsity: does the trigger policy fail where its signal fails? ───────
    sparsity_rows = []
    for level in SPARSITY_LEVELS:
        for seed in range(config.SEED, config.SEED + SPARSITY_SEEDS):
            for name, fn in strategies.items():
                events = simulate_campaign(users, fn, max_messages_per_user=MAX_MESSAGES,
                                           seed=seed, signal_sparsity=level)
                sparsity_rows.append({
                    "signal_sparsity": level, "seed": seed, "strategy": name,
                    **_metrics(events)})

    sparsity_df = pd.DataFrame(sparsity_rows)
    sparsity_summary = (sparsity_df
                        .groupby(["signal_sparsity", "strategy"])
                        ["conversions_per_1000_sends"]
                        .agg(["mean", "std"]).round(2).reset_index()
                        .rename(columns={"mean": "conversions_per_1000_sends",
                                         "std": "sd"})
                        .to_dict("records"))

    # ── The live build ──────────────────────────────────────────────────────
    live_rows, live_reason = _live_comparison()

    best = max(summary, key=lambda s: s["conversions_per_1000_sends"])
    cheapest = min(summary, key=lambda s: s["operational_complexity"])
    gap = best["conversions_per_1000_sends"] - cheapest["conversions_per_1000_sends"]

    notes = [
        "Every seed puts the same 8,000 users through all three policies, so the "
        "comparison is paired and the tests are paired accordingly.",
        "Conversions per 1,000 sends is the metric to read. User-level conversion "
        "rate rises with message volume, which would hand the win to `fixed` for "
        "sending more rather than for sending better.",
        "Simulated response. Module 2's simulator draws each user's behaviour "
        "from segment-level propensities calibrated against the dataset's own "
        "conversion rates; the policies are real code, the reactions are not "
        "observed behaviour.",
    ]
    if gap > 0:
        notes.append(
            f"{best['strategy']} leads {cheapest['strategy']} by {gap:.1f} "
            f"conversions per 1,000 sends for "
            f"{best['operational_complexity'] - cheapest['operational_complexity']} "
            "extra decision rules — the trade the report has to argue.")
    if live_reason:
        notes.append(f"Live comparison unavailable: {live_reason}")
    elif live_rows:
        # When the simulation and the live build rank the policies differently,
        # say so. Two runs disagreeing is a result about how much the ranking
        # depends on the response model — burying it would be the one genuinely
        # dishonest option.
        live_best = max(live_rows, key=lambda r: r["conversions_per_1000_sends"])
        if live_best["strategy"] != best["strategy"]:
            notes.append(
                f"The simulation and the live build disagree: {best['strategy']} "
                f"wins in simulation, {live_best['strategy']} wins on the imported "
                "audience. Both are volume-controlled, so the difference is in the "
                "response model — the simulator's segment propensities against "
                "per-customer rates drawn from the dataset's own email history. "
                "Neither is an observation of real people reacting, and the "
                "ranking is evidently not robust to how their reactions are "
                "modelled. That instability is the finding, and it belongs in the "
                "report rather than a single number picked from whichever run "
                "supports the preferred conclusion.")

    # Message volume explains a great deal of the efficiency metric, so it gets
    # stated next to it rather than left for a reader to infer.
    volumes = {s["strategy"]: s["messages_per_user"] for s in summary}
    notes.append(
        "Messages per user differ sharply ("
        + ", ".join(f"{k} {v:.2f}" for k, v in volumes.items())
        + "). A policy that stops early is rewarded by a per-send metric and "
        "penalised by a per-user one; both are reported so the choice of metric "
        "is visible rather than decisive.")

    return {
        "id": ID,
        "title": TITLE,
        "status": "ok",
        "metrics": {
            "n_seeds": config.N_SEEDS,
            "n_users": int(len(users)),
            "best_policy": best["strategy"],
            "best_conversions_per_1000": best["conversions_per_1000_sends"],
            "simplest_policy": cheapest["strategy"],
            "simplest_conversions_per_1000": cheapest["conversions_per_1000_sends"],
            "efficiency_gap": round(gap, 2),
            "hybrid_beats_fixed": next(
                c["significant"] for c in contests if c["comparison"] == "hybrid − fixed"),
            "live_measured": bool(live_rows),
        },
        "tables": {
            "e3_policy_summary": summary,
            "e3_policy_contests": contests,
            "e3_per_seed": seeds_df.round(4).to_dict("records"),
            "e3_sparsity": sparsity_summary,
            **({"e3_live_measured": live_rows} if live_rows else {}),
        },
        "notes": notes,
    }
