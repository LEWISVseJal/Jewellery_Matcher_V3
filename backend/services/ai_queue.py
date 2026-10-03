"""
JewelMatch AI

Background AI processing queue.

Behaviour:
    - Add Jewellery saves immediately with ai_status='pending'.
    - AI processing starts when there are 50 pending items.
    - AI processing also starts when the oldest pending item has waited
      for one hour.
    - Each background run processes at most 50 items.
    - New items added while a batch is running remain pending for the
      next batch.

MongoDB is the live catalogue source.

The DINO index is still stored locally in:
    backend/database/dino_index.npz

The queue status metadata is still stored locally in:
    backend/database/ai_queue_status.json

The jewellery catalogue itself is NOT stored or updated in jewellery.json.
"""

from __future__ import annotations

import json
import threading
import time
import traceback

from datetime import datetime, timezone
from pathlib import Path

from backend.scripts.create_dino_index import (
    create_index_for_items,
)

from backend.database.mongodb import (
    get_jewellery_collection,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parents[1]
)

DATABASE_DIR = (
    BASE_DIR /
    "database"
)

QUEUE_STATUS_FILE = (
    DATABASE_DIR /
    "ai_queue_status.json"
)


# ============================================================
# QUEUE CONFIGURATION
# ============================================================

BATCH_SIZE = 50

MAX_WAIT_SECONDS = (
    60 * 60
)

CHECK_INTERVAL_SECONDS = 15


# ============================================================
# WORKER STATE
# ============================================================

_worker_thread = None

_worker_lock = threading.Lock()

_catalogue_lock = threading.RLock()


# ============================================================
# TIME HELPERS
# ============================================================

def utc_now_iso() -> str:
    """
    Return the current UTC time as an ISO-8601 string.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


def parse_timestamp(
    value: str | None
) -> float | None:
    """
    Convert an ISO timestamp to Unix seconds.
    """

    if not value:
        return None

    try:

        timestamp = (
            str(value)
            .replace(
                "Z",
                "+00:00",
            )
        )

        return (
            datetime
            .fromisoformat(
                timestamp
            )
            .timestamp()
        )

    except Exception:
        return None


# ============================================================
# MONGODB CATALOGUE
# ============================================================

def get_catalogue_collection():
    """
    Return the live MongoDB jewellery collection.
    """

    return (
        get_jewellery_collection()
    )


def load_catalogue() -> list:
    """
    Load the current jewellery catalogue from MongoDB.

    MongoDB is now the single live source of catalogue data.
    """

    try:

        collection = (
            get_catalogue_collection()
        )

        documents = (
            collection
            .find(
                {},
                {
                    "_id": 0
                }
            )
        )

        return list(
            documents
        )

    except Exception as exc:

        print(
            "[AI QUEUE] "
            "Could not load catalogue "
            "from MongoDB:",
            exc,
        )

        traceback.print_exc()

        return []


# ============================================================
# UPDATE MONGODB ITEM
# ============================================================

def update_catalogue_item(
    item_id: str,
    update_fields: dict,
) -> bool:
    """
    Update one jewellery item in MongoDB.
    """

    item_id = str(
        item_id
    ).strip()

    if not item_id:
        return False

    try:

        collection = (
            get_catalogue_collection()
        )

        result = (
            collection
            .update_one(
                {
                    "id": item_id
                },
                {
                    "$set": update_fields
                }
            )
        )

        return (
            result.matched_count > 0
        )

    except Exception as exc:

        print(
            "[AI QUEUE] "
            f"Could not update {item_id}:",
            exc,
        )

        traceback.print_exc()

        return False


# ============================================================
# UPDATE MULTIPLE ITEMS
# ============================================================

def update_catalogue_items(
    item_ids: list[str],
    update_fields: dict,
    error_map: dict[str, str] | None = None,
    status: str | None = None,
) -> None:
    """
    Update multiple jewellery items in MongoDB.

    Status-specific fields are handled here so that the queue
    behaviour remains consistent with the previous implementation.
    """

    target_ids = {
        str(item_id).strip()
        for item_id in item_ids
        if str(item_id).strip()
    }

    if not target_ids:
        return

    error_map = (
        error_map or {}
    )

    now = utc_now_iso()

    collection = (
        get_catalogue_collection()
    )

    for item_id in target_ids:

        fields = dict(
            update_fields
        )

        if status == "pending":

            fields[
                "ai_status"
            ] = "pending"

            fields[
                "ai_queued_at"
            ] = now

            fields.pop(
                "ai_processing_at",
                None,
            )

            fields.pop(
                "ai_processed_at",
                None,
            )

            fields.pop(
                "ai_error",
                None,
            )

        elif status == "processing":

            fields[
                "ai_status"
            ] = "processing"

            fields[
                "ai_processing_at"
            ] = now

            fields.pop(
                "ai_error",
                None,
            )

        elif status == "ready":

            fields[
                "ai_status"
            ] = "ready"

            fields[
                "ai_processed_at"
            ] = now

            fields.pop(
                "ai_processing_at",
                None,
            )

            fields.pop(
                "ai_error",
                None,
            )

        elif status == "failed":

            fields[
                "ai_status"
            ] = "failed"

            fields.pop(
                "ai_processing_at",
                None,
            )

            fields[
                "ai_error"
            ] = error_map.get(
                item_id,
                "AI processing failed.",
            )

        try:

            collection.update_one(
                {
                    "id": item_id
                },
                {
                    "$set": fields
                }
            )

        except Exception as exc:

            print(
                "[AI QUEUE] "
                f"Could not update {item_id}:",
                exc,
            )

            traceback.print_exc()


# ============================================================
# MARK ITEMS STATUS
# ============================================================

def mark_items_status(
    item_ids: list[str],
    status: str,
    error_map: dict[str, str] | None = None,
) -> None:
    """
    Update AI status fields for specific catalogue items.

    IMPORTANT:
    This updates MongoDB only.
    """

    target_ids = {
        str(item_id).strip()
        for item_id in item_ids
        if str(item_id).strip()
    }

    if not target_ids:
        return

    error_map = (
        error_map or {}
    )

    with _catalogue_lock:

        now = utc_now_iso()

        collection = (
            get_catalogue_collection()
        )

        for item_id in target_ids:

            try:

                update_fields = {
                    "ai_status": status
                }

                if status == "pending":

                    update_fields[
                        "ai_queued_at"
                    ] = now

                    collection.update_one(
                        {
                            "id": item_id
                        },
                        {
                            "$set": update_fields,
                            "$unset": {
                                "ai_processing_at": "",
                                "ai_processed_at": "",
                                "ai_error": "",
                            }
                        }
                    )

                elif status == "processing":

                    update_fields[
                        "ai_processing_at"
                    ] = now

                    collection.update_one(
                        {
                            "id": item_id
                        },
                        {
                            "$set": update_fields,
                            "$unset": {
                                "ai_error": "",
                            }
                        }
                    )

                elif status == "ready":

                    update_fields[
                        "ai_processed_at"
                    ] = now

                    collection.update_one(
                        {
                            "id": item_id
                        },
                        {
                            "$set": update_fields,
                            "$unset": {
                                "ai_processing_at": "",
                                "ai_error": "",
                            }
                        }
                    )

                elif status == "failed":

                    update_fields[
                        "ai_error"
                    ] = error_map.get(
                        item_id,
                        "AI processing failed.",
                    )

                    collection.update_one(
                        {
                            "id": item_id
                        },
                        {
                            "$set": update_fields,
                            "$unset": {
                                "ai_processing_at": "",
                            }
                        }
                    )

            except Exception as exc:

                print(
                    "[AI QUEUE] "
                    f"Could not update status "
                    f"for {item_id}:",
                    exc,
                )

                traceback.print_exc()


# ============================================================
# MARK PENDING
# ============================================================

def mark_pending(
    item_id: str
) -> None:
    """
    Mark a newly added item as pending.

    This function is kept for compatibility.
    """

    mark_items_status(
        [item_id],
        "pending",
    )


# ============================================================
# QUEUE STATUS FILE
# ============================================================

def default_status() -> dict:
    """
    Return the default queue status object.
    """

    return {
        "worker_running": False,
        "pending_count": 0,
        "processing_count": 0,
        "last_batch_size": 0,
        "last_started_at": None,
        "last_completed_at": None,
        "last_error": None,
        "oldest_pending_at": None,
    }


def load_queue_status() -> dict:
    """
    Load queue status for the status API.

    This file contains queue-run metadata only.
    Jewellery records remain in MongoDB.
    """

    if not QUEUE_STATUS_FILE.exists():

        return default_status()

    try:

        with open(
            QUEUE_STATUS_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )

        if isinstance(
            data,
            dict,
        ):

            result = (
                default_status()
            )

            result.update(
                data
            )

            return result

    except Exception:

        pass

    return default_status()


def save_queue_status(
    status: dict
) -> None:
    """
    Atomically save queue status.
    """

    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = (
        QUEUE_STATUS_FILE
        .with_suffix(
            ".tmp.json"
        )
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            status,
            file,
            indent=2,
            ensure_ascii=False,
        )

    temporary_file.replace(
        QUEUE_STATUS_FILE
    )


# ============================================================
# PENDING ITEMS
# ============================================================

def get_pending_items() -> list[dict]:
    """
    Return pending items ordered by queue time.

    MongoDB is the source of truth.

    Items without ai_queued_at are assigned the current time.
    """

    try:

        collection = (
            get_catalogue_collection()
        )

        documents = list(
            collection.find(
                {
                    "ai_status": "pending"
                },
                {
                    "_id": 0
                }
            )
        )

    except Exception as exc:

        print(
            "[AI QUEUE] "
            "Could not load pending items:",
            exc,
        )

        traceback.print_exc()

        return []

    now = utc_now_iso()

    pending = []

    for item in documents:

        item_id = str(
            item.get(
                "id",
                item.get(
                    "design_id",
                    "",
                ),
            )
        ).strip()

        if not item_id:
            continue

        queued_at = (
            item.get(
                "ai_queued_at"
            )
        )

        if not queued_at:

            queued_at = now

            try:

                collection.update_one(
                    {
                        "id": item_id
                    },
                    {
                        "$set": {
                            "ai_queued_at":
                                queued_at
                        }
                    }
                )

            except Exception as exc:

                print(
                    "[AI QUEUE] "
                    "Could not add queue timestamp "
                    f"to {item_id}:",
                    exc,
                )

        pending.append(
            {
                "id": item_id,
                "queued_at": queued_at,
            }
        )

    def sort_key(item):

        timestamp = (
            parse_timestamp(
                item.get(
                    "queued_at"
                )
            )
        )

        if timestamp is None:

            return time.time()

        return timestamp

    pending.sort(
        key=sort_key
    )

    return pending


# ============================================================
# BATCH DECISION
# ============================================================

def should_process_pending(
    pending: list[dict]
) -> bool:
    """
    Return True when batch or maximum-wait conditions are met.
    """

    if not pending:
        return False

    # Process immediately when 50 items are waiting.
    if len(pending) >= BATCH_SIZE:
        return True

    oldest_timestamp = (
        parse_timestamp(
            pending[0].get(
                "queued_at"
            )
        )
    )

    if oldest_timestamp is None:
        return False

    return (
        time.time()
        - oldest_timestamp
    ) >= MAX_WAIT_SECONDS


# ============================================================
# BATCH PROCESSING
# ============================================================

def process_one_batch() -> bool:
    """
    Process one batch if the trigger condition has been reached.

    Returns True when a batch was started,
    otherwise False.
    """

    pending = (
        get_pending_items()
    )

    if not should_process_pending(
        pending
    ):
        return False

    batch = (
        pending[:BATCH_SIZE]
    )

    batch_ids = [
        item["id"]
        for item in batch
    ]

    print()
    print("=" * 70)
    print(
        "JEWELMATCH AI - BACKGROUND BATCH"
    )
    print("=" * 70)

    print(
        f"[AI QUEUE] Processing "
        f"{len(batch_ids)} item(s)."
    )

    print(
        f"[AI QUEUE] Pending after "
        f"selection: {len(pending)}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # QUEUE STATUS
    # --------------------------------------------------------

    status = (
        load_queue_status()
    )

    status.update(
        {
            "worker_running": True,
            "pending_count": len(
                pending
            ),
            "processing_count": len(
                batch_ids
            ),
            "last_batch_size": len(
                batch_ids
            ),
            "last_started_at":
                utc_now_iso(),
            "last_error": None,
        }
    )

    save_queue_status(
        status
    )

    # --------------------------------------------------------
    # MARK PROCESSING
    # --------------------------------------------------------

    mark_items_status(
        batch_ids,
        "processing",
    )

    # --------------------------------------------------------
    # CREATE / UPDATE DINO INDEX
    # --------------------------------------------------------

    try:

        result = (
            create_index_for_items(
                batch_ids
            )
        )

        if result is None:

            raise RuntimeError(
                "DINO index processing "
                "returned no result."
            )

        # ----------------------------------------------------
        # SUCCESSFUL ITEMS
        # ----------------------------------------------------

        processed_ids = {
            str(item_id).strip()
            for item_id in result.get(
                "processed_ids",
                [],
            )
        }

        # ----------------------------------------------------
        # ERRORS
        # ----------------------------------------------------

        errors = result.get(
            "errors",
            [],
        )

        error_map = {}

        for error in errors:

            item_id = str(
                error.get(
                    "item",
                    "",
                )
            ).strip()

            if item_id:

                error_map[
                    item_id
                ] = str(
                    error.get(
                        "error",
                        "AI processing failed.",
                    )
                )

        # ----------------------------------------------------
        # FAILED ITEMS
        # ----------------------------------------------------

        failed_ids = (
            set(batch_ids)
            - processed_ids
        )

        # ----------------------------------------------------
        # MARK READY
        # ----------------------------------------------------

        if processed_ids:

            mark_items_status(
                list(
                    processed_ids
                ),
                "ready",
            )

        # ----------------------------------------------------
        # MARK FAILED
        # ----------------------------------------------------

        if failed_ids:

            mark_items_status(
                list(
                    failed_ids
                ),
                "failed",
                error_map=error_map,
            )

        # ----------------------------------------------------
        # FINAL QUEUE STATUS
        # ----------------------------------------------------

        status = (
            load_queue_status()
        )

        status.update(
            {
                "worker_running":
                    True,

                "processing_count":
                    0,

                "last_completed_at":
                    utc_now_iso(),

                "last_error": (
                    "One or more items failed."
                    if failed_ids
                    else None
                ),
            }
        )

        save_queue_status(
            status
        )

        print(
            f"[AI QUEUE] Ready: "
            f"{len(processed_ids)} | "
            f"Failed: "
            f"{len(failed_ids)}"
        )

        return True

    except Exception as exc:

        print(
            "[AI QUEUE] Batch failed:",
            exc,
        )

        traceback.print_exc()

        # ----------------------------------------------------
        # MARK ENTIRE BATCH FAILED
        # ----------------------------------------------------

        error_map = {
            item_id: str(exc)
            for item_id in batch_ids
        }

        mark_items_status(
            batch_ids,
            "failed",
            error_map=error_map,
        )

        # ----------------------------------------------------
        # QUEUE STATUS
        # ----------------------------------------------------

        status = (
            load_queue_status()
        )

        status.update(
            {
                "worker_running":
                    True,

                "processing_count":
                    0,

                "last_completed_at":
                    utc_now_iso(),

                "last_error":
                    str(exc),
            }
        )

        save_queue_status(
            status
        )

        return True


# ============================================================
# WORKER LOOP
# ============================================================

def worker_loop() -> None:
    """
    Continuously check the queue and process
    triggered batches.
    """

    print(
        "[AI QUEUE] "
        "Background worker started."
    )

    while True:

        try:

            process_one_batch()

        except Exception as exc:

            print(
                "[AI QUEUE] "
                "Worker loop error:",
                exc,
            )

            traceback.print_exc()

            status = (
                load_queue_status()
            )

            status[
                "last_error"
            ] = str(exc)

            save_queue_status(
                status
            )

        time.sleep(
            CHECK_INTERVAL_SECONDS
        )


# ============================================================
# START WORKER
# ============================================================

def start_ai_worker() -> None:
    """
    Start one background worker per Python process.

    Calling this function multiple times is safe.
    """

    global _worker_thread

    with _worker_lock:

        if (
            _worker_thread is not None
            and _worker_thread.is_alive()
        ):
            return

        _worker_thread = (
            threading.Thread(
                target=worker_loop,
                name=(
                    "jewelmatch-ai-worker"
                ),
                daemon=True,
            )
        )

        _worker_thread.start()

        status = (
            load_queue_status()
        )

        status[
            "worker_running"
        ] = True

        save_queue_status(
            status
        )


# ============================================================
# STATUS
# ============================================================

def get_ai_status() -> dict:
    """
    Return live AI queue status.

    Pending and processing counts are read directly
    from MongoDB.
    """

    try:

        collection = (
            get_catalogue_collection()
        )

        pending = (
            get_pending_items()
        )

        processing_count = (
            collection
            .count_documents(
                {
                    "ai_status":
                        "processing"
                }
            )
        )

    except Exception as exc:

        print(
            "[AI QUEUE] "
            "Could not calculate status:",
            exc,
        )

        traceback.print_exc()

        pending = []

        processing_count = 0

    status = (
        load_queue_status()
    )

    status[
        "worker_running"
    ] = bool(
        _worker_thread is not None
        and _worker_thread.is_alive()
    )

    status[
        "pending_count"
    ] = len(
        pending
    )

    status[
        "processing_count"
    ] = processing_count

    if pending:

        status[
            "oldest_pending_at"
        ] = pending[0].get(
            "queued_at"
        )

    else:

        status[
            "oldest_pending_at"
        ] = None

    return status