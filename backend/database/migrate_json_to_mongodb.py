import json
from pathlib import Path

from pymongo import MongoClient, UpdateOne


# ============================================================
# CONFIGURATION
# ============================================================

MONGO_URI = "mongodb+srv://sejallewisaryahsworld_db_user:RLo9h0ldNgbeJNrC@jewelmatchcluster.4iyckea.mongodb.net"

DATABASE_NAME = "jewelmatch"
COLLECTION_NAME = "jewellery"

BASE_DIR = Path(__file__).resolve().parents[2]

JSON_FILE = (
    BASE_DIR
    / "backend"
    / "database"
    / "jewellery.json"
)


# ============================================================
# LOAD JSON
# ============================================================

print("=" * 70)
print("JEWELMATCH - JSON TO MONGODB MIGRATION")
print("=" * 70)

print(f"\nJSON file:")
print(JSON_FILE)

if not JSON_FILE.exists():
    print("\nERROR: jewellery.json was not found.")
    raise SystemExit(1)

with open(JSON_FILE, "r", encoding="utf-8") as file:
    jewellery_data = json.load(file)


if not isinstance(jewellery_data, list):
    print("\nERROR: jewellery.json does not contain a list.")
    raise SystemExit(1)


print(f"\nFound {len(jewellery_data)} jewellery records.")


# ============================================================
# CONNECT TO MONGODB
# ============================================================

print("\nConnecting to MongoDB Atlas...")

client = MongoClient(MONGO_URI)

try:
    client.admin.command("ping")
    print("MongoDB connection successful!")

    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]

    # --------------------------------------------------------
    # Remove our earlier TEST001 document
    # --------------------------------------------------------

    test_result = collection.delete_one({
        "id": "TEST001"
    })

    if test_result.deleted_count > 0:
        print("\nRemoved TEST001 test document.")

    # --------------------------------------------------------
    # Prepare records
    # --------------------------------------------------------

    operations = []

    for item in jewellery_data:

        if not item.get("id"):
            print("WARNING: Skipping record without an ID:")
            print(item)
            continue

        operations.append(
            UpdateOne(
                {"id": item["id"]},
                {"$set": item},
                upsert=True
            )
        )

    # --------------------------------------------------------
    # Insert / update records
    # --------------------------------------------------------

    if operations:
        result = collection.bulk_write(
            operations,
            ordered=False
        )

        print("\nMigration completed successfully.")

        print(f"Matched existing records : {result.matched_count}")
        print(f"Modified records          : {result.modified_count}")
        print(f"Inserted new records      : {result.upserted_count}")

    # --------------------------------------------------------
    # Create index on jewellery ID
    # --------------------------------------------------------

    collection.create_index(
        "id",
        unique=True
    )

    print("\nMongoDB index created on 'id'.")

    # --------------------------------------------------------
    # Show final count
    # --------------------------------------------------------

    total_records = collection.count_documents({})

    print("\nTotal records in MongoDB:")
    print(total_records)

    print("\n" + "=" * 70)
    print("MIGRATION FINISHED")
    print("=" * 70)

except Exception as e:

    print("\nMongoDB migration failed:")
    print(e)

finally:
    client.close()