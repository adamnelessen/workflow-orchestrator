# E2E Testing Quick Reference

## Run Tests

```bash
make test-e2e                      # Run all E2E tests
pytest tests/e2e/ -v -m e2e        # Alternative

# Specific tests
pytest tests/e2e/test_workflow_lifecycle.py -v -s
pytest tests/e2e/ -k "parallel" -v -s
```

## Manual Environment

```bash
make test-e2e-up       # Start containers
make test-e2e-logs     # View logs
pytest tests/e2e/      # Run tests
make test-e2e-down     # Stop containers
```

## Debugging

```bash
# Check services
docker-compose -f tests/e2e/docker-compose.e2e.yml ps

# Check health
curl http://localhost:8001/health
curl http://localhost:8001/workers

# View specific logs
docker-compose -f tests/e2e/docker-compose.e2e.yml logs coordinator-e2e
```

## Troubleshooting

**Containers won't start:**
```bash
make test-e2e-down
docker system prune -f
make test-e2e-up
```

**Tests timeout:**
```bash
make test-e2e-logs  # Check for errors
```

**Port conflict (8001):**
```bash
lsof -i :8001
kill -9 <PID>
```

## Prerequisites

- Docker installed and running
- Dependencies: `make install-dev`
- Virtual environment activated
