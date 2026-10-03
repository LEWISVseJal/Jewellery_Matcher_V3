# ============================================================
# JEWELMATCH AI - MONGODB CONNECTION
# ============================================================

import os
from pathlib import Path

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


# ============================================================
# ENVIRONMENT FILE
# ============================================================

ENV_FILE = (
    PROJECT_ROOT
    / ".env"
)


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv(
    ENV_FILE,
    override=True,
)


# ============================================================
# MONGODB URI
# ============================================================

MONGO_URI = os.environ.get(
    "MONGO_URI"
)


if not MONGO_URI:

    raise RuntimeError(
        "MONGO_URI is not configured. "
        f"Expected it in: {ENV_FILE}"
    )


# ============================================================
# DATABASE SETTINGS
# ============================================================

DATABASE_NAME = "jewelmatch"

JEWELLERY_COLLECTION = "jewellery"


# ============================================================
# MONGODB CLIENT
# ============================================================

client = MongoClient(

    MONGO_URI,

    # --------------------------------------------------------
    # TLS
    # --------------------------------------------------------

    tls=True,

    tlsCAFile=certifi.where(),

    # --------------------------------------------------------
    # TIMEOUTS
    # --------------------------------------------------------

    serverSelectionTimeoutMS=10000,

    connectTimeoutMS=20000,

    socketTimeoutMS=20000,

    # --------------------------------------------------------
    # CONNECTION POOL
    # --------------------------------------------------------

    maxPoolSize=10,

    minPoolSize=1,

    # --------------------------------------------------------
    # RETRY
    # --------------------------------------------------------

    retryWrites=True,

    retryReads=True,
)


# ============================================================
# DATABASE
# ============================================================

db = client[
    DATABASE_NAME
]


# ============================================================
# COLLECTION
# ============================================================

jewellery_collection = (
    db[
        JEWELLERY_COLLECTION
    ]
)


# ============================================================
# GET COLLECTION
# ============================================================

def get_jewellery_collection():

    return jewellery_collection


# ============================================================
# TEST CONNECTION
# ============================================================

def test_mongodb_connection():

    try:

        client.admin.command(
            "ping"
        )

        print(
            "[MONGODB] Connection successful."
        )

        return True

    except Exception as exc:

        print(
            "[MONGODB] Connection failed:"
        )

        print(
            repr(exc)
        )

        return False