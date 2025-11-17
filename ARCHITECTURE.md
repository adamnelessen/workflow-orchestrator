# Architecture Diagrams

## System Architecture (Before)

```
┌─────────────────────────────────────┐
│         Coordinator                 │
│  ┌──────────────────────────────┐   │
│  │   StateManager (In-Memory)   │   │
│  │   - Dict[workflows]          │   │
│  │   - Dict[workers]            │   │
│  │   - Dict[jobs]               │   │
│  │   - asyncio.Queue            │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
         ↓ WebSocket
┌─────────────────────────────────────┐
│         Workers (4x)                │
└─────────────────────────────────────┘

❌ State lost on restart
❌ Single coordinator only
❌ No audit trail
```

## System Architecture (After)

```
┌──────────────────────────────────────────────────────────┐
│                      Coordinator                         │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │          StateManager (Hybrid)                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │   │
│  │  │ Memory   │  │  Redis   │  │  PostgreSQL  │   │   │
│  │  │ (Fast)   │  │ (Cache)  │  │  (Persist)   │   │   │
│  │  │          │  │          │  │              │   │   │
│  │  │ Active   │→│ Queue    │→│ Workflows    │   │   │
│  │  │ State    │←│ Locks    │←│ Jobs         │   │   │
│  │  │ WS Conn  │  │ Metrics  │  │ Workers      │   │   │
│  │  │          │  │ Workers  │  │ History      │   │   │
│  │  └──────────┘  └──────────┘  └──────────────┘   │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
         ↓ WebSocket
┌──────────────────────────────────────────────────────────┐
│                    Workers (4x)                          │
└──────────────────────────────────────────────────────────┘

✅ Survives restarts (PostgreSQL)
✅ High performance (Redis)
✅ Scalable (multi-coordinator ready)
✅ Complete audit trail
```

## Data Flow

### Write Path
```
API Request
    ↓
StateManager.add_workflow()
    ↓
┌─────────────────────────────────────┐
│ 1. Update Memory (immediate)       │
│    - self.workflows[id] = workflow  │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 2. Cache in Redis (async, ~1ms)    │
│    - Fast subsequent reads          │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 3. Persist to PostgreSQL (~5ms)    │
│    - Durable storage                │
│    - Audit trail                    │
└─────────────────────────────────────┘
```

### Read Path (Fast)
```
API Request
    ↓
StateManager.get_workflow(id)
    ↓
┌─────────────────────────────────────┐
│ 1. Check Memory                     │
│    └─ Hit? Return immediately       │
└─────────────────────────────────────┘
    ↓ Miss
┌─────────────────────────────────────┐
│ 2. Check Redis Cache                │
│    └─ Hit? Cache in memory & return │
└─────────────────────────────────────┘
    ↓ Miss
┌─────────────────────────────────────┐
│ 3. Query PostgreSQL                 │
│    └─ Cache in Redis + Memory       │
└─────────────────────────────────────┘
```

## Component Responsibilities

### Memory (In-Memory Dict)
- **Purpose**: Fastest access, hot data
- **Stores**: Active workflows, jobs, workers, WebSocket connections
- **Latency**: ~1μs
- **Persistence**: None (volatile)
- **Use Case**: Active coordinator operations

### Redis
- **Purpose**: Distributed cache and coordination
- **Stores**: 
  - Job queue (sorted set by priority)
  - Worker heartbeats (with TTL)
  - Hot data cache
  - Distributed locks
  - Real-time metrics
- **Latency**: ~0.1-1ms
- **Persistence**: Optional (RDB/AOF)
- **Use Case**: Multi-coordinator coordination, fast reads

### PostgreSQL
- **Purpose**: Durable storage and analytics
- **Stores**:
  - All workflows (complete history)
  - All jobs (with status changes)
  - Worker registry
  - Job assignments
- **Latency**: ~1-10ms
- **Persistence**: Full ACID durability
- **Use Case**: Recovery, analytics, audit trail

## Redis Data Structures

```
queue:pending_jobs         → Sorted Set (priority queue)
├─ job-123: 1              (priority 1)
├─ job-456: 2              (priority 2)
└─ job-789: 0              (priority 0, highest)

set:active_workers         → Set (live workers)
├─ worker-1
├─ worker-2
└─ worker-3

worker:heartbeat:worker-1  → String (TTL: 30s)
worker:heartbeat:worker-2  → String (TTL: 30s)

cache:workflows            → Hash
├─ workflow-1: {json}
└─ workflow-2: {json}

cache:jobs                 → Hash
├─ job-1: {json}
└─ job-2: {json}

lock:job:123              → String (TTL: 10s)
lock:workflow:456         → String (TTL: 10s)

metric:workflows_started   → Counter
metric:jobs_completed      → Counter
```

## PostgreSQL Schema

```sql
-- Workflows table
workflows
├─ id (PK)
├─ name
├─ status (enum)
├─ current_jobs (json[])
├─ completed_jobs (json[])
├─ failed_jobs (json[])
├─ created_at
└─ updated_at

-- Jobs table
jobs
├─ id (PK)
├─ workflow_id (FK, indexed)
├─ type (enum)
├─ parameters (json)
├─ status (enum)
├─ worker_id (indexed)
├─ result (json)
├─ error (text)
├─ retry_count
├─ max_retries
├─ on_success (json[])
├─ on_failure (json[])
├─ always_run (bool)
├─ created_at
└─ updated_at

-- Workers table
workers
├─ id (PK)
├─ status (enum)
├─ capabilities (json[])
├─ current_job_id
├─ last_heartbeat
└─ registered_at

-- Job assignments
job_assignments
├─ job_id (PK)
├─ worker_id (indexed)
└─ assigned_at
```

## Scaling Patterns

### Single Coordinator (Current)
```
┌──────────────┐
│ Coordinator  │
│ + State Mgr  │
│ + PostgreSQL │
│ + Redis      │
└──────────────┘
       ↓
   Workers (N)
```

### Multi-Coordinator (Future)
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Coordinator1 │  │ Coordinator2 │  │ Coordinator3 │
│ + State Mgr  │  │ + State Mgr  │  │ + State Mgr  │
└──────────────┘  └──────────────┘  └──────────────┘
       ↓                  ↓                  ↓
       └──────────────────┴──────────────────┘
                          ↓
              ┌───────────────────────┐
              │  Shared PostgreSQL    │
              │  Shared Redis Cluster │
              └───────────────────────┘
                          ↓
                    Workers (N)
```

## Migration Strategy

### Phase 1: Foundation (✅ DONE)
- Add database infrastructure
- Create hybrid StateManager
- Maintain backward compatibility

### Phase 2: Gradual Adoption
```python
# Old code (still works)
state.add_workflow(workflow)  # Memory only

# New code (with persistence)
await state.add_workflow_async(workflow)  # Memory + Redis + PostgreSQL
```

### Phase 3: Background Sync
```python
# Sync memory to database periodically
async def background_sync():
    for workflow in state.workflows.values():
        await state.postgres.save_workflow(workflow)
```

### Phase 4: Full Async
```python
# All operations use async persistence
# Coordinator becomes stateless
# Can scale horizontally
```

## Performance Characteristics

| Operation | Memory | Redis | PostgreSQL |
|-----------|--------|-------|------------|
| Read (hot) | 1μs | - | - |
| Read (warm) | - | 0.1ms | - |
| Read (cold) | - | - | 5ms |
| Write | 1μs | +1ms | +5ms |
| Recovery | N/A | Partial | Full |
| Query | Limited | Basic | Complex SQL |

## Monitoring Points

```
┌─────────────────────────────────────┐
│          Observability              │
├─────────────────────────────────────┤
│ Redis Metrics:                      │
│  - redis.get_metric("jobs_queued")  │
│  - redis.queue_length()             │
│  - redis.get_active_workers()       │
│                                     │
│ PostgreSQL Metrics:                 │
│  - Workflow completion rate         │
│  - Job success/failure ratio        │
│  - Average execution time           │
│  - Worker utilization               │
│                                     │
│ Memory Metrics:                     │
│  - Active workflows count           │
│  - Active connections count         │
│  - Queue depth                      │
└─────────────────────────────────────┘
```
