#!/bin/bash
# start-services.sh - Start Flask + Celery + Celery Beat + Flower
# Usage: chmod +x start-services.sh && ./start-services.sh

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Starting Interview-ProAI Services                        ║"
echo "║  Flask + Celery + Celery Beat + Flower Monitoring        ║"
echo "╚════════════════════════════════════════════════════════════╝"

# Load environment variables
if [ ! -f ".env" ]; then
    echo "❌ .env file not found! Copy from .env.example"
    exit 1
fi

export $(cat .env | grep -v '#' | xargs)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check dependencies
echo -e "\n${YELLOW}Checking dependencies...${NC}"

if ! command -v redis-cli &> /dev/null; then
    echo -e "${RED}❌ Redis not found!${NC}"
    echo "   macOS: brew install redis"
    echo "   Ubuntu: sudo apt-get install redis-server"
    echo "   Or use Docker: docker-compose up -d redis"
    exit 1
fi

if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python not found!${NC}"
    exit 1
fi

# Start Redis (if not running)
if ! redis-cli ping &> /dev/null; then
    echo -e "${YELLOW}Starting Redis...${NC}"
    redis-server --daemonize yes > /dev/null 2>&1
    sleep 1
    redis-cli ping > /dev/null && echo -e "${GREEN}✅ Redis started${NC}"
fi

# Kill any existing processes
echo -e "\n${YELLOW}Cleaning up old processes...${NC}"
pkill -f "celery worker" || true
pkill -f "celery beat" || true
pkill -f "flower" || true

echo -e "${GREEN}✅ Cleaned${NC}"

# Start Celery worker (AI tasks queue)
echo -e "\n${YELLOW}Starting Celery Worker (AI tasks)...${NC}"
celery -A celery_app worker --loglevel=info -Q ai --concurrency=2 --logfile=logs/celery_worker.log --pidfile=logs/celery_worker.pid &
CELERY_PID=$!
sleep 2
echo -e "${GREEN}✅ Celery Worker (AI) started (PID: $CELERY_PID)${NC}"

# Start Celery worker (Email tasks)
echo -e "${YELLOW}Starting Celery Worker (Email tasks)...${NC}"
celery -A celery_app worker --loglevel=info -Q email --concurrency=2 --logfile=logs/celery_email.log --pidfile=logs/celery_email.pid &
CELERY_EMAIL_PID=$!
sleep 2
echo -e "${GREEN}✅ Celery Worker (Email) started (PID: $CELERY_EMAIL_PID)${NC}"

# Start Celery Beat (scheduler for periodic tasks)
echo -e "${YELLOW}Starting Celery Beat (Scheduler)...${NC}"
celery -A celery_app beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler --logfile=logs/celery_beat.log --pidfile=logs/celery_beat.pid &
CELERY_BEAT_PID=$!
sleep 2
echo -e "${GREEN}✅ Celery Beat started (PID: $CELERY_BEAT_PID)${NC}"

# Start Flower (monitoring dashboard)
echo -e "${YELLOW}Starting Flower (Celery monitoring)...${NC}"
celery -A celery_app flower --port=5555 --logfile=logs/flower.log &
FLOWER_PID=$!
sleep 2
echo -e "${GREEN}✅ Flower started (PID: $FLOWER_PID) - Visit http://localhost:5555${NC}"

# Start Flask development server
echo -e "${YELLOW}Starting Flask development server...${NC}"
python app.py &
FLASK_PID=$!
sleep 2
echo -e "${GREEN}✅ Flask started (PID: $FLASK_PID) - Visit http://localhost:5000${NC}"

echo -e "\n${GREEN}✅ All services running!${NC}"

echo -e """
╔════════════════════════════════════════════════════════════╗
║  Service Status                                           ║
├────────────────────────────────────────────────────────────┤
║  Flask:        http://localhost:5000                      ║
║  Flower:       http://localhost:5555                      ║
║  Redis:        localhost:6379                             ║
╚════════════════════════════════════════════════════════════╝

Press Ctrl+C to stop all services...

Logs location:
  logs/celery_worker.log   - AI tasks worker
  logs/celery_email.log    - Email tasks worker
  logs/celery_beat.log     - Scheduler
  logs/flower.log          - Flower dashboard
"""

# Keep script running
wait
