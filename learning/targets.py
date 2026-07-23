"""Content-relative engagement targets.

This module is the whole point of the learning subsystem, so it is worth being
explicit about *why* it exists.

The naive target is absolute interactions — "this post got 890 likes". Trained on
that, a model learns follower count, not content quality: a post from a
1,000,000-follower account outscores an identical caption from a 500-follower
account purely because more people saw it. That is the account-size confound,
and it is the documented reason text-only engagement prediction is weak (large
social/graph features dominate the text).

The fix is to make the target *relative to the account's own baseline*:

  1. engagement_rate = interactions / impressions
     Impressions already partly cancels reach, so this is the account-robust
     target to use when there is no per-account history (the cold-start base
     model). This is what the existing engagement.py already does.

  2. within-account normalization (z-score or percentile of the rate)
     "Is this post better than THIS account usually does?" This removes account
     size entirely, so one pooled model is comparable across accounts, and it is
     also the personalization signal — a caption is ranked against the business's
     own distribution. Requires an account id and enough posts per account.

`relative_target` returns level 2 where an account has enough history and falls
back to level 1 otherwise, so a single call handles a corpus that mixes
data-rich and brand-new accounts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def engagement_rate(
    likes,
    comments,
    shares,
    impressions,
) -> pd.Series:
    """(likes + comments + shares) / impressions, guarding divide-by-zero.

    Accepts scalars or Series. Impressions ≤ 0 yields a rate of 0 rather than
    inf/NaN, so a row with no recorded reach cannot poison the target column.
    """
    likes = pd.to_numeric(pd.Series(likes), errors="coerce").fillna(0.0)
    comments = pd.to_numeric(pd.Series(comments), errors="coerce").fillna(0.0)
    shares = pd.to_numeric(pd.Series(shares), errors="coerce").fillna(0.0)
    impressions = pd.to_numeric(pd.Series(impressions), errors="coerce").fillna(0.0)

    interactions = likes + comments + shares
    safe = impressions.where(impressions > 0, other=np.nan)
    rate = (interactions / safe).fillna(0.0)
    return rate.clip(lower=0.0).reset_index(drop=True)


def _account_relative(
    rate: pd.Series,
    account: pd.Series,
    method: str,
    min_posts: int,
) -> tuple[pd.Series, pd.Series]:
    """Normalize `rate` within each account.

    Returns (relative, used_relative) where used_relative marks the rows an
    account actually had enough history to normalize. Rows in a too-small
    account are left as NaN here for the caller to backfill with the raw rate.
    """
    rate = rate.reset_index(drop=True)
    account = account.reset_index(drop=True).fillna("__unknown__").astype(str)

    counts = account.map(account.value_counts())
    eligible = counts >= min_posts

    relative = pd.Series(np.nan, index=rate.index, dtype="float64")

    for account_id, group_index in account.groupby(account).groups.items():
        idx = pd.Index(group_index)
        if not eligible.loc[idx].iloc[0]:
            continue
        values = rate.loc[idx]
        if method == "percentile":
            # Rank within the account, scaled to [0, 1]. Robust to the heavy
            # right tail that raw engagement rates always have.
            normalized = values.rank(pct=True)
        else:  # zscore
            std = values.std(ddof=0)
            if std == 0 or np.isnan(std):
                normalized = pd.Series(0.0, index=idx)
            else:
                normalized = (values - values.mean()) / std
        relative.loc[idx] = normalized

    return relative, eligible


def relative_target(
    df: pd.DataFrame,
    *,
    account_col: str | None = "account_id",
    rate_col: str | None = None,
    likes_col: str = "likes",
    comments_col: str = "comments",
    shares_col: str = "shares",
    impressions_col: str = "impressions",
    method: str = "percentile",
    min_posts: int = 5,
) -> pd.DataFrame:
    """Attach a content-relative engagement target to a copy of `df`.

    Adds three columns:
      engagement_rate    interactions / impressions (level 1)
      target             the value a model should be trained on
      target_is_relative True where `target` is within-account normalized,
                         False where it fell back to the raw rate

    Pass `rate_col` if the frame already carries a computed rate (the rich
    corpus does, as `engagement_rate`); otherwise the rate is built from the
    like/comment/share/impression columns.
    """
    if method not in {"percentile", "zscore"}:
        raise ValueError(f"Unknown method: {method!r}")

    out = df.copy().reset_index(drop=True)

    if rate_col and rate_col in out.columns:
        rate = pd.to_numeric(out[rate_col], errors="coerce").fillna(0.0)
        rate = rate.clip(lower=0.0).reset_index(drop=True)
    else:
        rate = engagement_rate(
            out.get(likes_col, 0),
            out.get(comments_col, 0),
            out.get(shares_col, 0),
            out.get(impressions_col, 0),
        )
    out["engagement_rate"] = rate

    has_accounts = (
        account_col is not None
        and account_col in out.columns
        and out[account_col].notna().any()
    )

    if not has_accounts:
        # No per-account history at all: the raw rate is the best available
        # target. This is the honest cold-start case.
        out["target"] = rate
        out["target_is_relative"] = False
        return out

    relative, _ = _account_relative(
        rate, out[account_col], method=method, min_posts=min_posts
    )
    out["target_is_relative"] = relative.notna()
    # Backfill the small-account rows with the raw rate so no row is dropped.
    out["target"] = relative.where(relative.notna(), rate)
    return out


def account_baseline(
    df: pd.DataFrame,
    account_col: str = "account_id",
    rate_col: str = "engagement_rate",
) -> pd.DataFrame:
    """Per-account summary of the raw engagement rate.

    Useful both as an account-level feature (a strong prior: accounts that
    engage well keep engaging well) and for reporting how much history each
    account has before its relative target is trusted.
    """
    if account_col not in df.columns:
        return pd.DataFrame(
            columns=[account_col, "n_posts", "baseline_rate", "rate_std"]
        )
    grouped = df.groupby(account_col)[rate_col]
    return (
        pd.DataFrame(
            {
                "n_posts": grouped.size(),
                "baseline_rate": grouped.mean(),
                "rate_std": grouped.std(ddof=0).fillna(0.0),
            }
        )
        .reset_index()
        .sort_values("n_posts", ascending=False)
    )
