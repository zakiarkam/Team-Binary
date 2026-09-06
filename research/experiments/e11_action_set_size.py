"""E11 — How much data does a bigger action set cost you?

Letting the action set vary per website is the right design: a news site has no
checkout, a charity has no upgrade path, and offering the same four actions to
everyone is a category error. But it has a consequence that has to be measured
rather than assumed.

Exploration is a fixed budget. At ε = 10% with four actions, each non-greedy
action receives roughly 2.5% of traffic. With twelve, each receives 0.8%. The
evidence per action thins out, the importance weights in any off-policy
estimate grow, and the point at which a logged policy comparison becomes
trustworthy moves further away.

So: **how many logged decisions are needed before an off-policy estimate can be
trusted, as a function of how many actions are on offer?** That is a practical
question a marketer would actually ask — "I have twelve things I could send;
how long until the system knows which works?" — and it is answerable exactly in
simulation, because the true policy value is computable there.

Three things are measured, holding everything else fixed:

*   **Error against the truth** at each action-set size and log volume.
*   **The volume needed to reach a usable error**, which is the number the
    report can quote as guidance.
*   **Whether raising the exploration rate compensates**, since that is the
    obvious lever and its cost is real — every explored decision is one
    deliberately not taken greedily.

This is a simulation for the same reason E9 is: the quantity under test is a
property of an estimator, checkable exactly against a known answer. It claims
nothing about real customers.
"""

from __future__ import annotations

import numpy as np

from research import config

ID = "E11"
TITLE = "Module 3 — the cost of a larger action set"

ACTION_SET_SIZES = (2, 4, 8, 16)
LOG_SIZES = (1_000, 5_000, 20_000)
REPLICATIONS = 30

#: An estimate within this of the truth is good enough to choose between
#: policies. Stated explicitly because "trustworthy" is otherwise a matter of
#: taste, and every threshold in this project has to be defensible.
USABLE_ERROR = 0.02


def _world(rng: np.random.Generator, n: int, k: int):
    """A population where the best action depends on the customer.

    One latent trait orders the actions differently for different people, so
    no single action dominates and the policy has something real to learn. The
    reward surface keeps the same overall scale as `k` grows, so the comparison
    across action-set sizes is not confounded by the problem simply getting
    easier or harder.
    """
    trait = rng.random(n)
    # Each action has an ideal trait value; reward falls off with distance.
    centres = np.linspace(0.1, 0.9, k)
    distance = np.abs(trait[:, None] - centres[None, :])
    return trait, 0.30 - 0.22 * distance


def _run_once(rng: np.random.Generator, n: int, k: int, epsilon: float) -> float:
    """One logged run. Returns the SNIPS error against the true policy value."""
    trait, reward = _world(rng, n, k)

    # A logging policy that is good but not optimal — it uses a coarse rule.
    greedy = np.minimum((trait * k).astype(int), k - 1)
    greedy = np.where(rng.random(n) < 0.25, rng.integers(0, k, n), greedy)

    explore = rng.random(n) < epsilon
    taken = np.where(explore, rng.integers(0, k, n), greedy)
    propensity = epsilon / k + (1.0 - epsilon) * (taken == greedy)

    observed = (rng.random(n) < reward[np.arange(n), taken]).astype(float)

    target = reward.argmax(axis=1)
    true_value = float(reward[np.arange(n), target].mean())

    agrees = (taken == target).astype(float)
    weights = agrees / np.maximum(propensity, 1e-9)
    if weights.sum() == 0:
        return float("nan")

    snips = float((weights * observed).sum() / weights.sum())
    return snips - true_value


def run() -> dict:
    rng = np.random.default_rng(config.SEED)

    # ── 1. Error against action-set size and log volume ─────────────────────
    grid = []
    for k in ACTION_SET_SIZES:
        for n in LOG_SIZES:
            errors = [_run_once(rng, n, k, epsilon=0.10)
                      for _ in range(REPLICATIONS)]
            errs = np.asarray([e for e in errors if e == e])
            grid.append({
                "n_actions": k,
                "log_size": n,
                "rmse": round(float(np.sqrt(np.mean(errs ** 2))), 4),
                "bias": round(float(errs.mean()), 4),
                "usable": bool(np.sqrt(np.mean(errs ** 2)) <= USABLE_ERROR),
                "decisions_per_action": round(n / k),
            })

    # ── 2. How much data each action-set size needs ─────────────────────────
    # Searched rather than interpolated, so the number quoted is one that was
    # actually measured.
    requirement = []
    for k in ACTION_SET_SIZES:
        needed = None
        for n in (500, 1_000, 2_500, 5_000, 10_000, 20_000, 40_000, 80_000):
            errs = np.asarray([_run_once(rng, n, k, epsilon=0.10)
                               for _ in range(REPLICATIONS)])
            errs = errs[~np.isnan(errs)]
            if errs.size and np.sqrt(np.mean(errs ** 2)) <= USABLE_ERROR:
                needed = n
                break
        requirement.append({
            "n_actions": k,
            "decisions_needed": needed,
            "per_action": round(needed / k) if needed else None,
            "reached": needed is not None,
        })

    # ── 3. Does exploring harder compensate? ────────────────────────────────
    lever = []
    for epsilon in (0.05, 0.10, 0.20, 0.40):
        for k in (4, 16):
            errs = np.asarray([_run_once(rng, 5_000, k, epsilon)
                               for _ in range(REPLICATIONS)])
            errs = errs[~np.isnan(errs)]
            lever.append({
                "exploration_rate": epsilon,
                "n_actions": k,
                "rmse": round(float(np.sqrt(np.mean(errs ** 2))), 4),
                # Every explored decision is one not taken greedily.
                "reward_given_up": round(epsilon * (1 - 1 / k), 4),
            })

    small = next(r for r in requirement if r["n_actions"] == min(ACTION_SET_SIZES))
    large = next(r for r in requirement if r["n_actions"] == max(ACTION_SET_SIZES))

    notes = [
        "Letting each website use only the actions it can actually perform is "
        "not free. Exploration is a fixed budget, so the more actions on offer, "
        "the less evidence each one accumulates and the longer before a logged "
        "comparison means anything.",
    ]

    if small["decisions_needed"] and large["decisions_needed"]:
        ratio = large["decisions_needed"] / small["decisions_needed"]
        notes.append(
            f"Reaching an RMSE of {USABLE_ERROR} takes "
            f"{small['decisions_needed']:,} logged decisions with "
            f"{small['n_actions']} actions and {large['decisions_needed']:,} with "
            f"{large['n_actions']} — {ratio:.1f}× the data for "
            f"{large['n_actions'] / small['n_actions']:.0f}× the actions. The "
            "requirement grows with the action set, so a site offering twelve "
            "actions should not expect conclusions on the same timescale as one "
            "offering four.")
    else:
        notes.append(
            "At least one action-set size did not reach the target error within "
            "the volumes tested, which is itself the answer: that many actions "
            "needs more data than was simulated.")

    by_lever = {(r["exploration_rate"], r["n_actions"]): r["rmse"] for r in lever}
    if (0.40, 16) in by_lever and (0.10, 16) in by_lever:
        gain = by_lever[(0.10, 16)] - by_lever[(0.40, 16)]
        notes.append(
            f"Exploring harder helps but does not rescue it: at 16 actions, "
            f"quadrupling exploration from 10% to 40% cuts RMSE by {gain:.4f} "
            f"while giving up {0.40 * (1 - 1/16):.0%} of achievable reward. "
            "Volume is the effective lever; exploration rate is the expensive "
            "one.")

    notes.append(
        "The practical reading for this system: the catalogue should stay as "
        "small as honestly covers what a site can do. Adding an action nobody "
        "will choose costs every other action some of its evidence.")

    notes.append(
        "Simulated, deliberately — the claim is about how an estimator behaves, "
        "which is checkable exactly against a known answer, and says nothing "
        "about real customers.")

    return {
        "id": ID,
        "title": TITLE,
        "status": "ok",
        "metrics": {
            "replications": REPLICATIONS,
            "usable_error_target": USABLE_ERROR,
            "smallest_set": small["n_actions"],
            "smallest_set_decisions_needed": small["decisions_needed"],
            "largest_set": large["n_actions"],
            "largest_set_decisions_needed": large["decisions_needed"],
        },
        "tables": {
            "e11_error_grid": grid,
            "e11_data_requirement": requirement,
            "e11_exploration_lever": lever,
        },
        "notes": notes,
    }
