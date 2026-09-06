"""Module 1 — Hybrid Dynamic Segmentation Engine (runnable implementation).

This is the code behind Novel Contribution 1. It was previously only a Jupyter
notebook (`segmentation.ipynb`) whose output was frozen into a CSV, which meant
the system could never segment a *new* audience. This module makes it a real,
reusable engine that runs on live website visitors.

The method, unchanged from the research:

    rule-based  ─┐
    K-Means      ├─▶ agreement vote ─▶ segment + confidence
    hierarchical ┘

Three deliberate corrections to the notebook are documented inline below:

1.  **Cluster labels are derived, not hardcoded.**
    The notebook mapped cluster 0 → "Low Engagement", 1 → "High Intent", …
    Those indices are an artifact of one dataset and one random seed; on any new
    audience the mapping is simply wrong. Here each cluster is named from its
    own centroid, so the engine is correct on data it has never seen.

2.  **The Random Forest no longer leaks.**
    The notebook trained the RF with `rule_encoded` as both an input feature and
    the target, so it was predicting its own input — which is why 6,248 of 8,000
    users came out with confidence exactly 1.00. Here the RF learns the hybrid
    consensus from *behavioural features only*. Its accuracy is therefore a real
    generalisation number, and it gains a genuine purpose: labelling a brand-new
    visitor instantly, without re-running the clustering.

3.  **Cold start is handled explicitly, at two levels.**
    - *Population*: with fewer than `min_users_for_clustering` visitors there is
      nothing meaningful to cluster, so the engine runs rules only and says so.
    - *Individual*: a visitor with almost no history is decided by rules and
      flagged `is_cold_start`, whatever the clustering thinks.

Usage:

    from modules.m1_segmentation.segment import web_segmenter, research_segmenter

    result = web_segmenter().fit_predict(visitor_features_df)
    result = research_segmenter().fit_predict(kaggle_df)   # reproduces the study
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

# ── Segment vocabulary ───────────────────────────────────────────────────────
# These five labels are the contract with Module 2 (campaign automation) and
# Module 3 (analytics). The ids match the notebook so existing artifacts and
# figures stay comparable.
HIGH_INTENT = "High Intent"
LOW_ENGAGEMENT = "Low Engagement"
PRICE_SENSITIVE = "Price Sensitive"
LOYAL_CUSTOMER = "Loyal Customer"
NEW_COLD_USER = "New Cold User"

SEGMENTS = [HIGH_INTENT, LOW_ENGAGEMENT, PRICE_SENSITIVE, LOYAL_CUSTOMER, NEW_COLD_USER]
SEGMENT_IDS = {
    HIGH_INTENT: 1,
    LOW_ENGAGEMENT: 2,
    PRICE_SENSITIVE: 3,
    LOYAL_CUSTOMER: 4,
    NEW_COLD_USER: 5,
}

MODEL_VERSION = "m1-hybrid-2.0"


# ── Feature-set definitions ──────────────────────────────────────────────────
@dataclass(frozen=True)
class FeatureSet:
    """Which columns to cluster on, and how to read them behaviourally.

    `engagement` and `loyalty` name the columns that express those two ideas in
    this domain. They are what lets cluster naming be derived rather than
    hardcoded, and they are the only domain knowledge the engine needs.
    """

    name: str
    columns: list[str]
    engagement: list[str]
    loyalty: list[str]
    evidence: list[str]   # columns whose total says how much we know about a user


# Kaggle "digital marketing campaign" dataset — the research setting.
RESEARCH_FEATURES = FeatureSet(
    name="research",
    columns=[
        "EmailOpens", "EmailClicks", "WebsiteVisits", "PagesPerVisit",
        "TimeOnSite", "SocialShares", "PreviousPurchases", "LoyaltyPoints",
    ],
    engagement=["EmailOpens", "EmailClicks", "WebsiteVisits", "PagesPerVisit", "TimeOnSite"],
    loyalty=["PreviousPurchases", "LoyaltyPoints"],
    evidence=["EmailOpens", "EmailClicks", "WebsiteVisits", "PreviousPurchases"],
)

# Live website visitors — the product setting. These are exactly the columns
# api/routers/visitors.py computes from the mos.js event stream.
WEB_FEATURES = FeatureSet(
    name="web",
    columns=[
        "page_views", "clicks", "sessions", "unique_pages",
        "max_scroll_depth", "time_on_site_seconds", "form_submits", "purchases",
    ],
    engagement=["page_views", "clicks", "unique_pages", "max_scroll_depth",
                "time_on_site_seconds"],
    loyalty=["purchases", "sessions"],
    evidence=["page_views", "clicks", "sessions", "purchases"],
)


# ── Rule-based segmentation ──────────────────────────────────────────────────
def research_rules(df: pd.DataFrame) -> pd.Series:
    """The notebook's rules, vectorised and with its quantile cold-start test.

    Order matters: the first matching condition wins, and "New Cold User" is
    tested first so a genuinely new user is never mistaken for a disengaged one.
    """
    p25_purchases = df["PreviousPurchases"].quantile(0.25)
    p25_loyalty = df["LoyaltyPoints"].quantile(0.25)
    p25_clicks = df["EmailClicks"].quantile(0.25)

    cold = (
        (df["PreviousPurchases"] <= p25_purchases)
        & (df["LoyaltyPoints"] <= p25_loyalty)
        & (df["EmailClicks"] <= p25_clicks)
    )
    loyal = (df["PreviousPurchases"] >= 6) & (df["LoyaltyPoints"] >= 2000)
    high = (df["EmailClicks"] >= 6) & (df["WebsiteVisits"] >= 30)
    price = (df["WebsiteVisits"] >= 25) & (df["EmailClicks"] <= 4)

    out = pd.Series(LOW_ENGAGEMENT, index=df.index, dtype=object)
    out[price] = PRICE_SENSITIVE
    out[high] = HIGH_INTENT
    out[loyal] = LOYAL_CUSTOMER
    out[cold] = NEW_COLD_USER    # applied last so it takes priority
    return out


def web_rules(df: pd.DataFrame) -> pd.Series:
    """Rules for live website visitors.

    The research dataset assumes an email history that a first-time visitor to a
    newly launched product simply does not have — which is the cold-start
    problem this project is about. These rules therefore read the same five
    segments off on-site behaviour instead:

      New Cold User    almost no activity yet (this is the cold-start majority)
      Loyal Customer   has converted, and keeps coming back
      High Intent      deep, repeated engagement — reads a lot, clicks a lot
      Price Sensitive  browses repeatedly (often pricing) but does not engage
      Low Engagement   everything else: present, but shallow
    """
    page_views = df["page_views"]
    clicks = df["clicks"]
    sessions = df["sessions"]
    purchases = df["purchases"]
    depth = df["max_scroll_depth"]
    seconds = df["time_on_site_seconds"]

    cold = (page_views <= 1) & (clicks == 0) & (purchases == 0)
    # A repeat buyer is loyal; a first-time buyer is high intent. Conversion is
    # the strongest signal there is, so anyone who has converted must land in
    # one of those two — never in Low Engagement.
    loyal = (purchases >= 1) & (sessions >= 2)
    engaged = (clicks >= 2) & (page_views >= 2) & ((depth >= 75) | (seconds >= 60))
    high = (purchases >= 1) | engaged
    price = (sessions >= 2) & (clicks <= 1) & (purchases == 0)

    out = pd.Series(LOW_ENGAGEMENT, index=df.index, dtype=object)
    out[price] = PRICE_SENSITIVE
    out[high] = HIGH_INTENT
    out[loyal] = LOYAL_CUSTOMER
    out[cold] = NEW_COLD_USER
    return out


# ── Result container ─────────────────────────────────────────────────────────
@dataclass
class SegmentationResult:
    frame: pd.DataFrame                 # per-user labels, confidence, flags
    diagnostics: dict = field(default_factory=dict)

    @property
    def counts(self) -> dict[str, int]:
        return self.frame["segment_name"].value_counts().to_dict()

    def to_user_segments(self, id_column: str) -> pd.DataFrame:
        """The hand-off schema Module 2 consumes."""
        return pd.DataFrame({
            "user_id": self.frame[id_column],
            "CustomerID": self.frame[id_column],
            "segment_id": self.frame["segment_name"].map(SEGMENT_IDS),
            "segment_name": self.frame["segment_name"],
            "segment_method": self.frame["segment_method"],
            "segment_confidence": self.frame["segment_confidence"].round(3),
        })


# ── The engine ───────────────────────────────────────────────────────────────
class HybridSegmenter:
    """Rule-based + K-Means + hierarchical clustering, combined by agreement."""

    def __init__(
        self,
        features: FeatureSet,
        rule_fn: Callable[[pd.DataFrame], pd.Series],
        n_clusters: int = 4,
        min_users_for_clustering: int = 30,
        min_evidence: float = 2.0,
        random_state: int = 42,
    ) -> None:
        self.features = features
        self.rule_fn = rule_fn
        self.n_clusters = n_clusters
        self.min_users_for_clustering = min_users_for_clustering
        self.min_evidence = min_evidence
        self.random_state = random_state

        self.scaler: StandardScaler | None = None
        self.kmeans: KMeans | None = None
        self.cluster_names: dict[int, str] = {}
        self.classifier: RandomForestClassifier | None = None
        self.classifier_accuracy: float | None = None

    # ── helpers ─────────────────────────────────────────────────────────────
    def _matrix(self, df: pd.DataFrame) -> np.ndarray:
        missing = [c for c in self.features.columns if c not in df.columns]
        if missing:
            raise KeyError(
                f"Missing feature columns for the '{self.features.name}' "
                f"feature set: {missing}"
            )
        return df[self.features.columns].astype(float).fillna(0.0).to_numpy()

    def _name_clusters(self, scaled: np.ndarray, labels: np.ndarray) -> dict[int, str]:
        """Name each cluster from its own centroid.

        Every cluster is scored on two axes — how engaged it is and how loyal it
        is — using the already-standardised features, so the scores are directly
        comparable. Names are then assigned by rank, which makes the result
        stable across datasets and random seeds.
        """
        cols = self.features.columns
        eng_idx = [cols.index(c) for c in self.features.engagement if c in cols]
        loy_idx = [cols.index(c) for c in self.features.loyalty if c in cols]

        profile = []
        for cluster in sorted(set(labels)):
            centroid = scaled[labels == cluster].mean(axis=0)
            profile.append({
                "cluster": int(cluster),
                "engagement": float(centroid[eng_idx].mean()) if eng_idx else 0.0,
                "loyalty": float(centroid[loy_idx].mean()) if loy_idx else 0.0,
            })

        names: dict[int, str] = {}
        remaining = list(profile)

        # Most loyal cluster first — loyalty is the strongest commercial signal.
        loyal = max(remaining, key=lambda p: p["loyalty"])
        names[loyal["cluster"]] = LOYAL_CUSTOMER
        remaining.remove(loyal)

        if remaining:
            high = max(remaining, key=lambda p: p["engagement"])
            names[high["cluster"]] = HIGH_INTENT
            remaining.remove(high)
        if remaining:
            low = min(remaining, key=lambda p: p["engagement"])
            names[low["cluster"]] = LOW_ENGAGEMENT
            remaining.remove(low)
        for leftover in remaining:
            names[leftover["cluster"]] = PRICE_SENSITIVE

        return names

    def _evidence(self, df: pd.DataFrame) -> pd.Series:
        """How much we actually know about each user."""
        cols = [c for c in self.features.evidence if c in df.columns]
        if not cols:
            return pd.Series(np.inf, index=df.index)
        return df[cols].astype(float).fillna(0.0).sum(axis=1)

    @staticmethod
    def _vote(rule: str, ml: str, hier: str) -> tuple[str, float]:
        """Combine the three opinions into a label and a calibrated confidence.

        The confidence is the *agreement level*, not a probability: three
        independent methods concurring is strong evidence; none concurring means
        we fall back to the interpretable rule and say so with a low number.

        Cold start is resolved second, before any clustering agreement. This
        ordering is deliberate and differs from the notebook, where the
        `ml == hier` branch came first. Clustering cannot express "there is not
        enough evidence about this user" — it must place everyone in some
        cluster — so whenever the two clusterings happened to agree they
        overruled the rules and the New Cold User segment was silently emptied
        (43 detected → 0 surviving on live data; 163 → 127 on the research set).
        A method that cannot represent a finding does not get to veto it.
        """
        if rule == ml == hier:
            return rule, 0.95
        if rule == NEW_COLD_USER:
            # Clustering has no vote here, so confidence reflects that this
            # rests on the rule alone — evidence of absence, not strong evidence.
            return NEW_COLD_USER, 0.65
        if rule == ml:
            return rule, 0.80
        if rule == hier:
            return rule, 0.75
        if ml == hier:
            return ml, 0.70
        return rule, 0.60

    # ── main entry point ────────────────────────────────────────────────────
    def fit_predict(self, df: pd.DataFrame) -> SegmentationResult:
        df = df.reset_index(drop=True)
        n = len(df)
        if n == 0:
            return SegmentationResult(
                frame=df.assign(segment_name=[], segment_method=[],
                                segment_confidence=[], is_cold_start=[]),
                diagnostics={"n_users": 0, "reason": "empty input"},
            )

        rule_labels = self.rule_fn(df)
        evidence = self._evidence(df)
        thin = evidence < self.min_evidence

        # ── Population-level cold start ─────────────────────────────────────
        # Clustering a handful of visitors invents structure that is not there.
        # A newly launched product lives here, so this path is not an edge case
        # — it is the normal early state, and the engine must stay useful in it.
        if n < self.min_users_for_clustering:
            out = df.copy()
            out["segment_name"] = rule_labels
            out["segment_method"] = "cold_start_rules"
            out["segment_confidence"] = 0.50
            out["is_cold_start"] = True
            return SegmentationResult(
                frame=out,
                diagnostics={
                    "n_users": n,
                    "mode": "cold_start_rules",
                    "reason": (
                        f"only {n} users — fewer than the {self.min_users_for_clustering} "
                        "needed for meaningful clustering, so rules decide alone"
                    ),
                    "cold_start_users": int(n),
                },
            )

        # ── Full hybrid path ────────────────────────────────────────────────
        matrix = self._matrix(df)
        self.scaler = StandardScaler()
        scaled = self.scaler.fit_transform(matrix)

        k = min(self.n_clusters, n)
        self.kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
        km_labels = self.kmeans.fit_predict(scaled)

        hier_labels = AgglomerativeClustering(
            n_clusters=k, linkage="ward").fit_predict(scaled)

        self.cluster_names = self._name_clusters(scaled, km_labels)
        hier_names = self._name_clusters(scaled, hier_labels)

        ml_labels = pd.Series([self.cluster_names[c] for c in km_labels], index=df.index)
        hi_labels = pd.Series([hier_names[c] for c in hier_labels], index=df.index)

        voted = [self._vote(r, m, h)
                 for r, m, h in zip(rule_labels, ml_labels, hi_labels)]

        out = df.copy()
        out["rule_segment"] = rule_labels
        out["ml_segment"] = ml_labels
        out["hierarchical_segment"] = hi_labels
        out["segment_name"] = [v[0] for v in voted]
        out["segment_confidence"] = [v[1] for v in voted]
        out["segment_method"] = "hybrid"
        out["is_cold_start"] = False

        # ── Individual cold start ───────────────────────────────────────────
        # A visitor with one page view lands in whichever cluster the geometry
        # puts them, which is meaningless. Rules decide for them, and we mark it
        # so the dashboard and the campaign engine can treat them differently.
        if thin.any():
            out.loc[thin, "segment_name"] = rule_labels[thin]
            out.loc[thin, "segment_method"] = "cold_start_rules"
            out.loc[thin, "segment_confidence"] = 0.50
            out.loc[thin, "is_cold_start"] = True

        diagnostics = {
            "n_users": n,
            "mode": "hybrid",
            "k": k,
            "cluster_names": self.cluster_names,
            "cold_start_users": int(thin.sum()),
            "unanimous_users": int(sum(1 for v in voted if v[1] == 0.95)),
            "all_disagree_users": int(sum(1 for v in voted if v[1] == 0.60)),
            "mean_confidence": round(float(out["segment_confidence"].mean()), 3),
        }
        if k > 1 and n > k:
            diagnostics["silhouette"] = round(float(silhouette_score(scaled, km_labels)), 4)

        # ── Inductive classifier (no leakage) ───────────────────────────────
        self._fit_classifier(matrix, out["segment_name"], diagnostics)

        return SegmentationResult(frame=out, diagnostics=diagnostics)

    def _fit_classifier(self, matrix: np.ndarray, target: pd.Series,
                        diagnostics: dict) -> None:
        """Learn the hybrid consensus from behavioural features alone.

        Trained on features only — never on the rule/cluster labels that produced
        the target. That distinction is the whole difference between a model that
        generalises and the notebook's version, which was handed the answer as an
        input feature and unsurprisingly scored ~100%.

        Its purpose is practical: once fitted, a brand-new visitor can be
        segmented on the spot without re-clustering the whole audience.
        """
        from sklearn.model_selection import train_test_split

        if target.nunique() < 2:
            diagnostics["classifier"] = "not fitted — only one segment present"
            return

        counts = target.value_counts()
        stratify = target if counts.min() >= 2 else None
        try:
            x_train, x_test, y_train, y_test = train_test_split(
                matrix, target, test_size=0.2,
                random_state=self.random_state, stratify=stratify,
            )
        except ValueError as exc:  # too few samples in some class
            diagnostics["classifier"] = f"not fitted — {exc}"
            return

        clf = RandomForestClassifier(
            n_estimators=200, random_state=self.random_state,
            min_samples_leaf=2, class_weight="balanced_subsample",
        )
        clf.fit(x_train, y_train)

        self.classifier = clf
        self.classifier_accuracy = float(clf.score(x_test, y_test))
        diagnostics["classifier_accuracy"] = round(self.classifier_accuracy, 4)
        diagnostics["classifier_note"] = (
            "held-out accuracy predicting the hybrid consensus from behavioural "
            "features only (no segment labels among the inputs)"
        )
        if self.classifier_accuracy > 0.99:
            # Worth saying out loud rather than quoting as a headline result.
            diagnostics["classifier_caveat"] = (
                "near-perfect accuracy is expected here, not impressive: the rule "
                "component of the target is itself a deterministic function of "
                "these same features, so this measures internal consistency, not "
                "generalisation to a new audience"
            )
        diagnostics["feature_importance"] = {
            col: round(float(imp), 4)
            for col, imp in sorted(
                zip(self.features.columns, clf.feature_importances_),
                key=lambda pair: pair[1], reverse=True,
            )
        }

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Segment new users with the fitted classifier (no re-clustering)."""
        if self.classifier is None:
            raise RuntimeError("Call fit_predict() before predict().")

        matrix = self._matrix(df)
        labels = self.classifier.predict(matrix)
        proba = self.classifier.predict_proba(matrix).max(axis=1)

        evidence = self._evidence(df)
        thin = (evidence < self.min_evidence).to_numpy()
        rule_labels = self.rule_fn(df).to_numpy()

        labels = np.where(thin, rule_labels, labels)
        confidence = np.where(thin, 0.50, proba)

        return pd.DataFrame({
            "segment_name": labels,
            "segment_confidence": confidence,
            "segment_method": np.where(thin, "cold_start_rules", "hybrid_classifier"),
            "is_cold_start": thin,
        }, index=df.index)


# ── Preconfigured engines ────────────────────────────────────────────────────
def research_segmenter(**kwargs) -> HybridSegmenter:
    """The engine as evaluated in the research, on the Kaggle campaign dataset."""
    return HybridSegmenter(RESEARCH_FEATURES, research_rules, **kwargs)


def web_segmenter(**kwargs) -> HybridSegmenter:
    """The engine as deployed, on live website visitors from mos.js."""
    kwargs.setdefault("min_evidence", 2.0)
    return HybridSegmenter(WEB_FEATURES, web_rules, **kwargs)


# ── CLI: reproduce the research segmentation ─────────────────────────────────
def main() -> None:
    import argparse
    import json

    here = Path(__file__).resolve().parent

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default=str(here / "digital_marketing_campaign_dataset.csv"))
    ap.add_argument("--out", default=str(here / "user_segments.csv"))
    ap.add_argument("--dry-run", action="store_true", help="Do not write the CSV")
    args = ap.parse_args()

    df = pd.read_csv(args.dataset)
    print(f"Loaded {len(df):,} users from {Path(args.dataset).name}")

    result = research_segmenter().fit_predict(df)

    print("\nSegment distribution")
    for name, count in sorted(result.counts.items(), key=lambda kv: -kv[1]):
        print(f"  {name:<18} {count:>6,}  ({count / len(df):.1%})")

    print("\nDiagnostics")
    for key, value in result.diagnostics.items():
        if key == "feature_importance":
            print(f"  {key}:")
            for col, imp in list(value.items())[:5]:
                print(f"      {col:<20} {imp}")
        else:
            print(f"  {key}: {json.dumps(value) if isinstance(value, dict) else value}")

    if "Conversion" in df.columns:
        print("\nConversion rate by segment (evaluation only — never a feature)")
        conv = result.frame.groupby("segment_name")["Conversion"].mean().sort_values(
            ascending=False)
        for name, rate in conv.items():
            print(f"  {name:<18} {rate:.1%}")
        print(f"  → separation: {(conv.max() - conv.min()) * 100:.1f} percentage points")

    if not args.dry_run:
        out = result.to_user_segments("CustomerID")
        out.to_csv(args.out, index=False)
        print(f"\nWrote {len(out):,} rows → {args.out}")


if __name__ == "__main__":
    main()
