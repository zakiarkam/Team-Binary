"""SQLite-backed feedback store.

The store is the seam that lets the system learn without posting. It records
every generated asset together with the score the model predicted for it, and
holds a set of nullable "actual" columns that stay empty until real analytics
arrive (via an Insights CSV import, or an API sync later). Once actuals exist,
the retrain stage reads them back out as training rows.

Nothing here depends on torch, transformers, or the generation stack, so it is
cheap to import and to unit-test.

Two ways an asset acquires actuals later:
  - by `external_post_id` — the platform's own post id, if the user records it;
  - by normalized caption text — a pragmatic fallback when they don't, since the
    caption the user posted is the caption we generated.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import config

# Columns filled at generation time.
_PREDICTION_COLUMNS = [
    "account_id", "platform", "caption", "hashtags", "cta",
    "image_prompt", "shorts_prompt", "campaign_goal", "tone",
    "predicted_engagement", "predicted_engagement_score",
    "semantic_score", "platform_suitability_score", "final_score",
    "source", "external_post_id",
]

# Columns filled later, when analytics are observed. All nullable.
_ACTUAL_COLUMNS = [
    "actual_likes", "actual_comments", "actual_shares",
    "actual_impressions", "actual_reach", "actual_clicks",
    "actual_engagement_rate", "actuals_updated_at",
]

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS posts (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at                  TEXT NOT NULL,
    account_id                  TEXT,
    platform                    TEXT,
    caption                     TEXT,
    caption_key                 TEXT,
    hashtags                    TEXT,
    cta                         TEXT,
    image_prompt                TEXT,
    shorts_prompt               TEXT,
    campaign_goal               TEXT,
    tone                        TEXT,
    predicted_engagement        REAL,
    predicted_engagement_score  REAL,
    semantic_score              REAL,
    platform_suitability_score  REAL,
    final_score                 REAL,
    source                      TEXT,
    external_post_id            TEXT,
    actual_likes                REAL,
    actual_comments             REAL,
    actual_shares               REAL,
    actual_impressions          REAL,
    actual_reach                REAL,
    actual_clicks               REAL,
    actual_engagement_rate      REAL,
    actuals_updated_at          TEXT
);
CREATE INDEX IF NOT EXISTS idx_posts_caption_key ON posts (caption_key);
CREATE INDEX IF NOT EXISTS idx_posts_external ON posts (platform, external_post_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def caption_key(text) -> str:
    """Normalized caption for fuzzy matching: lowercase, alnum-only, collapsed."""
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


@contextmanager
def _connect(db_path: Path | None = None):
    path = Path(db_path or config.FEEDBACK_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def init(db_path: Path | None = None) -> None:
    """Create the store if it does not exist. Idempotent."""
    with _connect(db_path):
        pass


def log_assets(
    assets: pd.DataFrame,
    *,
    account_id: str | None = None,
    source: str = "generated",
    db_path: Path | None = None,
) -> int:
    """Record generated assets and their predictions. Returns rows written.

    `assets` is a scored asset frame (the output of evaluate/optimize). Any
    prediction column that is absent is stored as NULL, so this accepts both a
    freshly generated frame and a fully scored one.
    """
    if assets is None or assets.empty:
        return 0

    rows = []
    for _, asset in assets.iterrows():
        record = {col: None for col in _PREDICTION_COLUMNS}
        for col in _PREDICTION_COLUMNS:
            if col in assets.columns and _present(asset.get(col)):
                record[col] = asset[col]
        record["account_id"] = account_id or record.get("account_id")
        record["source"] = source
        record["created_at"] = _now()
        record["caption_key"] = caption_key(record.get("caption", ""))
        # Coerce list-valued hashtags to a stable string form.
        if isinstance(record.get("hashtags"), (list, tuple)):
            record["hashtags"] = " ".join(str(h) for h in record["hashtags"])
        rows.append(record)

    columns = ["created_at", "caption_key", *_PREDICTION_COLUMNS]
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO posts ({', '.join(columns)}) VALUES ({placeholders})"

    with _connect(db_path) as conn:
        conn.executemany(
            sql,
            [tuple(_coerce(r.get(c)) for c in columns) for r in rows],
        )
    return len(rows)


def _present(value) -> bool:
    """True if a cell holds real content. Handles list/array cells, which
    pd.notna would reduce to an ambiguous boolean array."""
    if value is None:
        return False
    if isinstance(value, (list, tuple)):
        return len(value) > 0
    try:
        return bool(pd.notna(value))
    except (TypeError, ValueError):
        return True


def _coerce(value):
    """SQLite accepts str/int/float/None; stringify anything else."""
    if value is None or isinstance(value, (str, int, float)):
        return value
    return str(value)


def update_actuals(
    updates: list[dict],
    *,
    db_path: Path | None = None,
) -> tuple[int, int]:
    """Attach observed analytics to existing posts.

    Each update dict carries the metric columns plus one of:
      external_post_id (+ platform), or caption (matched via caption_key).

    Returns (matched, unmatched). Unmatched updates that carry their own caption
    text are inserted as standalone historical training rows, so a business's
    back-catalogue of past posts is not lost just because we never generated it.
    """
    matched = 0
    unmatched_rows = []

    with _connect(db_path) as conn:
        for update in updates:
            metrics = {k: update.get(k) for k in _ACTUAL_COLUMNS if k in update}
            metrics["actuals_updated_at"] = _now()
            if update.get("actual_engagement_rate") is None:
                metrics["actual_engagement_rate"] = _rate_from(update)

            row_id = _find_post(conn, update)
            if row_id is not None:
                assignments = ", ".join(f"{k} = ?" for k in metrics)
                conn.execute(
                    f"UPDATE posts SET {assignments} WHERE id = ?",
                    (*[_coerce(v) for v in metrics.values()], row_id),
                )
                matched += 1
            elif update.get("caption"):
                unmatched_rows.append(update)

    inserted = _insert_history(unmatched_rows, db_path=db_path)
    return matched, inserted


def _rate_from(update: dict) -> float | None:
    imp = update.get("actual_impressions") or update.get("actual_reach")
    if not imp:
        return None
    interactions = sum(
        float(update.get(k) or 0)
        for k in ("actual_likes", "actual_comments", "actual_shares")
    )
    try:
        return interactions / float(imp) if float(imp) > 0 else None
    except (TypeError, ValueError):
        return None


def _find_post(conn, update: dict) -> int | None:
    ext = update.get("external_post_id")
    platform = update.get("platform")
    if ext:
        row = conn.execute(
            "SELECT id FROM posts WHERE external_post_id = ? "
            "AND (? IS NULL OR platform = ?) AND actual_engagement_rate IS NULL "
            "ORDER BY id LIMIT 1",
            (str(ext), platform, platform),
        ).fetchone()
        if row:
            return row["id"]
    if update.get("caption"):
        row = conn.execute(
            "SELECT id FROM posts WHERE caption_key = ? "
            "AND actual_engagement_rate IS NULL ORDER BY id LIMIT 1",
            (caption_key(update["caption"]),),
        ).fetchone()
        if row:
            return row["id"]
    return None


def _insert_history(updates: list[dict], *, db_path: Path | None = None) -> int:
    """Insert analytics rows that matched no generated post as history rows."""
    if not updates:
        return 0
    rows = []
    for update in updates:
        record = {col: None for col in _PREDICTION_COLUMNS}
        record.update({k: update.get(k) for k in _PREDICTION_COLUMNS if k in update})
        record["source"] = "imported"
        record["created_at"] = _now()
        record["caption_key"] = caption_key(update.get("caption", ""))
        for col in _ACTUAL_COLUMNS:
            record[col] = update.get(col)
        record["actuals_updated_at"] = _now()
        if record.get("actual_engagement_rate") is None:
            record["actual_engagement_rate"] = _rate_from(update)
        rows.append(record)

    columns = ["created_at", "caption_key", *_PREDICTION_COLUMNS, *_ACTUAL_COLUMNS]
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO posts ({', '.join(columns)}) VALUES ({placeholders})"
    with _connect(db_path) as conn:
        conn.executemany(
            sql, [tuple(_coerce(r.get(c)) for c in columns) for r in rows]
        )
    return len(rows)


def load_all(db_path: Path | None = None) -> pd.DataFrame:
    with _connect(db_path) as conn:
        return pd.read_sql_query("SELECT * FROM posts ORDER BY id", conn)


def load_labeled(db_path: Path | None = None) -> pd.DataFrame:
    """Rows that have an observed engagement rate — i.e. usable as training data."""
    with _connect(db_path) as conn:
        return pd.read_sql_query(
            "SELECT * FROM posts WHERE actual_engagement_rate IS NOT NULL "
            "ORDER BY id",
            conn,
        )


def summary(db_path: Path | None = None) -> dict:
    with _connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM posts").fetchone()["n"]
        labeled = conn.execute(
            "SELECT COUNT(*) AS n FROM posts WHERE actual_engagement_rate IS NOT NULL"
        ).fetchone()["n"]
        accounts = conn.execute(
            "SELECT COUNT(DISTINCT account_id) AS n FROM posts "
            "WHERE account_id IS NOT NULL"
        ).fetchone()["n"]
    return {"total_posts": total, "with_actuals": labeled, "accounts": accounts}
