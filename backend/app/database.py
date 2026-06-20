from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
from app.config import settings
import logging

logger = logging.getLogger(__name__)

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    await create_indexes()
    logger.info(f"Connected to MongoDB: {settings.DATABASE_NAME}")


async def disconnect_db():
    global client
    if client:
        client.close()
        logger.info("Disconnected from MongoDB")


async def create_indexes():
    # users
    await db.users.create_index([("email", ASCENDING)], unique=True)

    # expenses
    await db.expenses.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
    await db.expenses.create_index([("user_id", ASCENDING), ("category", ASCENDING)])
    await db.expenses.create_index(
        [("user_id", ASCENDING), ("date", DESCENDING), ("category", ASCENDING)]
    )
    await db.expenses.create_index([("title", "text"), ("description", "text")])

    # budgets
    await db.budgets.create_index(
        [("user_id", ASCENDING), ("year", ASCENDING), ("month", ASCENDING)],
        unique=True,
    )

    # ocr_jobs
    await db.ocr_jobs.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await db.ocr_jobs.create_index([("status", ASCENDING)])

    # insights_cache — TTL index
    await db.insights_cache.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
    await db.insights_cache.create_index(
        [("user_id", ASCENDING), ("year", ASCENDING), ("month", ASCENDING)],
        unique=True,
    )

    logger.info("Database indexes created")


def get_db():
    return db
