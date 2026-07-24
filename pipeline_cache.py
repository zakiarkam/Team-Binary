"""
Pipeline cache manager.

Instead of only checking whether an output file exists,
this module checks whether the INPUT of each stage has changed.

If the input hash changes:

    crawl
        ↓
    kb
        ↓
    summary
        ↓
    generate
        ↓
    evaluation
        ↓
    optimization

all downstream stages become invalid automatically.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import config


# ---------------------------------------------------------
# cache directory
# ---------------------------------------------------------

CACHE_DIR = config.DATA / "cache"

CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# stage metadata path
# ---------------------------------------------------------

def metadata_path(stage: str) -> Path:
    """
    Return metadata file for one stage.

    Example

    data/cache/crawl.json
    data/cache/kb.json
    """
    return CACHE_DIR / f"{stage}.json"


# ---------------------------------------------------------
# SHA256
# ---------------------------------------------------------

def sha256_object(obj) -> str:
    """
    Hash any Python object.

    Dictionaries are sorted so ordering
    never changes the hash.
    """

    text = json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()

def calculate_hash(obj, fields=None) -> str:
    """
    Calculate SHA256 hash.

    Parameters
    ----------
    obj:
        Input dictionary/object.

    fields:
        Optional list of keys to include in hash.

    Used by main.py:
        pipeline_cache.calculate_hash(
            module_input,
            config.PIPELINE_HASH_FIELDS
        )
    """

    if fields and isinstance(obj, dict):

        filtered = {
            key: obj.get(key)
            for key in fields
        }

        return sha256_object(filtered)

    return sha256_object(obj)

def compute_hash(obj) -> str:
    """
    Backward-compatible hash function.

    Used by stage modules like crawler.py.
    """

    return sha256_object(obj)

# =========================================================
# GLOBAL PIPELINE METADATA
# =========================================================

def load_hash(metadata_file: Path):
    """
    Load saved pipeline input hash.
    """

    if not metadata_file.exists():
        return None

    with open(
        metadata_file,
        encoding="utf-8",
    ) as f:

        metadata = json.load(f)

    return metadata.get("hash")


def save_hash(
    metadata_file: Path,
    current_hash: str,
):
    """
    Save current pipeline hash.
    """

    metadata_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        metadata_file,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            {
                "hash": current_hash
            },
            f,
            indent=4,
        )


def clear_metadata(
    metadata_file: Path,
):
    """
    Remove pipeline metadata.
    """

    if metadata_file.exists():
        metadata_file.unlink()

# ---------------------------------------------------------
# save metadata
# ---------------------------------------------------------

def save_stage_hash(stage: str, input_object) -> None:
    """
    Save the latest input hash for one stage.
    """

    path = metadata_path(stage)

    metadata = {
        "hash": sha256_object(input_object)
    }

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=4,
            ensure_ascii=False,
        )


# ---------------------------------------------------------
# compare metadata
# ---------------------------------------------------------

def stage_changed(stage: str, input_object) -> bool:
    """
    Return True if stage input has changed.

    Missing metadata
        -> changed

    Different hash
        -> changed

    Same hash
        -> unchanged
    """

    path = metadata_path(stage)

    current_hash = sha256_object(
        input_object
    )

    if not path.exists():
        return True

    with open(
        path,
        encoding="utf-8",
    ) as file:

        metadata = json.load(file)

    previous_hash = metadata.get("hash")

    return previous_hash != current_hash


# ---------------------------------------------------------
# delete metadata
# ---------------------------------------------------------

def delete_stage_metadata(stage: str) -> None:
    """
    Remove one metadata file.
    """

    path = metadata_path(stage)

    if path.exists():
        path.unlink()

def save_stage_metadata(metadata_file, metadata):
    """
    Save arbitrary pipeline metadata.
    """

    metadata_file.parent.mkdir(parents=True, exist_ok=True)

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(
            metadata,
            f,
            indent=4,
            ensure_ascii=False,
        )

# ---------------------------------------------------------
# invalidate downstream stages
# ---------------------------------------------------------

DOWNSTREAM = {

    "crawl": [
        "kb",
        "goal-tone-predict",
        "summary",
        "generate",
        "engagement-score",
        "evaluate",
        "optimize",
    ],

    "kb": [
        "goal-tone-predict",
        "summary",
        "generate",
        "engagement-score",
        "evaluate",
        "optimize",
    ],

    "goal-tone-predict": [
        "summary",
        "generate",
        "engagement-score",
        "evaluate",
        "optimize",
    ],

    "summary": [
        "generate",
        "engagement-score",
        "evaluate",
        "optimize",
    ],

    "generate": [
        "engagement-score",
        "evaluate",
        "optimize",
    ],

    "engagement-score": [
        "evaluate",
        "optimize",
    ],

    "evaluate": [
        "optimize",
    ],
}


OUTPUTS = {

    "crawl": config.CRAWL_JSON,

    "kb": config.KB_JSON,

    "summary": config.SUMMARY_JSON,

    "generate": config.GENERATED_CSV,

    "evaluate": config.RANKED_CSV,

    "optimize": [
        config.OPTIMIZED_CSV,
        config.OPTIMIZED_RANKED_CSV,
        config.COMPARISON_CSV,
    ],

    "engagement-score": config.GENERATED_CSV
}


def _delete_output(output):
    """
    Delete one output or a list of outputs.
    """

    if output is None:
        return

    if isinstance(output, (list, tuple)):

        for item in output:

            if item.exists():
                item.unlink()

    else:

        if output.exists():
            output.unlink()


def invalidate(stage: str, visited=None):
    """
    Recursively invalidate every downstream stage.
    """

    if visited is None:
        visited = set()

    if stage in visited:
        return

    visited.add(stage)

    for child in DOWNSTREAM.get(stage, []):

        _delete_output(
            OUTPUTS.get(child)
        )

        delete_stage_metadata(child)

        invalidate(
            child,
            visited,
        )

# ---------------------------------------------------------
# update cache
# ---------------------------------------------------------

def update(stage: str, input_object) -> None:
    """
    Save new metadata after a stage finishes successfully.
    """

    save_stage_hash(
        stage,
        input_object,
    )


# ---------------------------------------------------------
# helper
# ---------------------------------------------------------

def should_run(stage: str, input_object) -> bool:
    """
    Decide whether a stage should run.

    True
        run stage

    False
        reuse cache
    """

    return stage_changed(
        stage,
        input_object,
    )