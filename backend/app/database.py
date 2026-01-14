from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

# Create a single, reusable client instance
client: AsyncIOMotorClient = None
database: AsyncIOMotorDatabase = None


async def connect_to_mongo():
    """Create database connection"""
    global client, database
    client = AsyncIOMotorClient(settings.MONGO_URL)
    database = client[settings.DB_NAME]
    # Test connection
    await client.admin.command('ping')
    print(f"✅ Connected to MongoDB: {settings.DB_NAME}")


async def close_mongo_connection():
    """Close database connection"""
    global client
    if client:
        client.close()
        print("✅ MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance"""
    return database

