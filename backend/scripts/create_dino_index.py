"""
JewelMatch AI

DINOv2 Catalogue Index

This script supports:

1. Manual full index rebuild.
2. Background incremental batch processing.

The background queue calls create_index_for_items(item_ids), which now
creates DINO embeddings only for the supplied catalogue IDs and updates
the existing dino_index.npz.
"""

from pathlib import Path

from backend.services.matcher import (
    build_index,
    build_incremental_index,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

BATCH_SIZE = 50


# ============================================================
# FULL INDEX BUILD
# ============================================================


def build_full_index():
    """
    Build the complete DINO catalogue index.

    This is used for the manual "Rebuild Search Index" action and
    for the command-line full rebuild.
    """

    print()
    print("=" * 70)
    print("JEWELMATCH AI - DINO CATALOGUE INDEX")
    print("=" * 70)
    print()
    print("[DINO] Starting full catalogue index build...")
    print()

    try:
        result = build_index(
            force=True,
        )
    except Exception as exc:
        print()
        print("=" * 70)
        print("INDEX BUILD FAILED")
        print("=" * 70)
        print()
        print(f"Error: {exc}")
        print()
        raise

    if not result:
        print()
        print("=" * 70)
        print("INDEX BUILD FAILED")
        print("=" * 70)
        print()
        return None

    collections = result.get(
        "collections",
        [],
    )

    gold_count = sum(
        1
        for collection in collections
        if str(collection).lower() == "gold"
    )

    prototype_count = sum(
        1
        for collection in collections
        if str(collection).lower() == "prototype"
    )

    total_count = len(collections)

    embeddings = result.get(
        "embeddings"
    )

    if embeddings is not None:
        embedding_dimension = (
            embeddings.shape[1]
            if len(embeddings.shape) > 1
            else 0
        )
    else:
        embedding_dimension = 0

    errors = result.get(
        "errors",
        [],
    )

    index_file = result.get(
        "index_file",
        "database/dino_index.npz",
    )

    print()
    print("=" * 70)
    print("DINOv2-BASE INDEX CREATED")
    print("=" * 70)
    print(f"Total indexed : {total_count}")
    print(f"Gold indexed  : {gold_count}")
    print(f"Prototype     : {prototype_count}")
    print(f"Embedding dim : {embedding_dimension}")
    print(f"Errors        : {len(errors)}")
    print(f"Index file    : {index_file}")
    print("=" * 70)
    print()
    print("=" * 70)
    print("INDEX BUILD COMPLETE")
    print("=" * 70)
    print()

    return result


# ============================================================
# BACKGROUND BATCH ENTRY POINT
# ============================================================


def create_index_for_items(item_ids):
    """
    Process only the supplied catalogue IDs.

    The function does NOT rebuild the complete catalogue. It calculates
    DINO embeddings for the requested items and updates the existing
    index atomically.
    """

    if not item_ids:
        print("[DINO QUEUE] No items to process.")
        return None

    item_ids = [
        str(item_id).strip()
        for item_id in item_ids
        if str(item_id).strip()
    ]

    if not item_ids:
        print("[DINO QUEUE] No valid item IDs to process.")
        return None

    print()
    print("=" * 70)
    print("JEWELMATCH AI - BACKGROUND DINO PROCESSING")
    print("=" * 70)
    print()
    print(f"[DINO QUEUE] Requested items: {len(item_ids)}")
    print("[DINO QUEUE] Item IDs:")

    for item_id in item_ids:
        print(f"  - {item_id}")

    print()
    print("[DINO QUEUE] Running incremental index update...")
    print()

    result = build_incremental_index(
        item_ids
    )

    print()

    if result and result.get("success"):
        print(
            "[DINO QUEUE] Background incremental processing complete."
        )
    else:
        print(
            "[DINO QUEUE] Background processing completed with errors."
        )

    print()

    return result


# ============================================================
# COMMAND LINE
# ============================================================


def main():
    build_full_index()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
