"""What a site can do, and what a customer is eligible for.

The problem with a fixed action set
-----------------------------------
The recommender used four actions for every client, regardless of what the
client's website could actually perform. A news site has no checkout, so
"send a premium offer" is not a recommendation there — it is a category error.
A charity has no upgrade path. A subscription product has no basket to abandon.

So the action set is not a constant. It is the intersection of two things:

    what the SITE can do        — detected from its own pages (commerce,
                                  subscription, lead capture, donation, content)
    what the CUSTOMER qualifies  — you cannot send a replenishment reminder to
    for                           someone who has never bought, or a trial
                                  extension to someone with no trial

Both are computed per decision, so a customer of a shop and a reader of a blog
receive genuinely different candidate sets rather than the same four labels with
different wording.

Why this is not a machine-learning problem
------------------------------------------
It is tempting to train a classifier "website → action set". There is no dataset
of labelled websites-to-marketing-actions, so the labels would have to be
synthesised from a rule — and the model would then learn that rule back. This
project has already found two defects of exactly that shape (a Random Forest
given its own target as a feature; a recommender trained on a label built from
the segment it also takes as input). A third would not be a contribution.

What a site can do is *evidence on the page*, so it is detected. Which of the
available actions is best is genuinely unknown, so that is learned — by the
decision log and the off-policy machinery in `decisions.py`.

Consequences for the mathematics
--------------------------------
A varying action set changes the propensity. Exploration must be uniform over
the actions actually available to *that* customer at *that* moment:

    P(a | x) = ε/|A(x)| + (1 − ε)·1[a = greedy(x)]

and |A(x)| must be recorded with the decision, because an estimator run months
later cannot reconstruct which actions were on offer. This is the "varying
action set" case in the contextual-bandit literature, and getting the
denominator wrong is a silent bias, not an error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

#: The capabilities a website can have. Detected from its pages, never assumed.
CAPABILITIES = ("commerce", "subscription", "lead_capture", "donation", "content")


@dataclass(frozen=True)
class Action:
    """One thing the system can recommend.

    `requires` is the site side: at least one of these capabilities must be
    present, or the action is not offerable at all. `eligible` is the customer
    side: given the site can do it, does this particular person qualify?
    """

    key: str
    label: str
    #: Any one of these capabilities makes the action possible for a site.
    requires: tuple[str, ...]
    #: Which campaign goals this action serves — used to order, never to filter.
    goals: tuple[str, ...] = ()
    #: Per-customer predicate. Default: everyone the site can reach.
    eligible: Callable[[dict], bool] = field(default=lambda ctx: True)
    #: Roughly how strong an intervention this is; used only for presentation.
    intensity: int = 2


def _has(ctx: dict, key: str, default: float = 0.0) -> float:
    value = ctx.get(key, default)
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return default


#: The catalogue. Deliberately larger than any one site will use — a site is
#: expected to support a handful of these, not all of them. Adding an action
#: here is the supported way to extend the system; nothing downstream hard-codes
#: the list, and `available()` is the only thing that decides what is offerable.
CATALOGUE: tuple[Action, ...] = (
    # ── Commerce ────────────────────────────────────────────────────────────
    Action("send_premium_offer", "Premium offer", ("commerce",),
           goals=("conversion", "retention"), intensity=4,
           eligible=lambda ctx: _has(ctx, "purchases") >= 1),
    Action("send_discount_offer", "Discount offer", ("commerce",),
           goals=("conversion",), intensity=3),
    Action("send_abandoned_cart_reminder", "Abandoned basket reminder",
           ("commerce",), goals=("conversion",), intensity=3,
           eligible=lambda ctx: _has(ctx, "add_to_carts") > _has(ctx, "purchases")),
    Action("send_replenishment_reminder", "Replenishment reminder", ("commerce",),
           goals=("retention",), intensity=2,
           eligible=lambda ctx: _has(ctx, "purchases") >= 2),
    Action("send_new_arrivals", "New arrivals", ("commerce",),
           goals=("awareness", "engagement"), intensity=1),

    # ── Subscription / SaaS ─────────────────────────────────────────────────
    Action("send_upgrade_prompt", "Upgrade prompt", ("subscription",),
           goals=("conversion",), intensity=4,
           eligible=lambda ctx: _has(ctx, "sessions") >= 2),
    Action("send_trial_extension", "Trial extension", ("subscription",),
           goals=("conversion", "retention"), intensity=3,
           eligible=lambda ctx: _has(ctx, "purchases") == 0),
    Action("send_onboarding_nudge", "Onboarding nudge",
           ("subscription", "lead_capture"),
           goals=("engagement", "lead_generation"), intensity=2,
           eligible=lambda ctx: _has(ctx, "sessions") <= 3),
    Action("send_feature_announcement", "Feature announcement", ("subscription",),
           goals=("engagement", "retention"), intensity=1),

    # ── Lead capture ────────────────────────────────────────────────────────
    Action("send_personalized_offer", "Personalised offer",
           ("commerce", "subscription", "lead_capture"),
           goals=("conversion", "lead_generation"), intensity=3),
    Action("send_case_study", "Case study", ("lead_capture", "subscription"),
           goals=("lead_generation", "awareness"), intensity=2),

    # ── Donation ────────────────────────────────────────────────────────────
    Action("send_donation_appeal", "Donation appeal", ("donation",),
           goals=("conversion",), intensity=4),
    Action("send_impact_update", "Impact update", ("donation",),
           goals=("retention", "engagement"), intensity=2,
           eligible=lambda ctx: _has(ctx, "purchases") >= 1),

    # ── Content ─────────────────────────────────────────────────────────────
    Action("send_digest", "Content digest", ("content",),
           goals=("engagement", "retention"), intensity=1),
    Action("recommend_article", "Article recommendation", ("content",),
           goals=("engagement",), intensity=1,
           eligible=lambda ctx: _has(ctx, "page_views") >= 2),

    # ── Cross-cutting ───────────────────────────────────────────────────────
    Action("send_reactivation_campaign", "Reactivation campaign",
           ("commerce", "subscription", "lead_capture", "donation", "content"),
           goals=("retention",), intensity=3,
           eligible=lambda ctx: _has(ctx, "days_since_last_seen") >= 14),
    # The floor. Available to every site with any capability at all, and to
    # every customer — so `available()` can never return an empty list, which
    # would leave the policy with nothing to choose and no propensity to log.
    Action("send_general_reminder", "General reminder",
           ("commerce", "subscription", "lead_capture", "donation", "content"),
           goals=("awareness", "engagement"), intensity=1),
)

BY_KEY: dict[str, Action] = {a.key: a for a in CATALOGUE}

#: What a site gets when its capabilities are unknown — the historical set, so
#: an unmigrated site behaves exactly as it did before capability detection.
LEGACY_ACTIONS = ("send_premium_offer", "send_personalized_offer",
                  "send_reactivation_campaign", "send_general_reminder")


def site_actions(capabilities: dict[str, bool] | None) -> list[str]:
    """Which actions this website can perform at all.

    With no capabilities detected the legacy four are returned, so a site that
    predates detection keeps working rather than silently losing its actions.
    """
    if not capabilities:
        return list(LEGACY_ACTIONS)

    present = {c for c in CAPABILITIES if capabilities.get(c)}
    if not present:
        return list(LEGACY_ACTIONS)

    return [a.key for a in CATALOGUE if present.intersection(a.requires)]


def available(capabilities: dict[str, bool] | None, context: dict) -> list[str]:
    """The candidate actions for one customer of one site.

    This is the set the policy chooses from and the set the propensity is
    computed over, so it must be deterministic given the same inputs — an
    estimator reading the log months later has to be able to reproduce it.
    """
    offerable = site_actions(capabilities)
    eligible = [key for key in offerable if BY_KEY[key].eligible(context or {})]

    # Never empty: an empty candidate set means no action, no propensity and a
    # division by zero downstream.
    return eligible or ["send_general_reminder"]


def rank_for_goal(actions: list[str], campaign_goal: str | None) -> list[str]:
    """Order candidates by how well they serve the site's inferred goal.

    The goal comes from Module 4's trained classifier reading the site's own
    copy, so this is where an existing model contributes — it orders, it never
    filters. Filtering on a model with macro-F1 near 0.50 would remove actions a
    site genuinely supports on the strength of a coin-flip.
    """
    if not campaign_goal:
        return actions
    return sorted(
        actions,
        key=lambda key: (0 if campaign_goal in BY_KEY[key].goals else 1,
                         -BY_KEY[key].intensity),
    )


def describe(key: str) -> dict[str, Any]:
    """Human-readable detail for the dashboard and the plan."""
    action = BY_KEY.get(key)
    if action is None:
        return {"key": key, "label": key.replace("_", " ").title(),
                "requires": [], "goals": []}
    return {"key": action.key, "label": action.label,
            "requires": list(action.requires), "goals": list(action.goals),
            "intensity": action.intensity}


def withheld(capabilities: dict[str, bool] | None, context: dict) -> list[dict]:
    """Actions this site or customer cannot receive, and why.

    Shown in the dashboard rather than silently omitted: "no premium offer
    because the site has no checkout" is a useful thing for an operator to read,
    and it makes the capability detection auditable instead of invisible.
    """
    offerable = set(site_actions(capabilities))
    present = {c for c in CAPABILITIES if (capabilities or {}).get(c)}
    reasons = []

    for action in CATALOGUE:
        if action.key in offerable:
            if not action.eligible(context or {}):
                reasons.append({
                    "action": action.key, "label": action.label,
                    "reason": "this customer does not qualify yet",
                    "scope": "customer"})
        elif capabilities:
            missing = ", ".join(action.requires)
            reasons.append({
                "action": action.key, "label": action.label,
                "reason": f"the website has no {missing} capability",
                "scope": "site"})
    return reasons
