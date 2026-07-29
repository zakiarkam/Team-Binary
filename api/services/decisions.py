"""Making next-best-action learnable instead of merely assertable.

The problem this solves
-----------------------
The system recommends one of four actions per customer. Whether those
recommendations are any good is currently unanswerable, and no dataset on the
internet can answer it, because the question is causal: *would this customer
have converted had they received a different action?* Nothing in the data says.
Every customer received one action, and no comparable customer received another.

Experiment E8 borrowed the Hillstrom dataset to demonstrate the method on real
randomised data, but its actions are mens/womens email — not this project's.
Borrowing a better dataset cannot fix that: the features differ, the actions
differ, and the result can never be validated on this audience.

The fix is not a dataset. It is to make the system generate the data itself.

How
---
Three pieces, and all three are necessary:

1.  **Log the decision, not the opinion.** `analytics_output` is overwritten on
    every run, so it holds what the system thinks *now*. `action_log` is
    append-only and records what it actually chose, when, and on what features.

2.  **Log the propensity.** The probability the chosen action had of being
    chosen. Without it, logged data reveals only what the running policy
    achieved. With it, an inverse-propensity estimator can answer what a
    *different* policy would have achieved on the very same customers — the
    counterfactual, recovered from observational logs.

3.  **Explore on purpose.** A deterministic policy has propensity 1 for the
    action it takes and 0 for every other, and dividing by zero is the formal
    statement of "you can never learn anything about the actions you never
    take". So a small share of decisions are made at random. That deliberate
    randomisation is the whole mechanism; everything else here is bookkeeping.

Then off-policy evaluation scores a candidate policy on logged data before it
is ever deployed, which is the point: a new policy can be compared with the
running one without experimenting on customers.

Honesty
-------
The estimators are unbiased *only* where propensities are correct and every
action had some chance of being taken. Both hold by construction here, because
this module is what assigns the actions. They would not hold for the imported
research audience's historical behaviour, which no policy of ours produced —
so nothing here is applied retrospectively to it.
"""

from __future__ import annotations

import json
import logging
import math
import random
from typing import Any, Iterable, Sequence

from api import db

log = logging.getLogger("mos.decisions")

#: The action set. Fixed and ordered — the propensity of a uniform random draw
#: is 1/len(ACTIONS), so adding an action changes the arithmetic and must be a
#: deliberate act rather than a silent edit.
ACTIONS = (
    "send_premium_offer",
    "send_personalized_offer",
    "send_reactivation_campaign",
    "send_general_reminder",
)

#: Share of decisions made at random. 10% is the usual starting point: large
#: enough that every action accumulates evidence in reasonable time, small
#: enough that the cost of deliberately acting sub-optimally stays modest.
#: Lower it once the policy is trusted; it can never be zero without the system
#: going blind again.
EXPLORATION_RATE = 0.10

#: How long after a decision a conversion still counts as its consequence.
REWARD_WINDOW_DAYS = 14

#: What a decision is worth. Conversion is the outcome the business wants; a
#: click is partial credit for a message that worked well enough to be opened
#: and followed. Stated here rather than buried, because changing it changes
#: every policy comparison downstream.
REWARD_VALUES = {"convert": 1.0, "click": 0.25}


def epsilon_greedy(greedy_action: str, rng: random.Random,
                   epsilon: float = EXPLORATION_RATE,
                   candidates: Sequence[str] | None = None
                   ) -> tuple[str, str, float]:
    """Choose an action from what is available, and report how likely that was.

    Returns `(action, policy, propensity)` where

        P(a | x) = ε/|A(x)| + (1 − ε)·1[a = greedy(x)]

    The denominator is the number of actions available *to this customer of
    this site* — not a global constant. A shop with a basket, a subscription
    product and a charity offer different things, and within one site a lapsed
    buyer and a first-time reader qualify for different subsets. Dividing by a
    fixed K when the real set varies is a silent bias in every off-policy
    estimate computed afterwards, so |A(x)| travels with the decision.

    This is the "varying action set" case in the contextual-bandit literature.
    Nothing about it is exotic; it just has to be got right once.
    """
    pool = tuple(candidates) if candidates else ACTIONS
    if not pool:                       # never — available() guarantees non-empty
        pool = (ACTIONS[-1],)

    k = len(pool)
    greedy = greedy_action if greedy_action in pool else pool[-1]

    if rng.random() < epsilon:
        action = rng.choice(pool)
        policy = "explore"
    else:
        action = greedy
        policy = "exploit"

    propensity = epsilon / k + (1.0 - epsilon) * (1.0 if action == greedy else 0.0)
    return action, policy, propensity


def log_decisions(site_id: int, decisions: Sequence[dict],
                  epsilon: float = EXPLORATION_RATE,
                  seed: int | None = None) -> dict[str, Any]:
    """Record one decision per customer, applying exploration as it goes.

    `decisions` carries `visitor_id`, the `greedy` action the ranking chose, and
    a `context` dict of the features it was chosen on. Returns what was written
    and the resulting action mix.
    """
    if not decisions:
        return {"logged": 0, "explored": 0, "mix": {}}

    rng = random.Random(seed)
    rows, mix, explored, set_sizes = [], {}, 0, []

    for decision in decisions:
        # Which actions this site can perform, narrowed to those this customer
        # qualifies for. Falls back to the fixed set when a caller supplies no
        # candidates, so older call sites keep working.
        candidates = decision.get("candidates") or list(ACTIONS)

        action, policy, propensity = epsilon_greedy(
            str(decision.get("greedy") or candidates[-1]), rng, epsilon,
            candidates=candidates)
        explored += policy == "explore"
        set_sizes.append(len(candidates))
        mix[action] = mix.get(action, 0) + 1

        # The candidate set is stored with the decision, not just its size. An
        # estimator reading this log months later cannot otherwise reconstruct
        # what was on offer, and without that the propensity is unverifiable.
        context = dict(decision.get("context") or {})
        context["candidates"] = candidates

        rows.append({
            "site_id": site_id,
            "visitor_id": int(decision["visitor_id"]),
            "action": action,
            "policy": policy,
            "propensity": round(propensity, 6),
            "context": json.dumps(context, default=str),
        })

    db.execute_many(
        """
        INSERT INTO action_log (site_id, visitor_id, action, policy, propensity,
                                context, source)
        VALUES (:site_id, :visitor_id, :action, :policy, :propensity,
                CAST(:context AS jsonb),
                -- Derived from the visitor, exactly as everywhere else.
                (SELECT source FROM visitors WHERE id = :visitor_id))
        """,
        rows,
    )
    log.info("site %s: logged %s decisions (%s explored)", site_id, len(rows), explored)
    return {
        "logged": len(rows), "explored": explored,
        "exploration_rate": round(explored / len(rows), 4),
        "mix": mix,
        # How many actions were on offer, on average. With a larger candidate
        # set each action receives less exploration, so this is the number that
        # says how long the log must grow before it can support a conclusion —
        # see experiment E11.
        "mean_candidates": round(sum(set_sizes) / len(set_sizes), 2),
        "min_candidates": min(set_sizes),
        "max_candidates": max(set_sizes),
    }


def attach_rewards(site_id: int, window_days: int = REWARD_WINDOW_DAYS) -> dict[str, Any]:
    """Join what happened back onto the decision that preceded it.

    Only events *after* the decision count. A conversion that already happened
    cannot have been caused by an action taken afterwards, and letting one count
    would manufacture evidence for whatever the policy happened to do.

    And only events belonging to a campaign this system planned. Ordering by
    timestamp alone is not enough: the importer reconstructs each customer's
    prior email history across a 90-day window from their first visit, so a
    good deal of it carries a timestamp later than now. Those rows passed an
    "occurred after the decision" test while being reconstructions of a
    different company's campaign — they cannot be consequences of a
    recommendation made today. Requiring `campaign_id IS NOT NULL` restricts the
    reward to events downstream of an action this system actually took, which is
    the only thing a policy can be credited or blamed for.

    Decisions older than the window with nothing attached are settled at reward
    0 rather than left NULL: "nothing happened" is an outcome, and treating it
    as missing would quietly bias every estimate towards the actions that did
    provoke a response.
    """
    updated = db.fetch_all(
        f"""
        WITH outcome AS (
            SELECT l.id,
                   max(CASE i.event_type WHEN 'convert' THEN {REWARD_VALUES['convert']}
                                         WHEN 'click'   THEN {REWARD_VALUES['click']}
                                         ELSE 0 END)                    AS reward,
                   (array_agg(i.event_type ORDER BY
                        CASE i.event_type WHEN 'convert' THEN 0 ELSE 1 END))[1] AS kind,
                   min(i.occurred_at)                                   AS first_at
            FROM action_log l
            JOIN interactions i
              ON i.visitor_id = l.visitor_id
             AND i.occurred_at >  l.decided_at
             AND i.occurred_at <= l.decided_at + make_interval(days => :w)
             AND i.event_type IN ('click', 'convert')
             -- Downstream of an action this system took, not reconstructed
             -- history that happens to carry a later timestamp.
             AND i.campaign_id IS NOT NULL
            WHERE l.site_id = :s AND l.reward IS NULL
            GROUP BY l.id
        )
        UPDATE action_log l
        SET reward = o.reward, reward_kind = o.kind, rewarded_at = o.first_at
        FROM outcome o
        WHERE l.id = o.id
        RETURNING l.id
        """,
        s=site_id, w=window_days,
    )

    settled = db.fetch_all(
        """
        UPDATE action_log
        SET reward = 0, reward_kind = 'none', rewarded_at = now()
        WHERE site_id = :s AND reward IS NULL
          AND decided_at < now() - make_interval(days => :w)
        RETURNING id
        """,
        s=site_id, w=window_days,
    )

    return {"rewarded": len(updated), "settled_at_zero": len(settled)}


# ── Off-policy evaluation ────────────────────────────────────────────────────
def _logged(site_id: int) -> list[dict]:
    return db.fetch_all(
        """
        SELECT visitor_id, action, policy, propensity::float8 AS propensity,
               reward::float8 AS reward, context, source
        FROM action_log
        WHERE site_id = :s AND reward IS NOT NULL
        ORDER BY decided_at
        """,
        s=site_id,
    )


def evaluate_policy(site_id: int, target: dict[int, str] | None = None,
                    rows: list[dict] | None = None) -> dict[str, Any]:
    """What would a different policy have earned, on the customers we already have?

    `target` maps visitor_id → the action the candidate policy would take. With
    none given, the logged policy is evaluated against itself, which is a useful
    sanity check: the estimate should land on the observed average reward.

    Three estimators, because they fail differently and agreement between them
    is the only real evidence:

    *   **IPS** — unbiased, but its variance explodes when the candidate policy
        favours actions the logging policy rarely took (a small propensity in
        the denominator).
    *   **SNIPS** — self-normalised. Slightly biased, far more stable, and
        usually the one to quote.
    *   **Doubly robust** — combines a reward model with the IPS correction. It
        is right if *either* the reward model or the propensities are right,
        which is a genuinely weaker assumption than either alone requires.
    """
    rows = rows if rows is not None else _logged(site_id)
    if not rows:
        return {"n": 0, "note": ("No decision has both been logged and had its "
                                 "outcome observed yet. The mechanism records "
                                 "them; it cannot invent them.")}

    observed = sum(r["reward"] for r in rows) / len(rows)

    # A per-action mean reward, which is the simplest honest reward model. It is
    # what makes the doubly-robust estimator robust: even where the propensity
    # weights are unreliable, the direct term still carries a signal.
    totals: dict[str, list[float]] = {}
    for r in rows:
        totals.setdefault(r["action"], []).append(r["reward"])
    model = {a: sum(v) / len(v) for a, v in totals.items()}
    fallback = observed

    ips_terms, snips_weights, dr_terms, matched = [], [], [], 0

    for r in rows:
        chosen = r["action"]
        wanted = (target or {}).get(int(r["visitor_id"]), chosen)
        agrees = 1.0 if chosen == wanted else 0.0
        matched += int(agrees)

        # Guarded: the schema forbids a zero propensity, but a corrupt row must
        # not silently become an infinite weight.
        p = max(float(r["propensity"]), 1e-6)
        weight = agrees / p

        ips_terms.append(weight * r["reward"])
        snips_weights.append(weight)

        direct = model.get(wanted, fallback)
        dr_terms.append(direct + weight * (r["reward"] - model.get(chosen, fallback)))

    n = len(rows)
    ips = sum(ips_terms) / n
    snips = (sum(ips_terms) / sum(snips_weights)) if sum(snips_weights) > 0 else float("nan")
    doubly_robust = sum(dr_terms) / n

    # Effective sample size: how many decisions the importance weights are
    # really resting on. A handful of huge weights can dominate a nominally
    # large log, and the number silently stops meaning anything.
    total_w = sum(snips_weights)
    ess = (total_w ** 2 / sum(w * w for w in snips_weights)) if total_w > 0 else 0.0

    notes = []
    if ess < 0.1 * n:
        notes.append(
            f"Effective sample size is {ess:.0f} of {n} logged decisions — the "
            "estimate rests on a small, heavily-weighted subset. Treat the "
            "self-normalised and doubly-robust numbers as indicative and widen "
            "exploration before acting on them.")
    if matched == 0:
        notes.append("The candidate policy agrees with the logged policy on no "
                     "decision at all, so there is nothing to learn from.")

    explored = sum(1 for r in rows if r["policy"] == "explore")
    if explored == 0:
        notes.append(
            "No exploration in this log. Every propensity is 1 for the action "
            "taken, so a candidate policy can only be scored where it happens "
            "to agree with the logged one — which is exactly the blind spot "
            "exploration exists to remove.")

    return {
        "n": n,
        "observed_reward": round(observed, 5),
        "ips": round(ips, 5),
        "snips": round(snips, 5),
        "doubly_robust": round(doubly_robust, 5),
        "effective_sample_size": round(ess, 1),
        "agreement_with_logged": round(matched / n, 4),
        "explored_share": round(explored / n, 4),
        "reward_model": {a: round(v, 5) for a, v in sorted(model.items())},
        "notes": notes,
    }


def summary(site_id: int) -> dict[str, Any]:
    """What the log currently holds — for the dashboard and the research page."""
    totals = db.fetch_one(
        """
        SELECT count(*)                                        AS decisions,
               count(*) FILTER (WHERE policy = 'explore')       AS explored,
               count(*) FILTER (WHERE reward IS NOT NULL)       AS with_outcome,
               count(DISTINCT visitor_id)                       AS customers,
               min(decided_at)                                  AS first_decision,
               max(decided_at)                                  AS last_decision
        FROM action_log WHERE site_id = :s
        """, s=site_id) or {}

    by_action = db.fetch_all(
        """
        SELECT action,
               count(*)                                   AS decisions,
               count(*) FILTER (WHERE policy = 'explore') AS explored,
               count(*) FILTER (WHERE reward IS NOT NULL) AS with_outcome,
               round(avg(reward) FILTER (WHERE reward IS NOT NULL), 4)::float8
                                                          AS mean_reward
        FROM action_log WHERE site_id = :s
        GROUP BY action ORDER BY decisions DESC
        """, s=site_id)

    decisions = totals.get("decisions") or 0
    return {
        "totals": totals,
        "by_action": by_action,
        "exploration_rate": round((totals.get("explored") or 0) / decisions, 4)
                            if decisions else 0.0,
        "note": (
            "Append-only. Every row is a decision the system actually took, the "
            "probability it had of taking it, and what followed — which is what "
            "makes a better policy learnable from this audience rather than "
            "borrowed from another one."
        ),
    }
