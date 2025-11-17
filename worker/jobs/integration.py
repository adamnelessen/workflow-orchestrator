from worker.jobs.base import BaseJob
import asyncio
from datetime import datetime, UTC
import logging
import random

logger = logging.getLogger(__name__)


class Integration(BaseJob):

    async def execute(self) -> dict:
        endpoint = self.parameters.get("endpoint", "external-api")
        recipient = self.parameters.get("recipient")

        logger.info(f"Calling integration endpoint: {endpoint}")

        # Simulate integration call
        await asyncio.sleep(2)

        # Randomly succeed or fail for demonstration
        success = random.random() > 0.4  # 60% success rate
        if not success:
            raise Exception("Integration call failed")

        return {
            "endpoint": endpoint,
            "recipient": recipient,
            "status": "sent",
            "timestamp": datetime.now(UTC).isoformat()
        }
