import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


load_dotenv()

# Defaults work for local MongoDB.
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "fitness_db")

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]


async def check_db() -> None:
    """Fail-fast check so you instantly know Mongo is reachable."""
    await client.admin.command("ping")
    print("MongoDB connection successful!")


async def create_indexes() -> None:
    """Indexes required by the rubric (unique + compound)."""
    await db.workouts.create_index([("user_id", 1), ("date", -1)])
    await db.users.create_index("email", unique=True)
    print("Indexes created.")
