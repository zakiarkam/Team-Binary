"""Import platform Insights CSV exports into the feedback store.

This is the realistic data path for a research project: Instagram, LinkedIn and
Meta all let a business export a post-level analytics CSV, and reading analytics
needs none of the app-review bureaucracy that *posting* does. The user posts
manually, exports the CSV, drops it in `data/feedback/analytics_import/`, and
this maps its columns onto the store's canonical actuals.

Column names differ per platform and per export version, so mapping is
data-driven: each known layout is a dict from canonical name → list of accepted
source headers (case-insensitive). An unknown export is handled by the generic
map, and anything still unmapped is reported rather than silently dropped.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import config
from learning import feedback_store

# canonical -> accepted source headers (lowercased). First hit wins.
_COLUMN_MAPS: dict[str, dict[str, list[str]]] = {
    "instagram": {
        "external_post_id": ["post id", "media id", "id", "permalink"],
        "caption": ["caption", "description", "post caption"],
        "actual_likes": ["likes", "like count"],
        "actual_comments": ["comments", "comment count"],
        "actual_shares": ["shares", "share count"],
        "actual_impressions": ["impressions", "views"],
        "actual_reach": ["reach", "accounts reached"],
        "actual_clicks": ["website clicks", "link clicks", "clicks"],
    },
    "linkedin": {
        "external_post_id": ["post url", "share url", "update url", "id"],
        "caption": ["post title", "text", "commentary", "caption"],
        "actual_likes": ["likes", "reactions"],
        "actual_comments": ["comments"],
        "actual_shares": ["reposts", "shares"],
        "actual_impressions": ["impressions"],
        "actual_reach": ["unique impressions", "reach"],
        "actual_clicks": ["clicks"],
    },
    "generic": {
        "external_post_id": ["post_id", "post id", "id", "url", "post url"],
        "caption": ["caption", "text", "text_content", "post text", "message"],
        "actual_likes": ["likes", "likes_count", "num_likes", "reactions"],
        "actual_comments": ["comments", "comments_count", "num_comments"],
        "actual_shares": ["shares", "shares_count", "reposts", "retweets"],
        "actual_impressions": ["impressions", "views", "views_count"],
        "actual_reach": ["reach", "unique impressions"],
        "actual_clicks": ["clicks", "link clicks"],
    },
}


def _resolve(columns: list[str], layout: dict[str, list[str]]) -> dict[str, str]:
    """Map canonical names to the actual header present in this file."""
    lower = {c.lower().strip(): c for c in columns}
    resolved = {}
    for canonical, candidates in layout.items():
        for candidate in candidates:
            if candidate in lower:
                resolved[canonical] = lower[candidate]
                break
    return resolved


def _detect_platform(path: Path, columns: list[str]) -> str:
    name = path.name.lower()
    for platform in ("instagram", "linkedin"):
        if platform in name:
            return platform
    lower = {c.lower() for c in columns}
    if {"reactions", "reposts"} & lower:
        return "linkedin"
    return "generic"


def import_csv(
    path: str | Path,
    *,
    account_id: str | None = None,
    platform: str | None = None,
    db_path: Path | None = None,
) -> dict:
    """Ingest one analytics CSV. Returns a small report dict."""
    path = Path(path)
    frame = pd.read_csv(path)
    columns = list(frame.columns)

    layout_name = platform or _detect_platform(path, columns)
    layout = _COLUMN_MAPS.get(layout_name, _COLUMN_MAPS["generic"])
    resolved = _resolve(columns, layout)

    if "actual_likes" not in resolved and "actual_impressions" not in resolved:
        return {
            "file": path.name, "platform": layout_name, "rows": 0,
            "matched": 0, "inserted": 0,
            "error": "No engagement columns recognised. Pass platform= or add "
                     "the layout to _COLUMN_MAPS.",
            "columns_seen": columns,
        }

    updates = []
    for _, row in frame.iterrows():
        update = {"platform": layout_name if layout_name != "generic" else platform}
        if account_id:
            update["account_id"] = account_id
        for canonical, source in resolved.items():
            value = row.get(source)
            if pd.notna(value):
                update[canonical] = value
        # Numeric coercion for the metric columns.
        for metric in ("actual_likes", "actual_comments", "actual_shares",
                       "actual_impressions", "actual_reach", "actual_clicks"):
            if metric in update:
                update[metric] = pd.to_numeric(update[metric], errors="coerce")
        updates.append(update)

    matched, inserted = feedback_store.update_actuals(updates, db_path=db_path)
    return {
        "file": path.name, "platform": layout_name, "rows": len(updates),
        "matched": matched, "inserted": inserted,
        "mapped_columns": resolved,
    }


def import_dir(
    directory: str | Path | None = None,
    *,
    account_id: str | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    """Import every CSV in a directory. Returns one report per file."""
    directory = Path(directory or config.ANALYTICS_IMPORT_DIR)
    if not directory.exists():
        return []
    reports = []
    for csv_path in sorted(directory.glob("*.csv")):
        reports.append(
            import_csv(csv_path, account_id=account_id, db_path=db_path)
        )
    return reports
