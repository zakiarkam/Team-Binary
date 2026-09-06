"""bootstrap.py — Bootstrap 95% confidence intervals for headline metrics.

Resamples users (not events) with replacement to preserve within-user
correlation between events. For each replicate we recompute:

  - per-strategy end-to-end conversion rate
  - lift of trigger vs fixed and hybrid vs fixed
  - attribution MAE per model

Outputs a CSV with point estimate, 95% CI, and an approximate two-sided
p-value for the lift hypotheses (H0: lift <= 0).

Run:
    python -m src.bootstrap --n-boot 1000
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.attribution import attribution_mae, compare_to_ground_truth


def _resample_users(
    events: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """Sample user_ids with replacement and return their concatenated events.

    Vectorised join via a temporary index DataFrame so we don't loop over users.
    Each duplicated user gets a unique synthetic ID to preserve independence.
    """
    users = events["user_id"].unique()
    sampled = rng.choice(users, size=len(users), replace=True)
    # Map each draw to a synthetic id so duplicates don't collapse in groupby
    sample_df = pd.DataFrame(
        {"user_id": sampled, "_synth": [f"S{i:06d}" for i in range(len(sampled))]}
    )
    merged = sample_df.merge(events, on="user_id", how="left")
    merged["user_id"] = merged["_synth"]
    merged = merged.drop(columns="_synth")
    return merged


def _strategy_conv_rates(events: pd.DataFrame) -> dict[str, float]:
    """Per-strategy end-to-end conversion rate = unique converters / unique senders."""
    out: dict[str, float] = {}
    for strat, grp in events.groupby("strategy"):
        sent = grp.loc[grp["event_type"] == "sent", "user_id"].nunique()
        conv = grp.loc[grp["event_type"] == "convert", "user_id"].nunique()
        out[strat] = conv / sent if sent else 0.0
    return out


def bootstrap_strategy(
    events: pd.DataFrame, n_boot: int = 1000, seed: int = 42
) -> pd.DataFrame:
    """Bootstrap per-strategy conversion rates and pairwise lifts."""
    rng = np.random.default_rng(seed)
    rates_records: list[dict[str, float]] = []
    for _ in range(n_boot):
        boot = _resample_users(events, rng)
        rates_records.append(_strategy_conv_rates(boot))
    boot_df = pd.DataFrame(rates_records).fillna(0.0)

    point = _strategy_conv_rates(events)
    rows = []
    for strat in sorted(point):
        col = boot_df[strat]
        rows.append({
            "metric": f"conv_rate[{strat}]",
            "point": round(point[strat], 4),
            "ci_lo": round(float(col.quantile(0.025)), 4),
            "ci_hi": round(float(col.quantile(0.975)), 4),
            "p_value": np.nan,
        })

    # Lift rows: H0 = lift <= 0; report fraction of replicates where lift <= 0.
    if "fixed" in boot_df.columns:
        for strat in ("trigger", "hybrid"):
            if strat not in boot_df.columns:
                continue
            lift = (boot_df[strat] - boot_df["fixed"]) / boot_df["fixed"].replace(0, np.nan)
            lift = lift.dropna()
            point_lift = (point[strat] - point["fixed"]) / point["fixed"] if point["fixed"] else 0
            p = float((lift <= 0).mean())
            rows.append({
                "metric": f"lift[{strat} vs fixed]",
                "point": round(point_lift, 4),
                "ci_lo": round(float(lift.quantile(0.025)), 4),
                "ci_hi": round(float(lift.quantile(0.975)), 4),
                "p_value": round(p, 4),
            })
    return pd.DataFrame(rows)


def bootstrap_attribution(
    events: pd.DataFrame,
    ground_truth: pd.DataFrame,
    n_boot: int = 200,
    seed: int = 42,
) -> pd.DataFrame:
    """Bootstrap attribution MAE per model. Fewer iterations because Markov is slow."""
    rng = np.random.default_rng(seed)
    records: list[dict[str, float]] = []
    for _ in range(n_boot):
        boot = _resample_users(events, rng)
        comp = compare_to_ground_truth(boot, ground_truth, level="platform")
        records.append(attribution_mae(comp))
    boot_df = pd.DataFrame(records).fillna(0.0)

    point_comp = compare_to_ground_truth(events, ground_truth, level="platform")
    point = attribution_mae(point_comp)

    rows = []
    for model in boot_df.columns:
        col = boot_df[model]
        rows.append({
            "metric": f"attribution_MAE[{model}]",
            "point": round(point[model], 4),
            "ci_lo": round(float(col.quantile(0.025)), 4),
            "ci_hi": round(float(col.quantile(0.975)), 4),
            "p_value": np.nan,
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap 95% CIs for headline metrics.")
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--n-boot-attribution", type=int, default=200)
    parser.add_argument("--simulated-dir", default="data/simulated/")
    parser.add_argument("--out", default="outputs/reports/bootstrap_ci.csv")
    args = parser.parse_args()

    sim = Path(args.simulated_dir)
    events = pd.read_csv(sim / "event_logs.csv", parse_dates=["timestamp"])
    gt = pd.read_csv(sim / "ground_truth_influence.csv")

    print(f"Bootstrapping strategy conversion ({args.n_boot} replicates)...")
    s_df = bootstrap_strategy(events, n_boot=args.n_boot)

    print(f"Bootstrapping attribution MAE ({args.n_boot_attribution} replicates, slower)...")
    a_df = bootstrap_attribution(events, gt, n_boot=args.n_boot_attribution)

    out = pd.concat([s_df, a_df], ignore_index=True)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
