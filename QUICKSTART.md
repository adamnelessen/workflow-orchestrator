# Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies
```bash
make install
```

### Step 2: Setup Databases (Optional but Recommended)
```bash
make db-init
```

This will:
- Start PostgreSQL and Redis in Docker
- Create database schema
- Verify connections

### Step 3: Choose Your Path

#### A. Run the Demo
```bash
make db-demo
```
See database persistence in action!

#### B. Start the Full System
```bash
make docker-up
```
Starts coordinator + 4 workers + databases

#### C. Run Tests
```bash
make test
```

---

## 📖 Available Commands

Run `make help` to see all commands, or check key ones below:

### Database Commands
```bash
make db-init          # Setup databases
make db-demo          # Run persistence demo
make db-test          # Test database integration
make docker-db-only   # Start only databases
```

### Docker Commands
```bash
make docker-build     # Build images
make docker-up        # Start all services
make docker-down      # Stop all services
make docker-logs      # View logs
```

### Testing Commands
```bash
make test             # Run all tests
make test-unit        # Unit tests only
make test-integration # Integration tests
make test-e2e         # End-to-end tests
make test-cov         # With coverage report
make lint             # Run linters
```

### Development Commands
```bash
make install          # Install dependencies
make install-dev      # Install with dev tools
make clean            # Clean up
make reinstall        # Fresh install
```

---

## 🎯 Common Workflows

### First Time Setup
```bash
make install
make db-init
make db-demo
```

### Daily Development
```bash
# Start databases
make docker-db-only

# Run coordinator locally (in one terminal)
export DATABASE_URL=postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator
export REDIS_URL=redis://localhost:6379/0
python -m coordinator.main

# Run a worker (in another terminal)
export WORKER_ID=dev-worker-1
export COORDINATOR_URL=ws://localhost:8000/workers
python -m worker.main
```

### Testing Workflow
```bash
# Unit tests
make test-unit

# Test with databases
make db-test

# Full test suite
make test
```

### Production Deployment
```bash
# Build and start everything
make docker-build
make docker-up

# Submit a workflow
make submit-workflow

# Monitor logs
make docker-logs

# Stop when done
make docker-down
```

---

## 📚 Documentation

- **[README.md](README.md)** - Main documentation
- **[DATABASE_SETUP.md](DATABASE_SETUP.md)** - Database configuration guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and diagrams
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - What was implemented
- **[TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)** - Complete testing guide

---

## ❓ FAQ

### Do I need databases to run this?
No! The system works perfectly without databases using in-memory storage. Databases add persistence and scalability.

### How do I run without databases?
Simply don't set `DATABASE_URL` or `REDIS_URL`, and the system automatically falls back to in-memory mode.

### What if I only want PostgreSQL or only Redis?
Set only the environment variable you want. The system adapts to whatever backends are available.

### Can I use external databases?
Yes! Just point `DATABASE_URL` and `REDIS_URL` to your external instances.

### How do I reset everything?
```bash
make docker-down
make clean
make reinstall
make db-init
```

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Check what's using ports
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :8000  # Coordinator

# Stop conflicting services
make docker-down
```

### Database Connection Failed
```bash
# Check database status
make docker-db-only

# View logs
docker-compose logs postgres
docker-compose logs redis
```

### Import Errors
```bash
# Reinstall dependencies
make reinstall
```

### Tests Failing
```bash
# Clean and reinstall
make clean
make install-dev
make test
```

---

## 🎉 Next Steps

1. ✅ Run `make help` to see all commands
2. ✅ Run `make db-demo` to see persistence
3. ✅ Read [DATABASE_SETUP.md](DATABASE_SETUP.md) for details
4. ✅ Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
5. ✅ Start building your workflows!

---

**Need Help?** Check the full documentation or run `make help`.
