from backend.database.mongodb import test_mongodb_connection


if test_mongodb_connection():
    print("MongoDB connection successful!")
else:
    print("MongoDB connection failed!")