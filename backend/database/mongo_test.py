from pymongo import MongoClient

MONGO_URI = "mongodb+srv://sejallewisaryahsworld_db_user:RLo9h0ldNgbeJNrC@jewelmatchcluster.4iyckea.mongodb.net"

client = MongoClient(MONGO_URI)

try:
    # Test connection
    client.admin.command("ping")
    print("MongoDB connection successful!")

    # Select database
    db = client["jewelmatch"]

    # Select collection
    jewellery_collection = db["jewellery"]

    # Insert one test document
    test_document = {
        "id": "TEST001",
        "name": "MongoDB Test Jewellery",
        "collection": "Prototype",
        "type": "GP",
        "description": "Test document",
        "image": "test.jpeg",
        "ai_status": "ready"
    }

    result = jewellery_collection.insert_one(test_document)

    print("Test document inserted successfully!")
    print("MongoDB ID:", result.inserted_id)

except Exception as e:
    print("MongoDB operation failed:")
    print(e)

finally:
    client.close()