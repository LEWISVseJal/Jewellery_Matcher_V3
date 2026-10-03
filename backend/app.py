# ============================================================
# JEWELMATCH AI - BACKEND APPLICATION
# ============================================================

from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
import traceback

from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
    send_file,
)

from flask_cors import CORS
from werkzeug.utils import secure_filename

from pymongo import MongoClient
from gridfs import GridFS
from bson import ObjectId


# ============================================================
# INTERNAL IMPORTS
# ============================================================

from .config import (
    ALLOWED_EXTENSIONS,
    TOP_K,
)

from .services.matcher import match_jewellery

from .services.ai_queue import (
    get_ai_status,
    start_ai_worker,
)

from .database.mongodb import (
    get_jewellery_collection,
    test_mongodb_connection,
)


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(
    __name__,
    static_folder=None,
)

CORS(app)


# ============================================================
# UPLOAD LIMIT
# ============================================================

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# ============================================================
# PROJECT DIRECTORIES
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

BACKEND_DIR = (
    BASE_DIR / "backend"
)

DATABASE_DIR = (
    BACKEND_DIR / "database"
)

CATALOGUE_DIR = (
    BACKEND_DIR / "catalogue"
)

GOLD_DIR = (
    CATALOGUE_DIR / "gold"
)

PROTOTYPE_DIR = (
    CATALOGUE_DIR / "prototype"
)

DINO_INDEX = (
    DATABASE_DIR / "dino_index.npz"
)

FRONTEND_DIST = (
    BASE_DIR
    / "frontend"
    / "react"
    / "dist"
)


# ============================================================
# COLLECTION SETTINGS
# ============================================================

VALID_COLLECTIONS = {
    "gold": "Gold",
    "prototype": "Prototype",
}


# ============================================================
# JEWELLERY TYPES
# ============================================================

VALID_JEWELLERY_TYPES = {
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
}


# ============================================================
# NORMALIZE COLLECTION
# ============================================================

def normalize_collection(value):

    if value is None:
        return None

    value = str(value).strip().lower()

    if value == "gold":
        return "gold"

    if value == "prototype":
        return "prototype"

    return None


# ============================================================
# CHECK ALLOWED IMAGE
# ============================================================

def allowed_file(filename):

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = (
        filename
        .rsplit(".", 1)[1]
        .lower()
    )

    return extension in ALLOWED_EXTENSIONS


# ============================================================
# GET ITEM FILENAME
# ============================================================

def get_item_filename(item):

    if not item:
        return None

    filename = item.get("filename")

    if filename:
        return Path(
            str(filename)
        ).name

    image = item.get("image")

    if image:
        return Path(
            str(image)
        ).name

    image_path = item.get("image_path")

    if image_path:
        return Path(
            str(image_path)
        ).name

    return None


# ============================================================
# GET ITEM COLLECTION
# ============================================================

def get_item_collection(item):

    if not item:
        return None

    return normalize_collection(
        item.get("collection")
    )


# ============================================================
# GET GRIDFS
# ============================================================

def get_gridfs():

    mongo_collection = (
        get_jewellery_collection()
    )

    database = mongo_collection.database

    return GridFS(database)


# ============================================================
# CHECK GRIDFS ID
# ============================================================

def get_gridfs_id(item):

    if not item:
        return None

    value = item.get(
        "image_gridfs_id"
    )

    if not value:
        return None

    try:

        if isinstance(
            value,
            ObjectId
        ):
            return value

        return ObjectId(
            str(value)
        )

    except Exception:

        return None


# ============================================================
# ADD IMAGE URL TO ITEM
# ============================================================

def add_image_url(item):

    if not item:
        return item

    item = dict(item)

    collection = (
        get_item_collection(item)
    )

    filename = (
        get_item_filename(item)
    )

    gridfs_id = (
        get_gridfs_id(item)
    )

    # --------------------------------------------------------
    # GRIDFS IMAGE
    # --------------------------------------------------------

    if gridfs_id:

        item["image_url"] = (
            f"/catalogue-image/"
            f"stored/"
            f"{str(gridfs_id)}"
        )

    # --------------------------------------------------------
    # LOCAL IMAGE FALLBACK
    # --------------------------------------------------------

    elif collection and filename:

        encoded_filename = quote(
            filename,
            safe=""
        )

        item["image_url"] = (
            f"/catalogue-image/"
            f"{collection}/"
            f"{encoded_filename}"
        )

    if filename:

        item["image"] = filename
        item["filename"] = filename

    return item


# ============================================================
# SERIALIZE MONGODB ITEM
# ============================================================

def serialize_mongo_item(item):

    if not item:
        return item

    item = dict(item)

    item.pop(
        "_id",
        None
    )

    # ObjectId cannot be returned directly by jsonify
    if item.get(
        "image_gridfs_id"
    ):

        item["image_gridfs_id"] = (
            str(
                item["image_gridfs_id"]
            )
        )

    return add_image_url(item)


# ============================================================
# GET MONGODB COLLECTION
# ============================================================

def get_catalogue_collection():

    return get_jewellery_collection()


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    try:

        mongo_ok = (
            test_mongodb_connection()
        )

        return jsonify(
            {
                "success": True,
                "backend": "running",
                "mongodb": mongo_ok,
                "gridfs": mongo_ok,
            }
        )

    except Exception as exc:

        print(
            "Health check error:",
            repr(exc)
        )

        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 500


# ============================================================
# AI STATUS
# ============================================================

@app.get("/api/ai-status")
def ai_status():

    try:

        status = (
            get_ai_status()
        )

        return jsonify(
            {
                "success": True,
                "status": status,
            }
        )

    except Exception as exc:

        print(
            "AI status error:",
            repr(exc)
        )

        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 500


# ============================================================
# CATALOGUE
# ============================================================

@app.get("/api/catalogue")
def get_catalogue():

    try:

        collection_name = (
            request.args
            .get(
                "collection",
                "all"
            )
            .strip()
            .lower()
        )

        search_text = (
            request.args
            .get(
                "search",
                ""
            )
            .strip()
        )

        mongo_collection = (
            get_catalogue_collection()
        )

        # ----------------------------------------------------
        # VALIDATE COLLECTION
        # ----------------------------------------------------

        if collection_name not in {
            "all",
            "gold",
            "prototype",
        }:

            return jsonify(
                {
                    "success": False,
                    "error": "Invalid collection.",
                }
            ), 400

        # ----------------------------------------------------
        # BUILD QUERY
        # ----------------------------------------------------

        query = {}

        if collection_name in {
            "gold",
            "prototype",
        }:

            query["collection"] = (
                VALID_COLLECTIONS[
                    collection_name
                ]
            )

        # ----------------------------------------------------
        # SEARCH
        # ----------------------------------------------------

        if search_text:

            query["$or"] = [

                {
                    "id": {
                        "$regex": search_text,
                        "$options": "i",
                    }
                },

                {
                    "design_id": {
                        "$regex": search_text,
                        "$options": "i",
                    }
                },

                {
                    "name": {
                        "$regex": search_text,
                        "$options": "i",
                    }
                },

                {
                    "design_name": {
                        "$regex": search_text,
                        "$options": "i",
                    }
                },

                {
                    "type": {
                        "$regex": search_text,
                        "$options": "i",
                    }
                },

                {
                    "subtype": {
                        "$regex": search_text,
                        "$options": "i",
                    }
                },

                {
                    "description": {
                        "$regex": search_text,
                        "$options": "i",
                    }
                },

            ]

        # ----------------------------------------------------
        # FETCH ITEMS
        # ----------------------------------------------------

        documents = (
            mongo_collection
            .find(
                query,
                {
                    "_id": 0
                }
            )
            .sort(
                [
                    ("id", 1)
                ]
            )
        )

        items = [
            serialize_mongo_item(
                document
            )
            for document in documents
        ]

        # ----------------------------------------------------
        # COUNTS
        # ----------------------------------------------------

        total_count = (
            mongo_collection
            .count_documents({})
        )

        gold_count = (
            mongo_collection
            .count_documents(
                {
                    "collection":
                    VALID_COLLECTIONS[
                        "gold"
                    ]
                }
            )
        )

        prototype_count = (
            mongo_collection
            .count_documents(
                {
                    "collection":
                    VALID_COLLECTIONS[
                        "prototype"
                    ]
                }
            )
        )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return jsonify(
            {
                "success": True,
                "items": items,
                "count": len(items),
                "total_count": total_count,
                "gold_count": gold_count,
                "prototype_count": prototype_count,
            }
        )

    except Exception as exc:

        print(
            "Catalogue error:",
            repr(exc)
        )

        traceback.print_exc()

        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 500


# ============================================================
# GET SINGLE CATALOGUE ITEM
# ============================================================

@app.get(
    "/api/catalogue/<item_id>"
)
def get_catalogue_item(item_id):

    return get_single_jewellery_item(
        item_id
    )


# ============================================================
# GET SINGLE JEWELLERY ITEM
# ============================================================

@app.get(
    "/api/jewellery/<item_id>"
)
def get_jewellery_item(item_id):

    return get_single_jewellery_item(
        item_id
    )


# ============================================================
# SHARED GET SINGLE JEWELLERY
# ============================================================

def get_single_jewellery_item(
    item_id
):

    try:

        mongo_collection = (
            get_catalogue_collection()
        )

        item = (
            mongo_collection
            .find_one(
                {
                    "id": item_id
                },
                {
                    "_id": 0
                }
            )
        )

        if not item:

            return jsonify(
                {
                    "success": False,
                    "error": "Jewellery not found.",
                }
            ), 404

        item = (
            serialize_mongo_item(
                item
            )
        )

        return jsonify(
            {
                "success": True,
                "item": item,
            }
        )

    except Exception as exc:

        print(
            "Get jewellery error:",
            repr(exc)
        )

        traceback.print_exc()

        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 500


# ============================================================
# CATALOGUE IMAGE FROM GRIDFS
# ============================================================

@app.get(
    "/catalogue-image/stored/<gridfs_id>"
)
def catalogue_image_stored(
    gridfs_id
):

    try:

        # ----------------------------------------------------
        # VALIDATE OBJECT ID
        # ----------------------------------------------------

        try:

            object_id = ObjectId(
                gridfs_id
            )

        except Exception:

            return jsonify(
                {
                    "success": False,
                    "error": "Invalid image ID.",
                }
            ), 400

        # ----------------------------------------------------
        # GET GRIDFS
        # ----------------------------------------------------

        fs = get_gridfs()

        # ----------------------------------------------------
        # CHECK FILE
        # ----------------------------------------------------

        if not fs.exists(
            object_id
        ):

            return jsonify(
                {
                    "success": False,
                    "error": "Stored image not found.",
                }
            ), 404

        # ----------------------------------------------------
        # GET FILE
        # ----------------------------------------------------

        grid_file = (
            fs.get(
                object_id
            )
        )

        # ----------------------------------------------------
        # RETURN FILE
        # ----------------------------------------------------

        response = send_file(
            grid_file,
            mimetype=(
                grid_file.content_type
                if getattr(
                    grid_file,
                    "content_type",
                    None
                )
                else None
            ),
            download_name=(
                grid_file.filename
                if getattr(
                    grid_file,
                    "filename",
                    None
                )
                else "jewellery-image"
            ),
        )

        response.headers[
            "Cache-Control"
        ] = (
            "public, max-age=31536000"
        )

        return response

    except Exception as exc:

        print(
            "GridFS image error:",
            repr(exc)
        )

        traceback.print_exc()

        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 500


# ============================================================
# CATALOGUE IMAGE - LOCAL FALLBACK
# ============================================================

@app.get(
    "/catalogue-image/"
    "<collection>/"
    "<path:filename>"
)
def catalogue_image(
    collection,
    filename
):

    try:

        collection = (
            collection
            .strip()
            .lower()
        )

        # ----------------------------------------------------
        # SELECT DIRECTORY
        # ----------------------------------------------------

        if collection == "gold":

            directory = GOLD_DIR

        elif collection == "prototype":

            directory = PROTOTYPE_DIR

        else:

            return jsonify(
                {
                    "success": False,
                    "error": "Invalid collection.",
                }
            ), 400

        # ----------------------------------------------------
        # SECURITY
        # ----------------------------------------------------

        safe_filename = (
            Path(filename).name
        )

        if not safe_filename:

            return jsonify(
                {
                    "success": False,
                    "error": "Invalid filename.",
                }
            ), 400

        # ----------------------------------------------------
        # CHECK LOCAL FILE
        # ----------------------------------------------------

        image_path = (
            directory
            / safe_filename
        )

        if not image_path.exists():

            return jsonify(
                {
                    "success": False,
                    "error": (
                        "Catalogue image not found."
                    ),
                    "filename": safe_filename,
                    "collection": collection,
                }
            ), 404

        # ----------------------------------------------------
        # SEND IMAGE
        # ----------------------------------------------------

        response = send_from_directory(
            str(directory),
            safe_filename
        )

        response.headers[
            "Cache-Control"
        ] = (
            "public, max-age=31536000"
        )

        return response

    except Exception as exc:

        print(
            "Catalogue image error:",
            repr(exc)
        )

        traceback.print_exc()

        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 500


# ============================================================
# GENERATE NEXT JEWELLERY ID
# ============================================================

def generate_next_jewellery_id(
    mongo_collection
):

    try:

        documents = (
            mongo_collection
            .find(
                {
                    "id": {
                        "$regex": r"^J\d+$",
                        "$options": "i",
                    }
                },
                {
                    "_id": 0,
                    "id": 1,
                }
            )
        )

        highest_number = 0

        for document in documents:

            item_id = str(
                document.get(
                    "id",
                    ""
                )
            ).strip().upper()

            if not item_id.startswith("J"):
                continue

            number_part = (
                item_id[1:]
            )

            if not number_part.isdigit():
                continue

            number = int(
                number_part
            )

            if number > highest_number:

                highest_number = number

        next_number = (
            highest_number + 1
        )

        return f"J{next_number:03d}"

    except Exception as exc:

        print(
            "Generate ID error:",
            repr(exc)
        )

        raise


# ============================================================
# SAVE IMAGE TO GRIDFS
# ============================================================

def save_image_to_gridfs(
    image_file,
    filename,
    collection
):

    try:

        fs = get_gridfs()

        # ----------------------------------------------------
        # RESET FILE POINTER
        # ----------------------------------------------------

        image_file.stream.seek(0)

        # ----------------------------------------------------
        # READ IMAGE
        # ----------------------------------------------------

        image_bytes = (
            image_file.read()
        )

        if not image_bytes:

            raise ValueError(
                "Uploaded image is empty."
            )

        # ----------------------------------------------------
        # CONTENT TYPE
        # ----------------------------------------------------

        content_type = (
            image_file.content_type
            or "application/octet-stream"
        )

        # ----------------------------------------------------
        # STORE IN GRIDFS
        # ----------------------------------------------------

        gridfs_id = fs.put(
            image_bytes,
            filename=filename,
            content_type=content_type,
            collection=collection,
            uploaded_at=datetime.now(
                timezone.utc
            ).isoformat(),
        )

        print(
            "Image stored in GridFS:",
            gridfs_id
        )

        return gridfs_id

    except Exception as exc:

        print(
            "GridFS upload error:",
            repr(exc)
        )

        raise


# ============================================================
# ADD JEWELLERY
# ============================================================

@app.post("/api/catalogue")
def add_jewellery():

    target_path = None
    gridfs_id = None

    try:

        # ----------------------------------------------------
        # MONGODB
        # ----------------------------------------------------

        mongo_collection = (
            get_catalogue_collection()
        )

        # ----------------------------------------------------
        # FORM DATA
        # ----------------------------------------------------

        name = (
            request.form
            .get(
                "name",
                ""
            )
            .strip()
        )

        collection_value = (
            request.form
            .get(
                "collection",
                ""
            )
            .strip()
        )

        jewellery_type = (
            request.form
            .get(
                "type",
                ""
            )
            .strip()
        )

        description = (
            request.form
            .get(
                "description",
                ""
            )
            .strip()
        )

        # ----------------------------------------------------
        # VALIDATE NAME
        # ----------------------------------------------------

        if not name:

            return jsonify(
                {
                    "success": False,
                    "message": (
                        "Please enter the jewellery name."
                    ),
                    "error": (
                        "Jewellery name is required."
                    ),
                }
            ), 400

        # ----------------------------------------------------
        # VALIDATE COLLECTION
        # ----------------------------------------------------

        collection = (
            normalize_collection(
                collection_value
            )
        )

        if not collection:

            return jsonify(
                {
                    "success": False,
                    "message": (
                        "Please select a collection."
                    ),
                    "error": (
                        "Collection must be Gold or Prototype."
                    ),
                }
            ), 400

        # ----------------------------------------------------
        # VALIDATE TYPE
        # ----------------------------------------------------

        if not jewellery_type:

            return jsonify(
                {
                    "success": False,
                    "message": (
                        "Please select a jewellery type."
                    ),
                    "error": (
                        "Jewellery type is required."
                    ),
                }
            ), 400

        # ----------------------------------------------------
        # VALIDATE IMAGE
        # ----------------------------------------------------

        image_file = (
            request.files.get(
                "image"
            )
        )

        if not image_file:

            return jsonify(
                {
                    "success": False,
                    "message": (
                        "Please upload a jewellery image."
                    ),
                    "error": (
                        "Jewellery image is required."
                    ),
                }
            ), 400

        if not image_file.filename:

            return jsonify(
                {
                    "success": False,
                    "message": (
                        "Invalid image file."
                    ),
                    "error": (
                        "Invalid image filename."
                    ),
                }
            ), 400

        if not allowed_file(
            image_file.filename
        ):

            return jsonify(
                {
                    "success": False,
                    "message": (
                        "Unsupported image format."
                    ),
                    "error": (
                        "Use JPG, JPEG, PNG, WEBP or BMP."
                    ),
                }
            ), 400

        # ----------------------------------------------------
        # GENERATE ID
        # ----------------------------------------------------

        jewellery_id = (
            generate_next_jewellery_id(
                mongo_collection
            )
        )

        print(
            "Generated jewellery ID:",
            jewellery_id
        )

        # ----------------------------------------------------
        # SECURE FILENAME
        # ----------------------------------------------------

        original_filename = (
            secure_filename(
                image_file.filename
            )
        )

        if not original_filename:

            return jsonify(
                {
                    "success": False,
                    "message": (
                        "Invalid image filename."
                    ),
                    "error": (
                        "Invalid image filename."
                    ),
                }
            ), 400

        # ----------------------------------------------------
        # SELECT LOCAL DIRECTORY
        # ----------------------------------------------------

        if collection == "gold":

            target_directory = GOLD_DIR

        else:

            target_directory = PROTOTYPE_DIR

        target_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        # ----------------------------------------------------
        # AVOID OVERWRITING LOCAL IMAGE
        # ----------------------------------------------------

        target_path = (
            target_directory
            / original_filename
        )

        if target_path.exists():

            stem = target_path.stem
            suffix = target_path.suffix

            counter = 1

            while target_path.exists():

                new_filename = (
                    f"{stem}_{counter}{suffix}"
                )

                target_path = (
                    target_directory
                    / new_filename
                )

                counter += 1

            original_filename = (
                target_path.name
            )

        # ----------------------------------------------------
        # READ IMAGE ONCE
        # ----------------------------------------------------

        image_file.stream.seek(0)

        image_bytes = (
            image_file.read()
        )

        if not image_bytes:

            return jsonify(
                {
                    "success": False,
                    "error": "Uploaded image is empty.",
                }
            ), 400

        # ----------------------------------------------------
        # SAVE LOCAL IMAGE
        # ----------------------------------------------------

        with open(
            target_path,
            "wb"
        ) as output_file:

            output_file.write(
                image_bytes
            )

        print(
            "Image saved locally:",
            target_path
        )

        # ----------------------------------------------------
        # SAVE IMAGE TO GRIDFS
        # ----------------------------------------------------

        fs = get_gridfs()

        content_type = (
            image_file.content_type
            or "application/octet-stream"
        )

        gridfs_id = fs.put(
            image_bytes,
            filename=original_filename,
            content_type=content_type,
            collection=collection,
            jewellery_id=jewellery_id,
            uploaded_at=datetime.now(
                timezone.utc
            ).isoformat(),
        )

        print(
            "Image stored permanently in GridFS:",
            gridfs_id
        )

        # ----------------------------------------------------
        # CREATE MONGODB DOCUMENT
        # ----------------------------------------------------

        new_item = {

            "id":
                jewellery_id,

            "name":
                name,

            "collection":
                VALID_COLLECTIONS[
                    collection
                ],

            "type":
                jewellery_type,

            "description":
                description,

            "image":
                original_filename,

            "filename":
                original_filename,

            "image_path":
                str(target_path),

            # IMPORTANT:
            # Permanent image reference
            "image_gridfs_id":
                gridfs_id,

            "ai_status":
                "pending",

            "ai_queued_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

        }

        # ----------------------------------------------------
        # INSERT
        # ----------------------------------------------------

        result = (
            mongo_collection
            .insert_one(
                new_item
            )
        )

        print(
            "MongoDB inserted:",
            result.inserted_id
        )

        new_item.pop(
            "_id",
            None
        )

        # ----------------------------------------------------
        # START AI WORKER
        # ----------------------------------------------------

        try:

            start_ai_worker()

            print(
                "AI worker checked after jewellery addition."
            )

        except Exception as worker_exc:

            print(
                "AI worker warning:",
                repr(worker_exc)
            )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        response_item = (
            serialize_mongo_item(
                new_item
            )
        )

        return jsonify(
            {
                "success": True,

                "message": (
                    "Jewellery added successfully. "
                    "Image stored permanently. "
                    "AI processing will be completed automatically."
                ),

                "item":
                    response_item,

            }
        ), 201

    except Exception as exc:

        print(
            "Add jewellery error:",
            repr(exc)
        )

        traceback.print_exc()

        # ----------------------------------------------------
        # CLEANUP LOCAL FILE
        # ----------------------------------------------------

        if target_path:

            try:

                if target_path.exists():

                    target_path.unlink()

            except Exception:

                pass

        # ----------------------------------------------------
        # CLEANUP GRIDFS FILE
        # ----------------------------------------------------

        if gridfs_id:

            try:

                fs = get_gridfs()

                fs.delete(
                    gridfs_id
                )

            except Exception:

                pass

        return jsonify(
            {
                "success": False,
                "message": (
                    "Unable to add jewellery."
                ),
                "error": str(exc),
            }
        ), 500


# ============================================================
# ADD JEWELLERY COMPATIBILITY ROUTE
# ============================================================

@app.post(
    "/api/jewellery/add"
)
def add_jewellery_compatibility():

    return add_jewellery()


# ============================================================
# DELETE CATALOGUE ITEM
# ============================================================

@app.delete(
    "/api/catalogue/<item_id>"
)
def delete_catalogue_item(
    item_id
):

    return delete_jewellery_item(
        item_id
    )


# ============================================================
# DELETE JEWELLERY COMPATIBILITY
# ============================================================

@app.delete(
    "/api/jewellery/<item_id>"
)
def delete_jewellery_compatibility(
    item_id
):

    return delete_jewellery_item(
        item_id
    )


# ============================================================
# SHARED DELETE FUNCTION
# ============================================================

def delete_jewellery_item(
    item_id
):

    try:

        mongo_collection = (
            get_catalogue_collection()
        )

        # ----------------------------------------------------
        # FIND ITEM
        # ----------------------------------------------------

        item = (
            mongo_collection
            .find_one(
                {
                    "id": item_id
                }
            )
        )

        if not item:

            return jsonify(
                {
                    "success": False,
                    "error": (
                        "Jewellery not found."
                    ),
                }
            ), 404

        # ----------------------------------------------------
        # GET LOCAL IMAGE
        # ----------------------------------------------------

        collection = (
            get_item_collection(item)
        )

        filename = (
            get_item_filename(item)
        )

        # ----------------------------------------------------
        # DELETE GRIDFS IMAGE
        # ----------------------------------------------------

        gridfs_id = (
            get_gridfs_id(item)
        )

        if gridfs_id:

            try:

                fs = get_gridfs()

                if fs.exists(
                    gridfs_id
                ):

                    fs.delete(
                        gridfs_id
                    )

                    print(
                        "Deleted GridFS image:",
                        gridfs_id
                    )

            except Exception as grid_exc:

                print(
                    "GridFS delete warning:",
                    repr(grid_exc)
                )

        # ----------------------------------------------------
        # DELETE LOCAL IMAGE
        # ----------------------------------------------------

        if collection and filename:

            if collection == "gold":

                image_directory = GOLD_DIR

            elif collection == "prototype":

                image_directory = PROTOTYPE_DIR

            else:

                image_directory = None

            if image_directory:

                image_path = (
                    image_directory
                    / filename
                )

                if image_path.exists():

                    try:

                        image_path.unlink()

                        print(
                            "Deleted local image:",
                            image_path
                        )

                    except Exception as image_exc:

                        print(
                            "Image delete warning:",
                            repr(image_exc)
                        )

        # ----------------------------------------------------
        # DELETE MONGODB RECORD
        # ----------------------------------------------------

        result = (
            mongo_collection
            .delete_one(
                {
                    "id": item_id
                }
            )
        )

        if result.deleted_count == 0:

            return jsonify(
                {
                    "success": False,
                    "error": (
                        "Jewellery could not be deleted."
                    ),
                }
            ), 500

        return jsonify(
            {
                "success": True,
                "message": (
                    "Jewellery deleted successfully."
                ),
                "id": item_id,
            }
        ), 200

    except Exception as exc:

        print(
            "Delete jewellery error:",
            repr(exc)
        )

        traceback.print_exc()

        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 500


# ============================================================
# JEWELLERY MATCHING
# ============================================================

@app.post("/api/match")
def match():

    query_path = None

    try:

        # ----------------------------------------------------
        # IMAGE
        # ----------------------------------------------------

        image_file = (
            request.files.get(
                "image"
            )
        )

        if not image_file:

            return jsonify(
                {
                    "success": False,
                    "error": (
                        "Image is required."
                    ),
                }
            ), 400

        if not image_file.filename:

            return jsonify(
                {
                    "success": False,
                    "error": (
                        "Invalid image."
                    ),
                }
            ), 400

        if not allowed_file(
            image_file.filename
        ):

            return jsonify(
                {
                    "success": False,
                    "error": (
                        "Unsupported image format."
                    ),
                }
            ), 400

        # ----------------------------------------------------
        # SEARCH MODE
        # ----------------------------------------------------

        search_mode = (
            request.form
            .get(
                "search_mode",
                "all"
            )
            .strip()
            .lower()
        )

        valid_search_modes = {
            "all",
            "gold_to_prototype",
            "prototype_to_gold",
        }

        if search_mode not in valid_search_modes:

            return jsonify(
                {
                    "success": False,
                    "error": (
                        "Invalid search mode."
                    ),
                }
            ), 400

        # ----------------------------------------------------
        # QUERY UPLOAD DIRECTORY
        # ----------------------------------------------------

        uploads_directory = (
            DATABASE_DIR
            / "uploads"
        )

        uploads_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        # ----------------------------------------------------
        # SECURE FILENAME
        # ----------------------------------------------------

        filename = secure_filename(
            image_file.filename
        )

        if not filename:

            return jsonify(
                {
                    "success": False,
                    "error": (
                        "Invalid image filename."
                    ),
                }
            ), 400

        # ----------------------------------------------------
        # AVOID COLLISION
        # ----------------------------------------------------

        query_path = (
            uploads_directory
            / filename
        )

        if query_path.exists():

            stem = query_path.stem
            suffix = query_path.suffix

            counter = 1

            while query_path.exists():

                new_filename = (
                    f"{stem}_{counter}{suffix}"
                )

                query_path = (
                    uploads_directory
                    / new_filename
                )

                counter += 1

        # ----------------------------------------------------
        # SAVE QUERY IMAGE
        # ----------------------------------------------------

        image_file.save(
            query_path
        )

        print()

        print(
            "=" * 70
        )

        print(
            "JEWELMATCH AI - MATCH REQUEST"
        )

        print(
            "=" * 70
        )

        print(
            "Query image:",
            query_path
        )

        print(
            "Search mode:",
            search_mode
        )

        print(
            "Top K:",
            TOP_K
        )

        print(
            "=" * 70
        )

        # ----------------------------------------------------
        # RUN MATCHER
        # ----------------------------------------------------

        results = match_jewellery(
            str(query_path),
            top_k=TOP_K,
            search_mode=search_mode,
        )

        # ----------------------------------------------------
        # NORMALIZE RESPONSE
        # ----------------------------------------------------

        if isinstance(
            results,
            list
        ):

            results = [

                serialize_mongo_item(
                    item
                )
                if isinstance(
                    item,
                    dict
                )
                else item

                for item in results

            ]

        elif isinstance(
            results,
            dict
        ):

            if isinstance(
                results.get("results"),
                list
            ):

                results["results"] = [

                    serialize_mongo_item(
                        item
                    )
                    if isinstance(
                        item,
                        dict
                    )
                    else item

                    for item in results[
                        "results"
                    ]

                ]

            results["search_mode"] = (
                search_mode
            )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        print(
            "Matching completed successfully."
        )

        print(
            "=" * 70
        )

        return jsonify(
            {
                "success": True,
                "results": results,
                "search_mode": search_mode,
            }
        ), 200

    except Exception as exc:

        print(
            "Matching error:",
            repr(exc)
        )

        traceback.print_exc()

        return jsonify(
            {
                "success": False,
                "matched": False,
                "error": str(exc),
                "results": [],
            }
        ), 500

    finally:

        # ----------------------------------------------------
        # REMOVE QUERY IMAGE
        # ----------------------------------------------------

        if query_path:

            try:

                if query_path.exists():

                    query_path.unlink()

                    print(
                        "Temporary query image deleted:",
                        query_path
                    )

            except Exception as cleanup_exc:

                print(
                    "Query image cleanup warning:",
                    repr(cleanup_exc)
                )


# ============================================================
# REACT FRONTEND
# ============================================================

def frontend_response(
    path=""
):

    # --------------------------------------------------------
    # API ROUTES MUST NOT GO TO REACT
    # --------------------------------------------------------

    if path.startswith(
        "api/"
    ):

        return jsonify(
            {
                "success": False,
                "error": (
                    "API endpoint not found."
                ),
            }
        ), 404

    # --------------------------------------------------------
    # CATALOGUE IMAGE ROUTES MUST NOT GO TO REACT
    # --------------------------------------------------------

    if path.startswith(
        "catalogue-image/"
    ):

        return jsonify(
            {
                "success": False,
                "error": (
                    "Catalogue image endpoint not found."
                ),
            }
        ), 404

    # --------------------------------------------------------
    # CHECK FRONTEND
    # --------------------------------------------------------

    index_file = (
        FRONTEND_DIST
        / "index.html"
    )

    if not index_file.exists():

        return jsonify(
            {
                "success": False,
                "error": (
                    "React frontend build was not found."
                ),
                "frontend_dist": str(
                    FRONTEND_DIST
                ),
            }
        ), 500

    # --------------------------------------------------------
    # SERVE STATIC FILE
    # --------------------------------------------------------

    if path:

        requested_file = (
            FRONTEND_DIST
            / path
        )

        try:

            requested_file = (
                requested_file.resolve()
            )

            frontend_root = (
                FRONTEND_DIST
                .resolve()
            )

            requested_file.relative_to(
                frontend_root
            )

        except ValueError:

            return jsonify(
                {
                    "success": False,
                    "error": "Invalid path.",
                }
            ), 400

        if (
            requested_file.exists()
            and requested_file.is_file()
        ):

            return send_from_directory(
                str(FRONTEND_DIST),
                path
            )

    # --------------------------------------------------------
    # REACT SPA FALLBACK
    # --------------------------------------------------------

    return send_from_directory(
        str(FRONTEND_DIST),
        "index.html"
    )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def home():

    return frontend_response("")


# ============================================================
# REACT ROUTES
# ============================================================

@app.route(
    "/<path:path>"
)
def serve_frontend(path):

    return frontend_response(
        path
    )


# ============================================================
# FILE TOO LARGE
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify(
        {
            "success": False,
            "error": (
                "File is too large. "
                "Maximum allowed size is 10 MB."
            ),
        }
    ), 413


# ============================================================
# NOT FOUND
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify(
        {
            "success": False,
            "error": (
                "Endpoint not found."
            ),
        }
    ), 404


# ============================================================
# METHOD NOT ALLOWED
# ============================================================

@app.errorhandler(405)
def method_not_allowed(error):

    return jsonify(
        {
            "success": False,
            "error": (
                "Method not allowed."
            ),
        }
    ), 405


# ============================================================
# GENERAL ERROR
# ============================================================

@app.errorhandler(Exception)
def handle_general_error(error):

    print(
        "Unhandled application error:",
        repr(error)
    )

    traceback.print_exc()

    return jsonify(
        {
            "success": False,
            "error": str(error),
        }
    ), 500


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print(
        "=" * 70
    )

    print(
        "JEWELMATCH AI BACKEND"
    )

    print(
        "=" * 70
    )

    print(
        "Gold catalogue directory:"
    )

    print(
        GOLD_DIR
    )

    print(
        "Prototype catalogue directory:"
    )

    print(
        PROTOTYPE_DIR
    )

    print(
        "MongoDB connected:",
        test_mongodb_connection()
    )

    print(
        "DINO index exists:",
        DINO_INDEX.exists()
    )

    print(
        "Top K matches:",
        TOP_K
    )

    print(
        "Frontend directory:",
        FRONTEND_DIST
    )

    print(
        "Frontend index exists:",
        (
            FRONTEND_DIST
            / "index.html"
        ).exists()
    )

    print(
        "GridFS enabled: True"
    )

    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # START AI WORKER
    # --------------------------------------------------------

    try:

        start_ai_worker()

        print(
            "AI background worker started."
        )

    except Exception as exc:

        print(
            "AI worker warning:",
            repr(exc)
        )

    # --------------------------------------------------------
    # START FLASK
    # --------------------------------------------------------

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )