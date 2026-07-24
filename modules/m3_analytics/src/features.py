"""features.py — Build per-user feature table for predictive modelling (Phase 4a)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

DROPOFF_WINDOW_DAYS = 14


def build_features(
    events_df: pd.DataFrame,
    segments_df: pd.DataFrame,
    reference_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Return one row per user with engineered features and binary targets.

    Columns
    -------
    user_id, segment, strategy,
    n_sent, n_opens, n_clicks, journey_length,
    avg_time_between_events_hours, recency_days,
    dominant_channel, first_channel, last_channel,
    converted, dropped_off
    """
    events_df = events_df.copy()
    events_df["timestamp"] = pd.to_datetime(events_df["timestamp"])

    if reference_date is None:
        reference_date = events_df["timestamp"].max() + pd.Timedelta(days=1)

    rows = []
    for uid, grp in events_df.groupby("user_id"):
        grp = grp.sort_values("timestamp")
        event_types = set(grp["event_type"])

        # ---- counts ----
        n_sent   = (grp["event_type"] == "sent").sum()
        n_opens  = (grp["event_type"] == "open").sum()
        n_clicks = (grp["event_type"] == "click").sum()
        journey_length = len(grp)

        # ---- timing ----
        timestamps = grp["timestamp"].sort_values().reset_index(drop=True)
        if len(timestamps) > 1:
            diffs = timestamps.diff().dropna().dt.total_seconds() / 3600
            avg_gap_hours = diffs.mean()
        else:
            avg_gap_hours = 0.0

        recency_days = (reference_date - timestamps.iloc[-1]).total_seconds() / 86400

        # ---- channel features ----
        dominant_channel = grp["channel"].value_counts().idxmax()
        first_channel    = grp.iloc[0]["channel"]
        last_channel     = grp.iloc[-1]["channel"]

        # strategy: take the mode (most-used for this user)
        strategy = grp["strategy"].mode().iloc[0]

        # ---- targets ----
        converted   = int("convert" in event_types)
        # dropped_off: engaged (open or click) but no conversion within the window
        engaged = "open" in event_types or "click" in event_types
        if engaged and not converted:
            # Check whether they engaged within DROPOFF_WINDOW_DAYS of first engagement
            first_engage = grp.loc[
                grp["event_type"].isin(["open", "click"]), "timestamp"
            ].min()
            cutoff = first_engage + pd.Timedelta(days=DROPOFF_WINDOW_DAYS)
            still_no_convert = grp[
                (grp["event_type"] == "convert") & (grp["timestamp"] <= cutoff)
            ].empty
            dropped_off = int(still_no_convert)
        else:
            dropped_off = 0

        rows.append({
            "user_id":                     uid,
            "strategy":                    strategy,
            "n_sent":                      int(n_sent),
            "n_opens":                     int(n_opens),
            "n_clicks":                    int(n_clicks),
            "journey_length":              int(journey_length),
            "avg_time_between_events_hours": round(float(avg_gap_hours), 4),
            "recency_days":                round(float(recency_days), 4),
            "dominant_channel":            dominant_channel,
            "first_channel":               first_channel,
            "last_channel":                last_channel,
            "converted":                   converted,
            "dropped_off":                 dropped_off,
        })

    feat_df = pd.DataFrame(rows)
    feat_df = feat_df.merge(
        segments_df[["user_id", "segment"]], on="user_id", how="left"
    )
    # Reorder so user_id + segment are first
    cols = (
        ["user_id", "segment"]
        + [c for c in feat_df.columns if c not in ("user_id", "segment")]
    )
    return feat_df[cols]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build per-user feature table.")
    parser.add_argument("--in",  dest="src", default="data/simulated/",
                        help="Directory containing event_logs.csv and user_segments.csv")
    parser.add_argument("--out", dest="dst", default="data/processed/",
                        help="Output directory for features.csv")
    args = parser.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)
    dst.mkdir(parents=True, exist_ok=True)

    events   = pd.read_csv(src / "event_logs.csv",   parse_dates=["timestamp"])
    segments = pd.read_csv(src / "user_segments.csv")

    features = build_features(events, segments)
    out_path = dst / "features.csv"
    features.to_csv(out_path, index=False)

    print(f"Features saved: {out_path}  shape={features.shape}")
    print(f"Converted  : {features['converted'].sum()} / {len(features)} "
          f"({features['converted'].mean() * 100:.1f}%)")
    print(f"Dropped-off: {features['dropped_off'].sum()} / {len(features)} "
          f"({features['dropped_off'].mean() * 100:.1f}%)")


if __name__ == "__main__":
    main()
