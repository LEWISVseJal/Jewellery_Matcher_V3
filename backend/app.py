"""
JewelMatch AI
Flask Backend API

Features:
    - Jewellery visual matching
    - Catalogue listing
    - Catalogue item details
    - Add jewellery
    - Edit jewellery
    - Delete jewellery
    - Rebuild DINO index
    - Catalogue image serving

Add Jewellery fields:
    - name
    - collection
    - type
    - description
    - image

Removed fields:
    - gender
    - subtype
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import traceback
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
)
from flask_cors import CORS
from werkzeug.utils import secure_filename

from .services.matcher import match_jewellery


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

BACKEND_DIR = BASE_DIR / "backend"

DATABASE_DIR = BACKEND_DIR / "database"

CATALOGUE_DIR = BACKEND_DIR / "catalogue"

GOLD_DIR = CATALOGUE_DIR / "gold"

PROTOTYPE_DIR = CATALOGUE_DIR / "prototype"

JEWELLERY_JSON = DATABASE_DIR / "jewellery.json"

DINO_INDEX = DATABASE_DIR / "dino_index.npz"


# ============================================================
# APP
# ============================================================

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": "*"
        },
        r"/catalogue-image/*": {
            "origins": "*"
        },
    },
)


# ============================================================
# CONFIGURATION
# ============================================================

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "bmp",
}

MAX_UPLOAD_SIZE = 10 * 1024 * 1024

app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE


# ============================================================
# JEWELLERY TYPES
# ============================================================

JEWELLERY_TYPES = [
    "LP",
    "GP",
    "LAD",
    "GAD",
    "SSL",
    "SSG",
    "WB",
    "EMROLD",
    "KACHUWA TORTOISE",
    "CHALA MIX",
    "OMP",
    "GF",
    "FOTO",
    "LBR",
    "GBR",
    "PENDELS",
    "HIGHPOLISHCHARMS",
    "CUTTING CHARMS",
    "LCH",
    "SIMBA",
    "LETTERS",
    "OMRING",
    "RAJMUDRA",
    "OTHERS EXTRA",
    "GCH",
]


VALID_COLLECTIONS = {
    "gold": "Gold",
    "prototype": "Prototype",
}


# ============================================================
# DIRECTORY SETUP
# ============================================================

DATABASE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

GOLD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

PROTOTYPE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# HELPERS
# ============================================================

def allowed_file(filename: str) -> bool:
    """
    Check whether uploaded file has an allowed image extension.
    """

    if not filename:
        return False

    extension = Path(filename).suffix.lower().lstrip(".")

    return extension in ALLOWED_EXTENSIONS


def normalize_collection(value: str | None) -> str | None:
    """
    Convert collection value into canonical form.
    """

    if not value:
        return None

    value = value.strip().lower()

    return VALID_COLLECTIONS.get(value)


def normalize_type(value: str | None) -> str | None:
    """
    Match jewellery type against the allowed type list.
    """

    if not value:
        return None

    value = value.strip()

    for jewellery_type in JEWELLERY_TYPES:

        if jewellery_type.lower() == value.lower():
            return jewellery_type

    return None


def load_catalogue() -> list:
    """
    Load jewellery catalogue JSON.
    """

    if not JEWELLERY_JSON.exists():
        return []

    try:

        with open(
            JEWELLERY_JSON,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if isinstance(data, list):
            return data

        if isinstance(data, dict):

            if isinstance(data.get("items"), list):
                return data["items"]

            if isinstance(data.get("jewellery"), list):
                return data["jewellery"]

        return []

    except Exception as exc:

        print(
            "[CATALOGUE] Failed to load jewellery.json:",
            exc,
        )

        return []


def save_catalogue(items: list) -> None:
    """
    Save jewellery catalogue JSON atomically.
    """

    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = JEWELLERY_JSON.with_suffix(
        ".tmp.json"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            items,
            file,
            indent=2,
            ensure_ascii=False,
        )

    temporary_file.replace(
        JEWELLERY_JSON
    )


def generate_next_design_id(items: list) -> str:
    """
    Generate next J001-style design ID.
    """

    highest_number = 0

    for item in items:

        design_id = str(
            item.get(
                "design_id",
                item.get(
                    "id",
                    "",
                ),
            )
        )

        match = re.search(
            r"J(\d+)",
            design_id.upper(),
        )

        if match:

            number = int(
                match.group(1)
            )

            highest_number = max(
                highest_number,
                number,
            )

    return f"J{highest_number + 1:03d}"


def get_collection_directory(
    collection: str,
) -> Path:
    """
    Return catalogue directory for collection.
    """

    normalized = normalize_collection(
        collection
    )

    if normalized == "Gold":
        return GOLD_DIR

    if normalized == "Prototype":
        return PROTOTYPE_DIR

    raise ValueError(
        "Invalid collection."
    )


def build_image_url(
    collection: str,
    filename: str,
) -> str:
    """
    Build frontend image URL.
    """

    collection_value = collection.lower()

    return (
        f"/catalogue-image/"
        f"{collection_value}/"
        f"{filename}"
    )


def enrich_catalogue_item(
    item: dict,
) -> dict:
    """
    Add image_url/image fields without changing
    the stored catalogue object.
    """

    result = dict(item)

    collection = result.get(
        "collection",
        "",
    )

    image_path = result.get(
        "image_path",
        result.get(
            "image",
            "",
        ),
    )

    filename = result.get(
        "filename",
        "",
    )

    if image_path:

        path = Path(
            str(image_path)
        )

        filename = path.name

    if collection and filename:

        image_url = build_image_url(
            collection,
            filename,
        )

        result["image_url"] = image_url
        result["image"] = image_url

    return result


def rebuild_dino_index() -> dict:
    """
    Rebuild the DINO index.

    Uses the existing project index-building script,
    so the current matcher/index architecture remains intact.
    """

    print(
        "[INDEX] Rebuilding DINO index..."
    )

    try:

        from .scripts.create_dino_index import (
            build_index,
        )

        result = build_index(
            force=True
        )

        print(
            "[INDEX] DINO index rebuilt successfully."
        )

        return {
            "success": True,
            "result": result,
        }

    except Exception as exc:

        print(
            "[INDEX] Direct rebuild failed:",
            exc,
        )

        traceback.print_exc()

        return {
            "success": False,
            "message": str(exc),
        }


def remove_old_image(
    item: dict,
) -> None:
    """
    Remove old catalogue image when required.
    """

    image_path = item.get(
        "image_path"
    )

    if not image_path:
        return

    path = Path(
        image_path
    )

    if path.exists():

        try:

            path.unlink()

        except Exception as exc:

            print(
                "[IMAGE] Could not remove old image:",
                exc,
            )


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return jsonify(
        {
            "success": True,
            "status": "healthy",
            "service": "JewelMatch AI",
        }
    )


# ============================================================
# JEWELLERY TYPES API
# ============================================================

@app.get("/api/jewellery-types")
def get_jewellery_types():

    return jsonify(
        {
            "success": True,
            "types": JEWELLERY_TYPES,
        }
    )


# ============================================================
# MATCH API
# ============================================================

@app.post("/api/match")
def match_api():

    try:

        uploaded_file = request.files.get(
            "image"
        )

        if uploaded_file is None:

            return jsonify(
                {
                    "success": False,
                    "message": "No image was uploaded.",
                }
            ), 400

        if not uploaded_file.filename:

            return jsonify(
                {
                    "success": False,
                    "message": "Uploaded image has no filename.",
                }
            ), 400

        if not allowed_file(
            uploaded_file.filename
        ):

            return jsonify(
                {
                    "success": False,
                    "message": "Unsupported image format.",
                }
            ), 400

        search_mode = request.form.get(
            "search_mode",
            "all",
        )

        if search_mode not in {
            "all",
            "gold_to_prototype",
            "prototype_to_gold",
        }:

            search_mode = "all"

        try:

            top_k = int(
                request.form.get(
                    "top_k",
                    8,
                )
            )

        except ValueError:

            top_k = 8

        top_k = max(
            1,
            min(
                top_k,
                20,
            ),
        )

        upload_dir = DATABASE_DIR / "uploads"

        upload_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = secure_filename(
            uploaded_file.filename
        )

        temporary_path = (
            upload_dir /
            filename
        )

        uploaded_file.save(
            temporary_path
        )

        try:

            result = match_jewellery(
                temporary_path,
                top_k=top_k,
                search_mode=search_mode,
            )

        finally:

            if temporary_path.exists():

                try:
                    temporary_path.unlink()
                except Exception:
                    pass

        return jsonify(
            result
        )

    except Exception as exc:

        print(
            "[MATCH API ERROR]",
            exc,
        )

        traceback.print_exc()

        return jsonify(
            {
                "success": False,
                "message": str(exc),
            }
        ), 500


# ============================================================
# CATALOGUE API
# ============================================================

@app.get("/api/catalogue")
def get_catalogue():

    try:

        items = load_catalogue()

        collection_filter = request.args.get(
            "collection",
            "all",
        )

        search = request.args.get(
            "search",
            "",
        ).strip().lower()

        if collection_filter:

            collection_filter = (
                collection_filter.strip().lower()
            )

        filtered_items = []

        for item in items:

            item_collection = str(
                item.get(
                    "collection",
                    "",
                )
            ).lower()

            if (
                collection_filter
                and collection_filter != "all"
                and item_collection != collection_filter
            ):
                continue

            if search:

                searchable = " ".join(
                    [
                        str(
                            item.get(
                                "id",
                                "",
                            )
                        ),
                        str(
                            item.get(
                                "design_id",
                                "",
                            )
                        ),
                        str(
                            item.get(
                                "name",
                                "",
                            )
                        ),
                        str(
                            item.get(
                                "design_name",
                                "",
                            )
                        ),
                        str(
                            item.get(
                                "type",
                                "",
                            )
                        ),
                        str(
                            item.get(
                                "collection",
                                "",
                            )
                        ),
                    ]
                ).lower()

                if search not in searchable:
                    continue

            filtered_items.append(
                enrich_catalogue_item(
                    item
                )
            )

        gold_count = sum(
            1
            for item in items
            if str(
                item.get(
                    "collection",
                    "",
                )
            ).lower()
            == "gold"
        )

        prototype_count = sum(
            1
            for item in items
            if str(
                item.get(
                    "collection",
                    "",
                )
            ).lower()
            == "prototype"
        )

        return jsonify(
            {
                "success": True,
                "items": filtered_items,
                "total_count": len(items),
                "gold_count": gold_count,
                "prototype_count": prototype_count,
            }
        )

    except Exception as exc:

        print(
            "[CATALOGUE API ERROR]",
            exc,
        )

        traceback.print_exc()

        return jsonify(
            {
                "success": False,
                "message": str(exc),
            }
        ), 500


# ============================================================
# SINGLE CATALOGUE ITEM
# ============================================================

@app.get("/api/catalogue/<item_id>")
def get_catalogue_item(
    item_id: str,
):

    items = load_catalogue()

    for item in items:

        current_id = str(
            item.get(
                "id",
                item.get(
                    "design_id",
                    "",
                ),
            )
        )

        design_id = str(
            item.get(
                "design_id",
                "",
            )
        )

        if (
            current_id == item_id
            or design_id == item_id
        ):

            return jsonify(
                {
                    "success": True,
                    "item": enrich_catalogue_item(
                        item
                    ),
                }
            )

    return jsonify(
        {
            "success": False,
            "message": "Jewellery item not found.",
        }
    ), 404


# ============================================================
# ADD JEWELLERY
# ============================================================

@app.post("/api/jewellery/add")
def add_jewellery():

    try:

        uploaded_file = request.files.get(
            "image"
        )

        if uploaded_file is None:

            return jsonify(
                {
                    "success": False,
                    "message": "Jewellery image is required.",
                }
            ), 400

        if not uploaded_file.filename:

            return jsonify(
                {
                    "success": False,
                    "message": "Jewellery image filename is missing.",
                }
            ), 400

        if not allowed_file(
            uploaded_file.filename
        ):

            return jsonify(
                {
                    "success": False,
                    "message": "Only JPG, JPEG, PNG, WEBP and BMP images are allowed.",
                }
            ), 400

        name = request.form.get(
            "name",
            "",
        ).strip()

        collection = normalize_collection(
            request.form.get(
                "collection"
            )
        )

        jewellery_type = normalize_type(
            request.form.get(
                "type"
            )
        )

        description = request.form.get(
            "description",
            "",
        ).strip()

        if not name:

            return jsonify(
                {
                    "success": False,
                    "message": "Jewellery name is required.",
                }
            ), 400

        if not collection:

            return jsonify(
                {
                    "success": False,
                    "message": "Please select Gold or Prototype.",
                }
            ), 400

        if not jewellery_type:

            return jsonify(
                {
                    "success": False,
                    "message": "Please select a valid jewellery type.",
                }
            ), 400

        items = load_catalogue()

        design_id = generate_next_design_id(
            items
        )

        extension = (
            Path(
                uploaded_file.filename
            ).suffix.lower()
        )

        if not extension:
            extension = ".jpg"

        filename = (
            f"{design_id}"
            f"{extension}"
        )

        collection_dir = get_collection_directory(
            collection
        )

        image_path = (
            collection_dir /
            filename
        )

        uploaded_file.save(
            image_path
        )

        new_item = {
            "id": design_id,
            "design_id": design_id,
            "name": name,
            "design_name": name,
            "collection": collection,
            "type": jewellery_type,
            "description": description,
            "filename": filename,
            "image_path": str(
                image_path
            ),
        }

        items.append(
            new_item
        )

        try:

            save_catalogue(
                items
            )

            index_result = rebuild_dino_index()

            if not index_result["success"]:

                raise RuntimeError(
                    "Jewellery was saved, but DINO index rebuilding failed: "
                    + index_result["message"]
                )

        except Exception:

            if image_path.exists():

                try:
                    image_path.unlink()
                except Exception:
                    pass

            raise

        print(
            f"[CATALOGUE] Added {design_id}"
        )

        return jsonify(
            {
                "success": True,
                "message": "Jewellery added successfully.",
                "item": enrich_catalogue_item(
                    new_item
                ),
                "index_rebuilt": True,
            }
        ), 201

    except Exception as exc:

        print(
            "[ADD JEWELLERY ERROR]",
            exc,
        )

        traceback.print_exc()

        return jsonify(
            {
                "success": False,
                "message": str(exc),
            }
        ), 500


# ============================================================
# UPDATE JEWELLERY
# ============================================================

@app.post("/api/jewellery/<item_id>")
def update_jewellery(
    item_id: str,
):

    try:

        items = load_catalogue()

        item_index = None

        for index, item in enumerate(
            items
        ):

            current_id = str(
                item.get(
                    "id",
                    item.get(
                        "design_id",
                        "",
                    ),
                )
            )

            design_id = str(
                item.get(
                    "design_id",
                    "",
                )
            )

            if (
                current_id == item_id
                or design_id == item_id
            ):

                item_index = index
                break

        if item_index is None:

            return jsonify(
                {
                    "success": False,
                    "message": "Jewellery item not found.",
                }
            ), 404

        item = dict(
            items[item_index]
        )

        name = request.form.get(
            "name",
            item.get(
                "name",
                "",
            ),
        ).strip()

        collection = normalize_collection(
            request.form.get(
                "collection",
                item.get(
                    "collection",
                    "",
                ),
            )
        )

        jewellery_type = normalize_type(
            request.form.get(
                "type",
                item.get(
                    "type",
                    "",
                ),
            )
        )

        description = request.form.get(
            "description",
            item.get(
                "description",
                "",
            ),
        ).strip()

        if not name:

            return jsonify(
                {
                    "success": False,
                    "message": "Jewellery name is required.",
                }
            ), 400

        if not collection:

            return jsonify(
                {
                    "success": False,
                    "message": "Please select Gold or Prototype.",
                }
            ), 400

        if not jewellery_type:

            return jsonify(
                {
                    "success": False,
                    "message": "Please select a valid jewellery type.",
                }
            ), 400

        old_collection = normalize_collection(
            item.get(
                "collection"
            )
        )

        old_image_path = Path(
            item.get(
                "image_path",
                "",
            )
        )

        new_image = request.files.get(
            "image"
        )

        collection_changed = (
            old_collection != collection
        )

        image_changed = (
            new_image is not None
            and bool(
                new_image.filename
            )
        )

        if image_changed:

            if not allowed_file(
                new_image.filename
            ):

                return jsonify(
                    {
                        "success": False,
                        "message": "Unsupported image format.",
                    }
                ), 400

            extension = (
                Path(
                    new_image.filename
                ).suffix.lower()
            )

            filename = (
                f"{item.get('design_id', item_id)}"
                f"{extension}"
            )

            new_directory = get_collection_directory(
                collection
            )

            new_image_path = (
                new_directory /
                filename
            )

            new_image.save(
                new_image_path
            )

            if (
                old_image_path.exists()
                and old_image_path != new_image_path
            ):

                try:
                    old_image_path.unlink()
                except Exception:
                    pass

            item["filename"] = filename

            item["image_path"] = str(
                new_image_path
            )

        elif collection_changed:

            if old_image_path.exists():

                extension = (
                    old_image_path.suffix
                    or ".jpg"
                )

                filename = (
                    f"{item.get('design_id', item_id)}"
                    f"{extension}"
                )

                new_directory = get_collection_directory(
                    collection
                )

                new_image_path = (
                    new_directory /
                    filename
                )

                try:

                    old_image_path.rename(
                        new_image_path
                    )

                    item["filename"] = filename

                    item["image_path"] = str(
                        new_image_path
                    )

                except Exception:

                    pass

        item["name"] = name

        item["design_name"] = name

        item["collection"] = collection

        item["type"] = jewellery_type

        item["description"] = description

        # Remove fields that are no longer part
        # of the Add Jewellery data model.
        item.pop(
            "gender",
            None,
        )

        item.pop(
            "subtype",
            None,
        )

        items[item_index] = item

        save_catalogue(
            items
        )

        # Rebuild only when the image or collection
        # changes because those affect the DINO index.
        index_rebuilt = False

        if (
            image_changed
            or collection_changed
        ):

            index_result = rebuild_dino_index()

            if not index_result["success"]:

                return jsonify(
                    {
                        "success": False,
                        "message": (
                            "Catalogue updated, "
                            "but DINO index rebuilding failed: "
                            + index_result["message"]
                        ),
                    }
                ), 500

            index_rebuilt = True

        return jsonify(
            {
                "success": True,
                "message": "Jewellery updated successfully.",
                "item": enrich_catalogue_item(
                    item
                ),
                "index_rebuilt": index_rebuilt,
            }
        )

    except Exception as exc:

        print(
            "[UPDATE JEWELLERY ERROR]",
            exc,
        )

        traceback.print_exc()

        return jsonify(
            {
                "success": False,
                "message": str(exc),
            }
        ), 500


# ============================================================
# DELETE JEWELLERY
# ============================================================

@app.delete("/api/jewellery/<item_id>")
def delete_jewellery(
    item_id: str,
):

    try:

        items = load_catalogue()

        found_item = None

        remaining_items = []

        for item in items:

            current_id = str(
                item.get(
                    "id",
                    item.get(
                        "design_id",
                        "",
                    ),
                )
            )

            design_id = str(
                item.get(
                    "design_id",
                    "",
                )
            )

            if (
                current_id == item_id
                or design_id == item_id
            ):

                found_item = item

            else:

                remaining_items.append(
                    item
                )

        if found_item is None:

            return jsonify(
                {
                    "success": False,
                    "message": "Jewellery item not found.",
                }
            ), 404

        remove_old_image(
            found_item
        )

        save_catalogue(
            remaining_items
        )

        index_result = rebuild_dino_index()

        if not index_result["success"]:

            return jsonify(
                {
                    "success": False,
                    "message": (
                        "Jewellery deleted, "
                        "but DINO index rebuilding failed: "
                        + index_result["message"]
                    ),
                }
            ), 500

        return jsonify(
            {
                "success": True,
                "message": "Jewellery deleted successfully.",
                "deleted_id": item_id,
                "index_rebuilt": True,
            }
        )

    except Exception as exc:

        print(
            "[DELETE JEWELLERY ERROR]",
            exc,
        )

        traceback.print_exc()

        return jsonify(
            {
                "success": False,
                "message": str(exc),
            }
        ), 500


# ============================================================
# REBUILD INDEX
# ============================================================

@app.post("/api/rebuild-index")
def rebuild_index_api():

    try:

        result = rebuild_dino_index()

        if not result["success"]:

            return jsonify(
                {
                    "success": False,
                    "message": result["message"],
                }
            ), 500

        return jsonify(
            {
                "success": True,
                "message": "DINO search index rebuilt successfully.",
                "result": result.get(
                    "result"
                ),
            }
        )

    except Exception as exc:

        print(
            "[REBUILD INDEX ERROR]",
            exc,
        )

        traceback.print_exc()

        return jsonify(
            {
                "success": False,
                "message": str(exc),
            }
        ), 500


# ============================================================
# CATALOGUE IMAGE
# ============================================================

@app.get(
    "/catalogue-image/<collection>/<path:filename>"
)
def catalogue_image(
    collection: str,
    filename: str,
):

    collection_normalized = normalize_collection(
        collection
    )

    if collection_normalized == "Gold":

        directory = GOLD_DIR

    elif collection_normalized == "Prototype":

        directory = PROTOTYPE_DIR

    else:

        return jsonify(
            {
                "success": False,
                "message": "Invalid collection.",
            }
        ), 400

    return send_from_directory(
        directory,
        filename,
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000,
        )
    )

    host = os.environ.get(
        "HOST",
        "0.0.0.0",
    )

    print(
        ""
    )

    print(
        "=" * 70
    )

    print(
        "JewelMatch AI Backend"
    )

    print(
        "=" * 70
    )

    print(
        f"Host : {host}"
    )

    print(
        f"Port : {port}"
    )

    print(
        "=" * 70
    )

    app.run(
        host=host,
        port=port,
        debug=True,
    )