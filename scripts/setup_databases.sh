#!/bin/bash
# Quick start script for database-enabled workflow orchestrator

set -e

echo "🚀 Workflow Orchestrator - Database Setup"
echo "=========================================="
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Desktop."
    exit 1
fi

echo "📦 Step 1: Installing Python dependencies..."
pip install -e . > /dev/null 2>&1
echo "✅ Dependencies installed"
echo ""

echo "🐳 Step 2: Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis
echo "✅ Databases starting..."
echo ""

echo "⏳ Step 3: Waiting for databases to be ready..."
sleep 5

# Wait for PostgreSQL
echo "   Checking PostgreSQL..."
until docker-compose exec -T postgres pg_isready -U workflow > /dev/null 2>&1; do
    echo "   Waiting for PostgreSQL..."
    sleep 2
done
echo "✅ PostgreSQL is ready"

# Wait for Redis
echo "   Checking Redis..."
until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    echo "   Waiting for Redis..."
    sleep 2
done
echo "✅ Redis is ready"
echo ""

echo "🔧 Step 4: Initializing database schema..."
python scripts/init_db.py
echo ""

echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Start the full system:"
echo "     docker-compose up"
echo ""
echo "  2. Or run the demo:"
echo "     python examples/database_demo.py"
echo ""
echo "  3. Or start just the coordinator locally:"
echo "     export DATABASE_URL=postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator"
echo "     export REDIS_URL=redis://localhost:6379/0"
echo "     python -m coordinator.main"
echo ""
echo "📖 See DATABASE_SETUP.md for more information"
