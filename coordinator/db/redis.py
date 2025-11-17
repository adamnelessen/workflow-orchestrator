"""Redis cache and queue operations"""
import json
from typing import Optional, List, Any, Dict
import redis.asyncio as redis
from shared.models import Workflow, Job, Worker


class RedisCache:
    """Redis cache and queue manager"""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        self.client = await redis.from_url(self.redis_url,
                                           decode_responses=True)

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()

    # Job queue operations
    async def push_job(self, job_id: str, priority: int = 0) -> None:
        """Push a job to the pending queue"""
        await self.client.zadd("queue:pending_jobs", {job_id: priority})

    async def pop_job(self) -> Optional[str]:
        """Pop highest priority job from queue"""
        result = await self.client.zpopmin("queue:pending_jobs", count=1)
        if result:
            return result[0][0]  # Returns (job_id, score)
        return None

    async def queue_length(self) -> int:
        """Get pending job queue length"""
        return await self.client.zcard("queue:pending_jobs")

    # Worker presence tracking
    async def mark_worker_active(self, worker_id: str, ttl: int = 30) -> None:
        """Mark worker as active with TTL"""
        await self.client.setex(f"worker:heartbeat:{worker_id}", ttl, "1")
        await self.client.sadd("set:active_workers", worker_id)

    async def is_worker_active(self, worker_id: str) -> bool:
        """Check if worker is active"""
        return await self.client.exists(f"worker:heartbeat:{worker_id}") > 0

    async def get_active_workers(self) -> List[str]:
        """Get all active worker IDs"""
        return list(await self.client.smembers("set:active_workers"))

    async def remove_worker(self, worker_id: str) -> None:
        """Remove worker from active set"""
        await self.client.delete(f"worker:heartbeat:{worker_id}")
        await self.client.srem("set:active_workers", worker_id)

    # Caching operations
    async def cache_workflow(self, workflow: Workflow) -> None:
        """Cache workflow in Redis"""
        await self.client.hset(
            "cache:workflows",
            workflow.id,
            workflow.model_dump_json(),
        )

    async def get_cached_workflow(self, workflow_id: str) -> Optional[Dict]:
        """Get cached workflow"""
        data = await self.client.hget("cache:workflows", workflow_id)
        return json.loads(data) if data else None

    async def cache_job(self, job: Job) -> None:
        """Cache job in Redis"""
        await self.client.hset(
            "cache:jobs",
            job.id,
            job.model_dump_json(),
        )

    async def get_cached_job(self, job_id: str) -> Optional[Dict]:
        """Get cached job"""
        data = await self.client.hget("cache:jobs", job_id)
        return json.loads(data) if data else None

    async def invalidate_workflow(self, workflow_id: str) -> None:
        """Invalidate workflow cache"""
        await self.client.hdel("cache:workflows", workflow_id)

    async def invalidate_job(self, job_id: str) -> None:
        """Invalidate job cache"""
        await self.client.hdel("cache:jobs", job_id)

    # Distributed locks
    async def acquire_lock(self, lock_key: str, ttl: int = 10) -> bool:
        """Acquire a distributed lock"""
        return await self.client.set(f"lock:{lock_key}", "1", nx=True, ex=ttl)

    async def release_lock(self, lock_key: str) -> None:
        """Release a distributed lock"""
        await self.client.delete(f"lock:{lock_key}")

    # Metrics and monitoring
    async def increment_metric(self, metric: str) -> None:
        """Increment a counter metric"""
        await self.client.incr(f"metric:{metric}")

    async def get_metric(self, metric: str) -> int:
        """Get metric value"""
        value = await self.client.get(f"metric:{metric}")
        return int(value) if value else 0
