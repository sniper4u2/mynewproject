#!/bin/bash

# Source utility functions
source scripts/utils.sh

# Create directories
echo "Creating required directories..."
mkdir -p logs tools/{osint,ss7,monitoring,exploit,geolocation} data/db

# Set up virtual environment
setup_venv

# Skip dependency installation if venv exists
if [ -d "venv" ]; then
    echo "Virtual environment already exists"
else
    echo "Installing dependencies..."
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
fi

# Configure environment for development
configure_env "dev"

# Start services in development mode
# Check if MongoDB is already running
if ! pgrep -x "mongod" > /dev/null; then
    echo "Starting MongoDB..."
    start_dev_service "mongodb"
else
    echo "MongoDB is already running"
fi

start_dev_service "influxdb"
start_dev_service "elasticsearch"
start_dev_service "redis"

# Initialize database in development mode
python3 -m src.database.init_db --dev

# Start the server in development mode
echo "Starting B13 C2 Server in development mode..."
python3 -m src.core.server --dev
