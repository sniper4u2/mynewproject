#!/bin/bash

# Exit on error
set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root"
    exit 1
fi

# Source utility functions
source scripts/utils.sh

# Create directories
create_directories

# Set up virtual environment
setup_venv

# Install dependencies
install_dependencies

# Configure environment
configure_env

# Start services
start_service "mongodb"
start_service "influxdb"
start_service "elasticsearch"
start_service "redis"

# Initialize database
python3 -m src.database.init_db

# Start the server
echo "Starting B13 C2 Server..."
python3 -m src.core.server
