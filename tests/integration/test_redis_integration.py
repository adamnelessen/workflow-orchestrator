"""Integration tests for Redis caching operations"""
import pytest
import asyncio
from coordinator.db.redis import RedisCache
from shared.models import Workflow, Job
from shared.enums import JobStatus, JobType, WorkflowStatus
from datetime import datetime, UTC


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_cache_workflow(
    redis_cache: RedisCache, sample_workflow: Workflow
) -> None:
    """Test caching and retrieving a workflow"""
    # Cache workflow
    await redis_cache.cache_workflow(sample_workflow)
    
    # Retrieve from cache
    cached = await redis_cache.get_cached_workflow(sample_workflow.id)
    
    assert cached is not None
    assert cached["id"] == sample_workflow.id
    assert cached["name"] == sample_workflow.name
    assert cached["status"] == sample_workflow.status


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_cache_job(
    redis_cache: RedisCache, sample_job: Job
) -> None:
    """Test caching and retrieving a job"""
    # Cache job
    await redis_cache.cache_job(sample_job)
    
    # Retrieve from cache
    cached = await redis_cache.get_cached_job(sample_job.id)
    
    assert cached is not None
    assert cached["id"] == sample_job.id
    assert cached["type"] == sample_job.type
    assert cached["status"] == sample_job.status


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_invalidate_workflow(
    redis_cache: RedisCache, sample_workflow: Workflow
) -> None:
    """Test invalidating workflow cache"""
    # Cache workflow
    await redis_cache.cache_workflow(sample_workflow)
    
    # Verify it's cached
    cached = await redis_cache.get_cached_workflow(sample_workflow.id)
    assert cached is not None
    
    # Invalidate
    await redis_cache.invalidate_workflow(sample_workflow.id)
    
    # Verify it's gone
    cached = await redis_cache.get_cached_workflow(sample_workflow.id)
    assert cached is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_invalidate_job(redis_cache: RedisCache, sample_job: Job) -> None:
    """Test invalidating job cache"""
    # Cache job
    await redis_cache.cache_job(sample_job)
    
    # Verify it's cached
    cached = await redis_cache.get_cached_job(sample_job.id)
    assert cached is not None
    
    # Invalidate
    await redis_cache.invalidate_job(sample_job.id)
    
    # Verify it's gone
    cached = await redis_cache.get_cached_job(sample_job.id)
    assert cached is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_job_queue_push_pop(redis_cache: RedisCache) -> None:
    """Test job queue operations"""
    # Push jobs with different priorities
    await redis_cache.push_job("job-high", priority=10)
    await redis_cache.push_job("job-low", priority=1)
    await redis_cache.push_job("job-medium", priority=5)
    
    # Check queue length
    length = await redis_cache.queue_length()
    assert length >= 3
    
    # Pop jobs (should come out in priority order: lowest score first)
    job1 = await redis_cache.pop_job()
    assert job1 == "job-low"  # Priority 1
    
    job2 = await redis_cache.pop_job()
    assert job2 == "job-medium"  # Priority 5
    
    job3 = await redis_cache.pop_job()
    assert job3 == "job-high"  # Priority 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_worker_heartbeat(redis_cache: RedisCache) -> None:
    """Test worker heartbeat tracking"""
    worker_id = "redis-test-worker-1"
    
    # Mark worker as active with short TTL
    await redis_cache.mark_worker_active(worker_id, ttl=2)
    
    # Check worker is active
    is_active = await redis_cache.is_worker_active(worker_id)
    assert is_active is True
    
    # Check worker appears in active workers set
    active_workers = await redis_cache.get_active_workers()
    assert worker_id in active_workers
    
    # Wait for TTL to expire
    await asyncio.sleep(3)
    
    # Check worker is no longer active
    is_active = await redis_cache.is_worker_active(worker_id)
    assert is_active is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_remove_worker(redis_cache: RedisCache) -> None:
    """Test explicitly removing a worker"""
    worker_id = "redis-test-worker-2"
    
    # Mark worker as active
    await redis_cache.mark_worker_active(worker_id, ttl=30)
    
    # Verify it's active
    is_active = await redis_cache.is_worker_active(worker_id)
    assert is_active is True
    
    # Remove worker
    await redis_cache.remove_worker(worker_id)
    
    # Verify it's gone
    is_active = await redis_cache.is_worker_active(worker_id)
    assert is_active is False
    
    active_workers = await redis_cache.get_active_workers()
    assert worker_id not in active_workers


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_distributed_lock(redis_cache: RedisCache) -> None:
    """Test distributed lock operations"""
    lock_key = "test-resource"
    
    # Acquire lock
    acquired = await redis_cache.acquire_lock(lock_key, ttl=5)
    assert acquired is True
    
    # Try to acquire same lock (should fail - returns None or False)
    acquired_again = await redis_cache.acquire_lock(lock_key, ttl=5)
    assert acquired_again in (False, None)  # Redis returns None on failure
    
    # Release lock
    await redis_cache.release_lock(lock_key)
    
    # Try to acquire again (should succeed)
    acquired_after_release = await redis_cache.acquire_lock(lock_key, ttl=5)
    assert acquired_after_release is True
    
    # Clean up
    await redis_cache.release_lock(lock_key)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_metrics(redis_cache: RedisCache) -> None:
    """Test metric tracking"""
    metric_name = "test_counter"
    
    # Get initial value
    initial = await redis_cache.get_metric(metric_name)
    
    # Increment metric
    await redis_cache.increment_metric(metric_name)
    await redis_cache.increment_metric(metric_name)
    await redis_cache.increment_metric(metric_name)
    
    # Check final value
    final = await redis_cache.get_metric(metric_name)
    assert final == initial + 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_empty_queue(redis_cache: RedisCache) -> None:
    """Test popping from empty queue"""
    # Clear queue first by popping everything
    while await redis_cache.pop_job():
        pass
    
    # Pop from empty queue
    result = await redis_cache.pop_job()
    assert result is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_cache_miss(redis_cache: RedisCache) -> None:
    """Test cache miss returns None"""
    # Try to get non-existent workflow
    cached = await redis_cache.get_cached_workflow("non-existent-id")
    assert cached is None
    
    # Try to get non-existent job
    cached = await redis_cache.get_cached_job("non-existent-job-id")
    assert cached is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
