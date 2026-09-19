#!/bin/bash

# Start script for Worker Service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Worker Service...${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Copying from .env.example${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please update .env with your configuration before running in production${NC}"
fi

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oP '(?<=Python )\d+\.\d+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo -e "${RED}Error: Python $required_version or higher is required${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Wait for RabbitMQ (if running with Docker)
if [ ! -z "$RABBITMQ_HOST" ] && [ "$RABBITMQ_HOST" != "localhost" ]; then
    echo -e "${YELLOW}Waiting for RabbitMQ to be ready...${NC}"
    timeout=30
    count=0
    until nc -z $RABBITMQ_HOST ${RABBITMQ_PORT:-5672} || [ $count -eq $timeout ]; do
        sleep 1
        count=$((count + 1))
    done

    if [ $count -eq $timeout ]; then
        echo -e "${RED}Error: RabbitMQ not available after ${timeout} seconds${NC}"
        exit 1
    fi
    echo -e "${GREEN}RabbitMQ is ready${NC}"
fi

# Wait for PostgreSQL (if running with Docker)
if [ ! -z "$DATABASE_HOST" ] && [ "$DATABASE_HOST" != "localhost" ]; then
    echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
    timeout=30
    count=0
    until nc -z $DATABASE_HOST ${DATABASE_PORT:-5432} || [ $count -eq $timeout ]; do
        sleep 1
        count=$((count + 1))
    done

    if [ $count -eq $timeout ]; then
        echo -e "${RED}Error: PostgreSQL not available after ${timeout} seconds${NC}"
        exit 1
    fi
    echo -e "${GREEN}PostgreSQL is ready${NC}"
fi

# Run the worker
echo -e "${GREEN}Starting worker service...${NC}"
python -m app.main
