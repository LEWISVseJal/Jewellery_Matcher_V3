import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

# Project root:
# Jewellery_Matcher/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load .env from the project root
ENV_FILE = PROJECT_ROOT / ".env"

# override=True ensures that the MONGO_URI from this project's
# .env file is used instead of any existing environment variable.
load_dotenv(ENV_FILE, override=True)


# ============================================================
# MONGODB CONFIGURATION
# ============================================================

MONGO_URI = os.environ.get("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError(
        "MONGO_URI is not configured. "
        f"Expected it in: {ENV_FILE}"
    )


DATABASE_NAME = "jewelmatch"
JEWELLERY_COLLECTION = "jewellery"


# ============================================================
# MONGODB CLIENT
# ============================================================

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=10000,
)

db = client[DATABASE_NAME]

jewellery_collection = db[
    JEWELLERY_COLLECTION
]


# ============================================================
# COLLECTION ACCESS
# ============================================================

def get_jewellery_collection():
    return jewellery_collection


# ============================================================
# CONNECTION TEST
# ============================================================

def test_mongodb_connection():
    try:
        client.admin.command("ping")
        return True
    except Exception:
        return False

