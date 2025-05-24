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

# Stop services
function stop_service {
    local service_name=$1
    
    echo "Stopping $service_name..."
    if systemctl is-active --quiet $service_name; then
        systemctl stop $service_name
        if [ $? -eq 0 ]; then
            echo "$service_name stopped successfully"
        else
            echo "Failed to stop $service_name"
        fi
    else
        echo "$service_name is not running"
    fi
}

# Stop required services
stop_service "mongodb"
stop_service "influxdb"
stop_service "elasticsearch"
stop_service "redis"

# Kill any remaining python processes
pkill -f "python3 -m src.core.server" 2>/dev/null || true
pkill -f "mongod" 2>/dev/null || true
pkill -f "influxd" 2>/dev/null || true
pkill -f "elasticsearch" 2>/dev/null || true
pkill -f "redis-server" 2>/dev/null || true

# Clean up temporary files
rm -rf /tmp/b13_* 2>/dev/null || true

# Deactivate virtual environment if active
deactivate 2>/dev/null || true

# Clean up python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

# Reset environment variables
unset PYTHONPATH
unset FLASK_ENV
unset FLASK_DEBUG

# Print completion message
echo "Cleanup completed"
