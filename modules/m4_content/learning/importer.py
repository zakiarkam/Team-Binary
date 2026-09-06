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

# canonical -> accepted source headers (lowercased). First hit wins, so the
# most specific alias for a platform is listed before the generic one.
#
# ⚠ These aliases are NOT verified against real export files or platform
# documentation. They are best-effort guesses at each platform's post-level
# export headers, and export schemas change without notice — Instagram renamed
# "Impressions" to "Views", Meta has restructured Business Suite exports more
# than once, and TikTok's columns differ by account type.
#
# So do not treat this dict as a specification. Treat it as a starting set that
# will be wrong for some real file. What makes that safe is the *reporting*:
# `import_csv` returns `mapped_columns` and `unmapped_columns`, and refuses the
# file outright rather than importing nothing quietly when the columns it needs
# are absent. Run `inspect_csv()` on a real export first, read what resolved,
# and add the missing alias here — that is a one-line change and the only
# supported way to onboard a new export layout.
_COLUMN_MAPS: dict[str, dict[str, list[str]]] = {
    "instagram": {
        "external_post_id": ["post id", "media id", "id", "permalink"],
        "caption": ["description", "caption", "post caption", "title"],
        "actual_likes": ["likes", "like count"],
        "actual_comments": ["comments", "comment count"],
        "actual_shares": ["shares", "share count"],
        "actual_impressions": ["impressions", "views", "plays"],
        "actual_reach": ["reach", "accounts reached", "accounts center accounts reached"],
        "actual_clicks": ["website clicks", "link clicks", "clicks", "profile visits"],
    },
    "facebook": {
        # Meta exports "Reactions" where the store means likes, and carries both
        # Title and Description — Description holds the post copy.
        "external_post_id": ["post id", "permalink", "id"],
        "caption": ["description", "message", "caption", "title"],
        "actual_likes": ["reactions", "likes"],
        "actual_comments": ["comments"],
        "actual_shares": ["shares"],
        "actual_impressions": ["impressions", "views"],
        "actual_reach": ["reach", "people reached"],
        "actual_clicks": ["link clicks", "post clicks", "clicks"],
    },
    "linkedin": {
        # The export header is "Post link", not "Post URL" — matching the latter
        # silently cost every row its exact identifier and fell back to caption
        # text matching, which is heuristic.
        "external_post_id": ["post link", "post url", "share url", "update url", "id"],
        "caption": ["post title", "text", "commentary", "caption"],
        "actual_likes": ["likes", "reactions"],
        "actual_comments": ["comments"],
        "actual_shares": ["reposts", "shares"],
        "actual_impressions": ["impressions"],
        "actual_reach": ["unique impressions", "reach"],
        "actual_clicks": ["clicks"],
    },
    "tiktok": {
        "external_post_id": ["video link", "video id", "post id", "id"],
        "caption": ["video title", "caption", "description", "title"],
        "actual_likes": ["likes"],
        "actual_comments": ["comments"],
        "actual_shares": ["shares"],
        "actual_impressions": ["video views", "views", "total views"],
        "actual_reach": ["reach", "unique viewers"],
        "actual_clicks": ["clicks", "link clicks", "profile visits"],
    },
    "youtube": {
        # Studio writes the video id into a column literally called "Content",
        # and pluralises the comment column as "Comments added".
        "external_post_id": ["content", "video id", "video", "id"],
        "caption": ["video title", "title", "caption"],
        "actual_likes": ["likes"],
        "actual_comments": ["comments added", "comments"],
        "actual_shares": ["shares"],
        "actual_impressions": ["impressions", "views"],
        "actual_reach": ["unique viewers", "reach"],
        "actual_clicks": ["clicks"],
    },
    "email": {
        # Email has no likes. Opens are the nearest positive interaction and
        # delivered is the denominator, so the derived engagement rate reads as
        # an OPEN rate — which this project's own finding says under-reports,
        # because most clients block the pixel. Click-through is the column to
        # trust; it is preserved exactly as actual_clicks.
        "external_post_id": ["external_campaign_id", "campaign id", "campaign_id",
                             "id"],
        "caption": ["subject_and_body", "subject line", "subject", "title",
                    "content", "caption"],
        "actual_likes": ["unique opens", "opens", "opened"],
        "actual_comments": ["replies"],
        "actual_shares": ["forwards"],
        "actual_impressions": ["delivered", "sent", "recipients"],
        "actual_reach": ["unique recipients"],
        "actual_clicks": ["unique clicks", "clicks", "clicked"],
    },
    "generic": {
        "external_post_id": ["post_id", "post id", "id", "url", "post url",
                             "post link", "permalink", "video link"],
        "caption": ["caption", "text", "text_content", "post text", "message",
                    "description", "video title", "post title", "title"],
        "actual_likes": ["likes", "likes_count", "num_likes", "reactions"],
        "actual_comments": ["comments", "comments_count", "num_comments",
                            "comments added"],
        "actual_shares": ["shares", "shares_count", "reposts", "retweets"],
        "actual_impressions": ["impressions", "video views", "views",
                               "views_count"],
        "actual_reach": ["reach", "unique impressions"],
        "actual_clicks": ["clicks", "link clicks"],
    },
}

#: Headers that identify a platform when the filename does not. Checked in this
#: order, most distinctive first — Meta and LinkedIn both write "Reactions", so
#: detection must key on something only one of them has ("Page ID" against
#: "Reposts") rather than on the shared column.
_PLATFORM_SIGNALS: tuple[tuple[str, frozenset[str]], ...] = (
    ("tiktok", frozenset({"video views", "total time watched",
                          "average time watched", "new followers"})),
    ("youtube", frozenset({"watch time (hours)", "comments added",
                           "impressions click-through rate"})),
    ("email", frozenset({"subject_and_body", "unsubscribes", "delivered",
                         "unique opens"})),
    ("facebook", frozenset({"page id", "post clicks", "people reached"})),
    ("linkedin", frozenset({"reposts", "click through rate (ctr)",
                            "published by"})),
    ("instagram", frozenset({"accounts reached", "saves", "account username"})),
)


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
    """Which layout to apply, from the filename first and the headers second.

    Filename wins because it is what a user controls; header signatures are the
    fallback for a renamed file. Both must be specific: reading Meta's
    "Reactions" as LinkedIn was measurably wrong, and cost every Facebook row
    its caption because LinkedIn's caption aliases do not include "Description".
    """
    name = path.name.lower()
    for platform in _COLUMN_MAPS:
        if platform != "generic" and platform in name:
            return platform

    lower = {c.lower().strip() for c in columns}
    for platform, signals in _PLATFORM_SIGNALS:
        if signals & lower:
            return platform
    return "generic"


#: Canonical fields, and whether the store can work without each one.
_REQUIRED = ("caption", "actual_likes", "actual_impressions")
_OPTIONAL = ("external_post_id", "actual_comments", "actual_shares",
             "actual_reach", "actual_clicks")


def inspect_csv(path: str | Path, *, platform: str | None = None) -> dict:
    """Dry run: what WOULD map, without touching the store.

    The aliases in `_COLUMN_MAPS` are unverified guesses at each platform's real
    export headers, so the supported workflow for a new export is to run this
    first. It reads only the header row, so it is instant on a large file and
    cannot modify anything.

        from learning import importer
        print(importer.inspect_csv("data/feedback/analytics_import/my.csv"))

    Read `unmapped_columns`, add the missing header to the right alias list in
    `_COLUMN_MAPS`, and re-run. No editing of the CSV itself is ever required.
    """
    path = Path(path)
    columns = list(pd.read_csv(path, nrows=0).columns)
    layout_name = platform or _detect_platform(path, columns)
    resolved = _resolve(columns, _COLUMN_MAPS.get(layout_name,
                                                  _COLUMN_MAPS["generic"]))

    missing_required = [f for f in _REQUIRED if f not in resolved]
    return {
        "file": path.name,
        "detected_platform": layout_name,
        "would_import": not missing_required,
        "mapped": {canonical: resolved[canonical]
                   for canonical in (*_REQUIRED, *_OPTIONAL)
                   if canonical in resolved},
        "missing_required": missing_required,
        "missing_optional": [f for f in _OPTIONAL if f not in resolved],
        "unmapped_columns": [c for c in columns if c not in resolved.values()],
        "hint": "" if not missing_required else (
            f"Add the header that carries {missing_required[0]} to "
            f"_COLUMN_MAPS['{layout_name}']['{missing_required[0]}']."
        ),
    }


def inspect_dir(directory: str | Path | None = None) -> list[dict]:
    """Dry-run every CSV in the import directory."""
    directory = Path(directory or config.ANALYTICS_IMPORT_DIR)
    if not directory.exists():
        return []
    return [inspect_csv(p) for p in sorted(directory.glob("*.csv"))]


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

    # A row survives only if it matches an existing post by id or carries its own
    # caption text (feedback_store.update_actuals drops the rest). With neither
    # column resolved every row is discarded, and the old code reported that as
    # a clean `inserted: 0` — a successful-looking import of nothing.
    if "caption" not in resolved and "external_post_id" not in resolved:
        return {
            "file": path.name, "platform": layout_name, "rows": 0,
            "matched": 0, "inserted": 0,
            "error": "Recognised engagement columns but no caption or post-id "
                     "column, so every row would be discarded. Pass platform= "
                     "or add the layout to _COLUMN_MAPS.",
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
    report = {
        "file": path.name, "platform": layout_name, "rows": len(updates),
        "matched": matched, "inserted": inserted,
        "mapped_columns": resolved,
        "unmapped_columns": [c for c in columns if c not in resolved.values()],
    }
    if "caption" not in resolved:
        report["warning"] = (
            "No caption column: rows can update posts we already generated, but "
            "none can be kept as standalone history, so this export contributes "
            "no new training text."
        )
    elif matched == 0 and inserted == 0 and updates:
        report["warning"] = (
            f"{len(updates)} row(s) read but none stored — every row had an "
            "empty caption and matched no existing post."
        )
    return report


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
