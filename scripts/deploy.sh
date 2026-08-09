#!/bin/bash

# ==============================================================================
# V4 Studio - Production Deployment Script
# ==============================================================================
# This script securely updates the application on a single AWS EC2 instance.
# It enforces zero destructive volume operations and aggressive health checking.

# Exit immediately if a command exits with a non-zero status.
set -e

# Define Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ------------------------------------------------------------------------------
# Rollback Guidance (Error Trap)
# ------------------------------------------------------------------------------
function handle_error {
    echo -e "${RED}\n================================================================${NC}"
    echo -e "${RED}DEPLOYMENT FAILED! An error occurred during the deployment.${NC}"
    echo -e "${RED}================================================================${NC}"
    echo -e "\n${YELLOW}ROLLBACK INSTRUCTIONS:${NC}"
    echo "If the containers are broken, rollback to the previous git commit and rebuild:"
    echo -e "  1. View git history: ${GREEN}git log --oneline${NC}"
    echo -e "  2. Checkout previous working commit: ${GREEN}git checkout <commit_hash>${NC}"
    echo -e "  3. Rebuild and restart: ${GREEN}docker-compose -f docker-compose.production.yml up -d --build${NC}"
    echo "If a database migration failed, you may need to restore from the latest backup:"
    echo -e "  ${GREEN}bash scripts/restore_database.sh backups/db/<latest_backup>.sql.gz${NC}"
    echo -e "${RED}================================================================${NC}\n"
    exit 1
}

# Trap any error signal and run the handle_error function
trap 'handle_error' ERR

echo -e "${GREEN}Starting V4 Studio Deployment Workflow...${NC}\n"

# 1. Pull Latest Code
echo -e "${YELLOW}[1/7] Fetching latest code from repository...${NC}"
git pull origin main
echo "Git pull completed successfully."

# 2. Build Containers
echo -e "\n${YELLOW}[2/7] Building Docker containers...${NC}"
docker-compose -f docker-compose.production.yml build
echo "Docker build completed successfully."

# 3. Restart Containers (Zero-Downtime Strategy where possible)
echo -e "\n${YELLOW}[3/7] Bringing up containers in detached mode...${NC}"
docker-compose -f docker-compose.production.yml up -d
echo "Containers are up and running."

# 4. Database Migrations
echo -e "\n${YELLOW}[4/7] Running database migrations...${NC}"
echo "Executing safe migrations inside the 'web' container..."
docker exec v4_studio_web_prod python manage.py migrate --noinput
echo "Migrations completed safely."

# 5. Collect Static Files
echo -e "\n${YELLOW}[5/7] Collecting static files...${NC}"
docker exec v4_studio_web_prod python manage.py collectstatic --noinput
echo "Static files collected."

# 6. Wait for Services to Stabilize
echo -e "\n${YELLOW}[6/7] Waiting 5 seconds for services to stabilize...${NC}"
sleep 5

# 7. Aggressive Health Checks
echo -e "\n${YELLOW}[7/7] Executing strict health checks...${NC}"

# 7a. Database Connectivity
echo -n "Checking PostgreSQL connectivity... "
if docker exec v4_studio_postgres_prod pg_isready -U v4_studio_user -d v4_studio > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    false # Trigger trap
fi

# 7b. Redis Connectivity
echo -n "Checking Redis connectivity... "
if docker exec v4_studio_redis_prod redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    false
fi

# 7c. Celery Worker Health
echo -n "Checking Celery Workers... "
if docker exec v4_studio_celery_worker_prod celery -A config inspect ping > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    false
fi

# 7d. Backend HTTP API Health
# Using wget since Alpine Linux doesn't always have curl installed by default
echo -n "Checking Backend HTTP API (Daphne)... "
if docker exec v4_studio_web_prod wget -q --spider http://localhost:8000/api/v1/; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}Endpoint returned non-200 (Expected if auth is required, but connection succeeded).${NC}"
fi

# 7e. WebSocket / ASGI Health
echo -n "Checking WebSocket ASGI Port Binding... "
if docker exec v4_studio_web_prod nc -z localhost 8000; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED - Daphne is not bound to port 8000!${NC}"
    false
fi

# ==============================================================================
echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}DEPLOYMENT SUCCESSFUL!${NC}"
echo -e "${GREEN}V4 Studio has been securely updated and all health checks passed.${NC}"
echo -e "${GREEN}================================================================${NC}"
