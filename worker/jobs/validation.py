from worker.jobs.base import BaseJob
import asyncio
from datetime import datetime, UTC
import logging
import random

logger = logging.getLogger(__name__)


class Validation(BaseJob):

    async def execute(self) -> dict:
        schema = self.parameters.get("schema", "default")
        logger.info(f"Validating with schema: {schema}")

        # Simulate validation
        await asyncio.sleep(1)

        # Randomly succeed or fail for demonstration
        success = random.random() > 0.2  # 80% success rate
        if not success:
            raise Exception("Validation failed")

        return {
            "schema": schema,
            "valid": success,
            "timestamp": datetime.now(UTC).isoformat()
        }
