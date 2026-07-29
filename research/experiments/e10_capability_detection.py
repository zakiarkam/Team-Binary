"""E10 — Does the capability detector read real websites correctly?

The action set is no longer fixed: it is the intersection of what a website can
do and what a customer qualifies for. That makes the capability detector load
bearing. If it misses a checkout, the client silently loses every commerce
action; if it hallucinates one, the system recommends a discount to a news site.

So it is measured on real websites rather than on the demo store it was written
against — the only test that means anything for a detector built from
hand-written signals.

Method
------
A small, hand-labelled sample. For each site the expected capabilities are
recorded from what the *business* demonstrably does — a shop sells things, a
charity takes donations — and the detector is then run against the fetched
homepage. Agreement is reported per capability, with every disagreement listed
individually, because at this sample size the interesting content is *which*
ones it got wrong.

Two honest limitations, both reported rather than designed around:

*   **The label is about the business; the detector sees one page.** A shop
    whose homepage links to no basket is a true miss for single-page detection,
    and pooling across pages (which the running system does) would fix it. The
    experiment measures the harder single-page case on purpose.
*   **The sample is small.** Around twenty sites supports "the detector works"
    or "it does not", not a precise accuracy figure, so Wilson intervals are
    reported and the number is described as indicative.

Pages are cached under `data/raw/capability_sites/` on first run, so the
experiment reproduces offline and never re-fetches during a demonstration.
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from research import config
from research.stats import proportion_ci

ID = "E10"
TITLE = "Module 4 — capability detection on real websites"

CACHE = config.ROOT / "data" / "raw" / "capability_sites"
TIMEOUT = 20
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")

CAPABILITIES = ("commerce", "subscription", "lead_capture", "donation")

#: Hand-labelled sample. `expect` records what the business demonstrably does,
#: judged from the organisation itself rather than from the page — so a miss is
#: a genuine detector failure and not a definition written to be passed.
SITES: tuple[dict, ...] = (
    # ── Retail / commerce ───────────────────────────────────────────────────
    {"url": "https://www.gymshark.com/", "kind": "retail",
     "expect": {"commerce": True, "donation": False}},
    {"url": "https://www.allbirds.com/", "kind": "retail",
     "expect": {"commerce": True, "donation": False}},
    {"url": "https://www.patagonia.com/shop/index", "kind": "retail",
     "expect": {"commerce": True}},
    {"url": "https://www.lush.com/uk/en", "kind": "retail",
     "expect": {"commerce": True}},

    # ── Subscription / SaaS ─────────────────────────────────────────────────
    {"url": "https://slack.com/", "kind": "saas",
     "expect": {"subscription": True, "donation": False}},
    {"url": "https://www.notion.com/", "kind": "saas",
     "expect": {"subscription": True}},
    {"url": "https://www.figma.com/", "kind": "saas",
     "expect": {"subscription": True}},
    {"url": "https://www.dropbox.com/", "kind": "saas",
     "expect": {"subscription": True}},

    # ── Charity / donation ──────────────────────────────────────────────────
    # commerce is True, not False. The first run of this experiment recorded it
    # as False on the assumption that a charity does not sell — and the detector
    # was right and the label wrong: shop.wateraid.org is a real shop. Capability
    # is not a site *type*; a charity that sells merchandise has both. Keeping
    # the correction visible here rather than quietly editing it is the point.
    {"url": "https://www.wateraid.org/uk/", "kind": "charity",
     "expect": {"donation": True, "commerce": True}},
    {"url": "https://www.redcross.org.uk/", "kind": "charity",
     "expect": {"donation": True}},
    {"url": "https://www.wwf.org.uk/", "kind": "charity",
     "expect": {"donation": True}},
    {"url": "https://www.oxfam.org.uk/", "kind": "charity",
     "expect": {"donation": True}},

    # ── Content / publishing ────────────────────────────────────────────────
    {"url": "https://www.bbc.co.uk/news", "kind": "content",
     "expect": {"commerce": False, "donation": False}},
    # Likewise corrected: Ars Technica runs a store selling subscriptions, so
    # commerce is True. A publisher is not automatically content-only.
    {"url": "https://arstechnica.com/", "kind": "content",
     "expect": {"commerce": True}},
    {"url": "https://www.smashingmagazine.com/", "kind": "content",
     "expect": {"commerce": False}},
    {"url": "https://css-tricks.com/", "kind": "content",
     "expect": {"commerce": False}},

    # ── The demo store, as a control ────────────────────────────────────────
    {"url": "local:demo-site/index.html", "kind": "retail (local control)",
     "expect": {"commerce": True, "lead_capture": True, "donation": False}},
)


def _slug(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_")[:80]


def _fetch(url: str) -> tuple[str | None, str]:
    """Return the page HTML, from cache when possible. Never raises."""
    if url.startswith("local:"):
        path = config.ROOT / url.removeprefix("local:")
        return (path.read_text(encoding="utf-8"), "local") if path.exists() \
            else (None, "local file missing")

    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"{_slug(url)}.html"
    if cached.exists():
        return cached.read_text(encoding="utf-8", errors="replace"), "cached"

    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read(3_000_000)
        # The crawler's own encoding lesson: requests defaults to ISO-8859-1 for
        # text/html when the header omits a charset, which turns every em-dash
        # into mojibake. Decode as UTF-8 and replace rather than guess.
        html = raw.decode("utf-8", errors="replace")
        cached.write_text(html, encoding="utf-8")
        return html, "fetched"
    except Exception as exc:
        return None, f"{type(exc).__name__}"


def run() -> dict:
    import crawler

    rows, failures = [], []
    for site in SITES:
        html, how = _fetch(site["url"])
        if html is None:
            failures.append({"url": site["url"], "kind": site["kind"],
                             "reason": how})
            continue

        detected = crawler.extract_page_data(html).get("capabilities", {})
        for capability, expected in site["expect"].items():
            rows.append({
                "url": site["url"],
                "kind": site["kind"],
                "capability": capability,
                "expected": bool(expected),
                "detected": bool(detected.get(capability)),
                "correct": bool(detected.get(capability)) == bool(expected),
                "source": how,
            })

    if not rows:
        return {"id": ID, "title": TITLE, "status": "skipped",
                "reason": ("no page could be fetched or read; the sample needs "
                           "network access on its first run to populate "
                           f"{CACHE.relative_to(config.ROOT)}")}

    # Per-capability agreement, with an interval — the sample is small and a
    # bare percentage would imply more precision than twenty sites can carry.
    per_capability = []
    for capability in CAPABILITIES:
        subset = [r for r in rows if r["capability"] == capability]
        if not subset:
            continue
        correct = sum(r["correct"] for r in subset)
        interval = proportion_ci(correct, len(subset))

        true_positive = sum(1 for r in subset if r["expected"] and r["detected"])
        false_positive = sum(1 for r in subset if not r["expected"] and r["detected"])
        false_negative = sum(1 for r in subset if r["expected"] and not r["detected"])

        per_capability.append({
            "capability": capability,
            "judgements": len(subset),
            "correct": correct,
            "agreement": round(correct / len(subset), 3),
            "ci_low": round(interval.low, 3),
            "ci_high": round(interval.high, 3),
            "false_positives": false_positive,
            "false_negatives": false_negative,
            "precision": round(true_positive / (true_positive + false_positive), 3)
                         if (true_positive + false_positive) else None,
            "recall": round(true_positive / (true_positive + false_negative), 3)
                      if (true_positive + false_negative) else None,
        })

    mistakes = [{"url": r["url"], "kind": r["kind"], "capability": r["capability"],
                 "expected": r["expected"], "detected": r["detected"]}
                for r in rows if not r["correct"]]

    correct_total = sum(r["correct"] for r in rows)
    overall = proportion_ci(correct_total, len(rows))

    notes = [
        f"{len(rows)} capability judgements across "
        f"{len({r['url'] for r in rows})} websites. Overall agreement with the "
        f"hand label is {correct_total / len(rows):.0%} "
        f"[{overall.low:.0%}, {overall.high:.0%}].",

        "The label records what the business demonstrably does; the detector "
        "sees one page. A shop whose homepage links to no basket is a true miss "
        "for single-page detection — the running system pools evidence across "
        "every page it has crawled, which this experiment deliberately does not, "
        "so these figures are a lower bound on what the system achieves.",

        f"Around twenty sites supports a verdict, not a precise accuracy. The "
        f"intervals are wide and are reported rather than rounded away.",

        "**This sample is a development set, not a held-out test set, and the "
        "figure above is fitted.** The first run disagreed on four judgements. "
        "Two were detector faults and were fixed: substring matching on URLs "
        "fired `/product` on a magazine's `/categories/product-strategy` and "
        "read a retailer's customer-support subdomain as a donation page, so "
        "matching now works on whole path segments and host labels. The other "
        "two were faults in the labels — a charity with a shop and a publisher "
        "with a store were both marked as having no commerce, and the detector "
        "was right. Both the code and the labels therefore changed after seeing "
        "the results, which is precisely what makes an accuracy figure optimistic. "
        "A fresh sample of sites never inspected during development would be "
        "needed to claim generalisation, and this experiment does not claim it.",

        "The useful finding is not the percentage but what the disagreements "
        "taught: capability is not a site *type*. A charity that sells "
        "merchandise has both donation and commerce; a publisher running a "
        "store has commerce as well as content. Modelling capabilities as "
        "independent flags rather than as a category is what let the detector "
        "be right where the hand label was wrong.",
    ]

    false_positives = sum(c["false_positives"] for c in per_capability)
    if false_positives:
        notes.append(
            f"{false_positives} false positive(s): the detector claimed a "
            "capability the site does not have, which is the worse error — it "
            "would let the system recommend an action the client cannot "
            "perform. A false negative only costs a smaller action set.")
    else:
        notes.append(
            "No false positives: the detector never claimed a capability a site "
            "does not have. That is the error that matters, because it would "
            "have the system recommend something the client cannot do.")

    if failures:
        notes.append(
            f"{len(failures)} site(s) could not be fetched "
            f"({', '.join(sorted({f['reason'] for f in failures}))}) and are "
            "excluded. Reported rather than quietly dropped.")

    return {
        "id": ID,
        "title": TITLE,
        "status": "ok",
        "metrics": {
            "sites_evaluated": len({r["url"] for r in rows}),
            "sites_unreachable": len(failures),
            "judgements": len(rows),
            "overall_agreement": round(correct_total / len(rows), 3),
            "agreement_ci": [round(overall.low, 3), round(overall.high, 3)],
            "false_positives": false_positives,
            "false_negatives": sum(c["false_negatives"] for c in per_capability),
        },
        "tables": {
            "e10_per_capability": per_capability,
            "e10_judgements": rows,
            **({"e10_mistakes": mistakes} if mistakes else {}),
            **({"e10_unreachable": failures} if failures else {}),
        },
        "notes": notes,
    }
