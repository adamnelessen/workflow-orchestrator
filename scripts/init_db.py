"""Database initialization script"""
import asyncio
import os
import sys
from coordinator.db.postgres import PostgresDB
from coordinator.db.redis import RedisCache


async def init_databases():
    """Initialize PostgreSQL and Redis connections"""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator"
    )
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    print(
        f"🔧 Initializing PostgreSQL: {database_url.split('@')[1] if '@' in database_url else database_url}"
    )
    postgres = PostgresDB(database_url)
    await postgres.init_db()
    print("✅ PostgreSQL schema created successfully")

    print(f"\n🔧 Connecting to Redis: {redis_url}")
    redis = RedisCache(redis_url)
    await redis.connect()
    await redis.client.ping()
    print("✅ Redis connection successful")

    # Cleanup
    await postgres.close()
    await redis.close()

    print("\n🎉 Database initialization complete!")
    print("\nYou can now start the coordinator with:")
    print("  docker-compose up")
    print("  or")
    print("  python -m coordinator.main")


if __name__ == "__main__":
    try:
        asyncio.run(init_databases())
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
