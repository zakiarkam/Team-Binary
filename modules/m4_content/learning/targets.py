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


def leave_one_out_baseline(
    df: pd.DataFrame,
    account_col: str = "account_id",
    rate_col: str = "engagement_rate",
) -> pd.Series:
    """Each row's account baseline, computed WITHOUT that row's own rate.

    An account's mean rate is a *target-derived aggregate*, so using it as a
    training feature leaks. It is not a subtle leak either: where an account has
    a single post its mean IS that post's rate, and `relative_target` falls back
    to the raw rate for exactly those accounts — so feature and target become the
    same number. Measured on this project's base corpus (`Social Media Engagement
    Dataset.csv`, 12,000 accounts with one post each) the correlation was 1.000
    on 100% of rows, and a RandomForest scored R² = 0.995 / Spearman = 1.000 with
    the feature against R² = -0.172 / Spearman = 0.010 without it. That is the
    same failure the base engagement model was already fixed for, in the same
    module, so it is fixed the same way: the aggregate never sees its own row.

    A row whose account has no *other* post has no usable baseline, so it falls
    back to the **plain global mean — a constant**. Note that the leave-one-out
    global mean, (total - rate_i) / (n - 1), would be the wrong choice here and
    is a leak in its own right: it is a strictly decreasing function of the row's
    own rate, so it correlates -1.000 with the target instead of +1.000. A
    constant is the only fallback that genuinely says "nothing is known about
    this account", and a constant column cannot carry information at all.

    This is for TRAINING. At prediction time there is no target to leak, so the
    full account mean from `account_baseline` is the right value to serve.
    """
    frame = df.reset_index(drop=True)
    rate = pd.to_numeric(frame[rate_col], errors="coerce").fillna(0.0)

    global_mean = float(rate.mean()) if len(rate) else 0.0

    if account_col not in frame.columns:
        return pd.Series(global_mean, index=rate.index, dtype="float64")

    account = frame[account_col].fillna("__unknown__").astype(str)
    group_sum = account.map(rate.groupby(account).sum())
    group_n = account.map(account.value_counts())

    # NaN denominator where the account has a single post, so no divide-by-zero
    # warning and no inf; those rows take the constant global mean below.
    loo = (group_sum - rate) / (group_n - 1).where(group_n > 1)
    return loo.where(group_n > 1, global_mean).astype("float64")


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
