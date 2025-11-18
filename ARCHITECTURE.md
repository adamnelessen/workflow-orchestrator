# Workflow Orchestrator Architecture

A production-grade distributed workflow orchestration system built on hybrid storage architecture for resilience, performance, and horizontal scalability.

## Core Tenets

**Performance Through Layering**: Three-tier storage (memory → Redis → PostgreSQL) optimizes for the common case while preserving durability.

**Resilience by Design**: Automatic state reconstruction from persistent storage ensures zero data loss across coordinator restarts.

**Horizontal Scalability**: Shared state layer (PostgreSQL + Redis) enables multi-coordinator deployments without coordination complexity.

**Operational Simplicity**: Graceful degradation to in-memory mode when databases unavailable; no mandatory infrastructure dependencies.

## System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     Coordinator                            │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │            StateManager (Hybrid)                     │ │
│  │                                                      │ │
│  │   Memory          Redis           PostgreSQL        │ │
│  │   ├─ Hot Cache    ├─ Job Queue    ├─ Workflows      │ │
│  │   ├─ WebSockets   ├─ Locks        ├─ Jobs           │ │
│  │   ├─ Active State ├─ Heartbeats   ├─ Workers        │ │
│  │   └─ ~1μs         ├─ Metrics      ├─ Audit Trail    │ │
│  │                   └─ ~0.1-1ms     └─ ~5ms ACID      │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  REST API (FastAPI) ──┐                                   │
│  WebSocket Gateway ───┼── Job Scheduler                   │
│  Health Monitoring ────┘                                   │
└────────────────────────────────────────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          │      WebSocket (wss://)     │
          └──────────────┬──────────────┘
                         │
          ┌──────────────┴──────────────┐
          │       Worker Pool (N)       │
          │  ┌───────┐  ┌───────┐       │
          │  │Worker1│  │Worker2│  ...  │
          │  │ Jobs: │  │ Jobs: │       │
          │  │ •Val  │  │ •Proc │       │
          │  │ •Int  │  │ •Clnp │       │
          │  └───────┘  └───────────┘   │
          └─────────────────────────────┘
```

## Data Flow Patterns

### Write Path (Optimized for Consistency)
```
API Request → StateManager
    │
    ├─→ Memory      (immediate, ~1μs)
    ├─→ Redis       (async, ~1ms)    
    └─→ PostgreSQL  (durable, ~5ms)
```

### Read Path (Optimized for Latency)
```
Query → Memory? ────Yes────→ Return (~1μs)
         │
         No
         ↓
     Redis? ────Yes────→ Cache → Return (~0.1ms)
         │
         No
         ↓
     PostgreSQL ────→ Cache All Tiers → Return (~5ms)
```

## Storage Layer Responsibilities

| Layer | Purpose | Latency | Durability | Scale Strategy |
|-------|---------|---------|------------|----------------|
| **Memory** | Hot path, WebSocket state | ~1μs | Volatile | Vertical (single coordinator) |
| **Redis** | Distributed coordination, caching | ~0.1-1ms | Optional AOF | Horizontal (Redis Cluster) |
| **PostgreSQL** | Source of truth, analytics | ~5ms | ACID | Replication + Sharding |

### Memory
- Active workflow execution state
- WebSocket connections and routing
- Scheduler work queues
- Instant lookups for hot operations

### Redis
```
queue:pending_jobs         → Sorted Set (priority-based)
set:active_workers         → Set (live registration)
worker:heartbeat:{id}      → String + TTL (30s)
cache:workflows:{id}       → Hash (hot data)
lock:job:{id}              → String + TTL (distributed locks)
metric:*                   → Counters (real-time observability)
```

### PostgreSQL
```sql
workflows          → Full workflow lifecycle + history
jobs               → Job definitions, state, results
workers            → Worker registry, capabilities
job_assignments    → Audit trail for job execution
```

## Core Components

### StateManager
Orchestrates three-tier storage with transparent caching and automatic state reconstruction.

**Key Operations**:
- `add_workflow()`: Write to all layers
- `get_workflow()`: Read with cache population
- `_rebuild_from_db()`: Automatic recovery on startup

### Scheduler
Assigns jobs to workers based on capability matching and load distribution.

**Algorithms**:
- Priority queue (Redis sorted sets)
- Capability-based routing
- Load-aware distribution

### WorkerRegistry
Maintains live worker inventory with automatic cleanup via TTL-based heartbeats.

**Features**:
- WebSocket lifecycle management
- Heartbeat monitoring (30s TTL)
- Capability tracking

### WorkflowEngine
Executes workflow DAGs with dependency resolution and failure handling.

**Capabilities**:
- Conditional execution (`on_success`, `on_failure`)
- Parallel job execution
- Retry logic with exponential backoff
- Always-run cleanup jobs

## Resilience Mechanisms

### Coordinator Restart
```
Crash → Restart → _rebuild_from_db()
    │
    ├─→ Load workflows from PostgreSQL
    ├─→ Load workers from PostgreSQL  
    ├─→ Rebuild cache (Redis + Memory)
    └─→ Resume execution (< 1s)
```

### Worker Failure
```
Heartbeat Miss (>30s) → Mark Inactive
    │
    ├─→ Reassign in-flight jobs
    ├─→ Update workflow state
    └─→ Log failure for audit
```

### Database Unavailability
```
Connection Failure → Graceful Degradation
    │
    ├─→ Memory-only mode (in-memory queue)
    ├─→ Warning logs
    └─→ Automatic reconnect attempts
```

## Scalability Architecture

### Current: Single Coordinator
- 1 coordinator handles all workflows
- N workers via WebSocket fan-out
- Shared databases for persistence

### Future: Multi-Coordinator
```
Load Balancer
    │
    ├─→ Coordinator1 ┐
    ├─→ Coordinator2 ├─→ Shared PostgreSQL
    └─→ Coordinator3 ┘   Shared Redis Cluster
            │
            └─→ Worker Pool (M × N)
```

**Coordination via**:
- PostgreSQL: Workflow ownership (row-level locks)
- Redis: Distributed locks, pub/sub for events
- Leader election: Redis-based or external (Consul, etcd)

## Performance Profile

| Metric | Value | Notes |
|--------|-------|-------|
| Hot read | 1μs | Memory lookup |
| Warm read | 0.1-1ms | Redis cache hit |
| Cold read | 5ms | PostgreSQL query |
| Workflow submission | 10ms | Full write path |
| Job assignment | 1-2ms | Redis queue ops |
| Coordinator restart | <1s | State rebuild |
| Worker connection | <100ms | WebSocket handshake |

## Monitoring & Observability

```python
# Redis Metrics (Real-time)
jobs_queued = redis.get_metric("jobs_queued")
active_workers = redis.get_active_workers()

# PostgreSQL Analytics (Historical)
completion_rate = db.query("""
    SELECT COUNT(*) FILTER (WHERE status = 'completed')
    FROM workflows WHERE created_at > NOW() - INTERVAL '1 hour'
""")

# Memory Stats (Operational)
active_workflows = len(state_manager.workflows)
websocket_connections = len(worker_registry.connections)
```

## Project Structure

```
workflow-orchestrator/
├── coordinator/
│   ├── main.py              # FastAPI app, startup/shutdown
│   ├── api/                 # REST endpoints
│   │   ├── workflows.py
│   │   ├── jobs.py
│   │   └── workers.py
│   ├── core/
│   │   ├── state_manager.py      # Three-tier state management
│   │   ├── scheduler.py          # Job assignment logic
│   │   ├── worker_registry.py    # WebSocket connections
│   │   └── workflow_engine.py    # DAG execution
│   ├── db/
│   │   ├── postgres.py           # PostgreSQL client
│   │   └── redis.py              # Redis client
│   └── utils/
│       └── workflow_parser.py    # YAML → DAG conversion
├── worker/
│   ├── main.py              # Worker event loop
│   └── jobs/                # Job type implementations
│       ├── validation.py
│       ├── processing.py
│       ├── integration.py
│       └── cleanup.py
├── shared/
│   ├── models.py            # Pydantic models
│   ├── enums.py             # Status enums
│   └── messages.py          # WebSocket protocol
├── client/
│   └── workflow_client.py   # Python SDK
└── tests/
    ├── unit/                # Component tests
    ├── integration/         # API + DB tests
    └── e2e/                 # Full-stack Docker tests
```

## Technology Stack

- **API Framework**: FastAPI (async, OpenAPI docs)
- **WebSocket**: Native Python `websockets` with reconnect logic
- **Databases**: PostgreSQL 16 (persistence), Redis 7 (cache/coordination)
- **Serialization**: Pydantic v2 (validation + serialization)
- **Testing**: pytest + Docker Compose (40+ E2E tests)
- **Deployment**: Docker + docker-compose
