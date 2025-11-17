# Testing Checklist

## Quick Validation

### ✅ Before Starting
- [ ] Docker Desktop is running
- [ ] Python 3.11+ is installed
- [ ] No services running on ports 5432, 6379, 8000

### ✅ Installation
```bash
# Option 1: Using Make (recommended)
make db-init

# Option 2: Manual installation
pip install -e .
./scripts/setup_databases.sh
```

### ✅ Verify Infrastructure
```bash
# Check PostgreSQL (should show 4 tables)
docker-compose exec postgres psql -U workflow -d workflow_orchestrator -c "\dt"

# Check Redis (should return PONG)
docker-compose exec redis redis-cli ping

# Or use Make command to start just databases
make docker-db-only
```

### ✅ Test In-Memory Mode (Backward Compatibility)
```bash
# Start coordinator without databases
unset DATABASE_URL
unset REDIS_URL
python -m coordinator.main
```

Expected output:
```
INFO:__main__:Running with in-memory state only
INFO:__main__:Coordinator started - WebSocket server ready
```

### ✅ Test Database Mode
```bash
# Set environment variables
export DATABASE_URL=postgresql+asyncpg://workflow:workflow_dev@localhost:5432/workflow_orchestrator
export REDIS_URL=redis://localhost:6379/0

# Start coordinator
python -m coordinator.main
```

Expected output:
```
INFO:__main__:Initializing state manager with backends (DB: True, Redis: True)
INFO:__main__:Coordinator started - WebSocket server ready
```

### ✅ Run Demo
```bash
# Using Make (easiest)
make db-demo

# Or manually
docker-compose up -d postgres redis
python examples/database_demo.py
```

Expected output:
```
✅ Connected to PostgreSQL and Redis
💾 Saving workflow: demo-workflow-001
✅ Workflow saved to PostgreSQL and cached in Redis
💥 Simulating coordinator crash (clearing memory)...
🔄 Recovering workflow from database...
✅ Workflow recovered successfully!
🎉 Database persistence working correctly!
```

### ✅ Run Unit Tests
```bash
# Using Make
make db-test

# Or directly with pytest
pytest tests/unit/test_state_manager_db.py -v
```

Expected:
```
test_state_manager_in_memory_mode PASSED
test_state_manager_job_assignments PASSED
test_state_manager_has_async_methods PASSED
```

### ✅ Run Full System
```bash
# Using Make
make docker-up

# In another terminal, submit a workflow
make submit-workflow

# View logs
make docker-logs

# Stop when done
make docker-down
```

Expected:
- Coordinator starts on port 8000
- 4 workers connect via WebSocket
- Workflow executes successfully
- Data persists in PostgreSQL

### ✅ Test Persistence
```bash
# 1. Start system and submit workflow
docker-compose up -d
python examples/submit_workflow.py

# 2. Stop coordinator (simulate crash)
docker-compose stop coordinator

# 3. Check database has data
docker-compose exec postgres psql -U workflow -d workflow_orchestrator \
  -c "SELECT id, name, status FROM workflows;"

# 4. Restart coordinator
docker-compose up -d coordinator

# Expected: Coordinator recovers state from database
```

### ✅ Test Redis Queue
```bash
# Connect to Redis
docker-compose exec redis redis-cli

# Check queue
ZCARD queue:pending_jobs

# Check active workers
SMEMBERS set:active_workers

# Check metrics
GET metric:workflows_started
```

## Manual Testing Scenarios

### Scenario 1: Crash Recovery
1. Start system: `docker-compose up -d`
2. Submit workflow: `python examples/submit_workflow.py`
3. Kill coordinator: `docker-compose kill coordinator`
4. Check DB: `docker-compose exec postgres psql ...`
5. Restart: `docker-compose up -d coordinator`
6. Verify workflow continues ✅

### Scenario 2: Worker Failure
1. Start system with 4 workers
2. Submit workflow
3. Kill one worker: `docker-compose kill worker-1`
4. Redis should detect worker down (TTL expires)
5. Scheduler should reassign jobs ✅

### Scenario 3: Database Unavailable
1. Start coordinator without DATABASE_URL
2. System should work in memory-only mode ✅
3. Performance should be unchanged ✅

### Scenario 4: Redis Unavailable
1. Start with DATABASE_URL but no REDIS_URL
2. System should use PostgreSQL only ✅
3. Slower but fully functional ✅

## Performance Tests

### Latency Test
```python
import time
from coordinator.core.state_manager import state_manager

state = state_manager()

# Test memory access
start = time.perf_counter()
for _ in range(1000):
    state.get_workflow("test-id")
memory_time = (time.perf_counter() - start) / 1000
print(f"Memory access: {memory_time*1000:.3f}ms")

# Expected: <0.001ms per access
```

### Throughput Test
```bash
# Submit 100 workflows
for i in {1..100}; do
  python examples/submit_workflow.py &
done
wait

# Check completion
docker-compose exec postgres psql -U workflow -d workflow_orchestrator \
  -c "SELECT status, COUNT(*) FROM workflows GROUP BY status;"
```

## Troubleshooting

### PostgreSQL Connection Failed
```bash
# Check if running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart
docker-compose restart postgres
```

### Redis Connection Failed
```bash
# Check if running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping

# Restart
docker-compose restart redis
```

### Import Errors
```bash
# Reinstall in development mode
pip install -e .

# Check dependencies
pip list | grep -E "sqlalchemy|redis|asyncpg"
```

### Port Conflicts
```bash
# Check what's using ports
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :8000  # Coordinator

# Kill conflicting processes or change ports in docker-compose.yml
```

## Success Criteria

- [x] Docker services start successfully
- [x] Database schema initializes
- [x] Coordinator starts with/without databases
- [x] Workers connect via WebSocket
- [x] Workflows execute end-to-end
- [x] Data persists in PostgreSQL
- [x] Redis caching works
- [x] System recovers from crashes
- [x] Unit tests pass
- [x] No breaking changes to existing code

## Next Steps After Validation

1. **Run integration tests**: `pytest tests/integration/ -v`
2. **Run E2E tests**: `pytest tests/e2e/ -v`
3. **Load test**: Submit 1000 workflows
4. **Monitor**: Check PostgreSQL and Redis metrics
5. **Production**: Deploy with external databases

---

**Report Issues**: If any test fails, check logs:
```bash
docker-compose logs coordinator
docker-compose logs postgres
docker-compose logs redis
```
