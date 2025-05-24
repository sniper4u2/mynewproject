#!/bin/bash

# Common utility functions for project scripts

# Exit on error
set -e

# Project root directory
PROJECT_ROOT=$(dirname $(readlink -f "$0"))

# Create required directories
function create_directories {
    echo "Creating required directories..."
    mkdir -p logs tools/{osint,ss7,monitoring,exploit,geolocation}
}

# Set up virtual environment
function setup_venv {
    echo "Setting up virtual environment..."
    if [ ! -d "$PROJECT_ROOT/venv" ]; then
        python3 -m venv "$PROJECT_ROOT/venv"
    fi
    
    source "$PROJECT_ROOT/venv/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
}

# Install dependencies
function install_dependencies {
    echo "Installing dependencies..."
    pip install -r "$PROJECT_ROOT/requirements.txt"
    if [ -f "$PROJECT_ROOT/requirements-dev.txt" ]; then
        pip install -r "$PROJECT_ROOT/requirements-dev.txt"
    fi
}

# Configure environment
function configure_env {
    echo "Configuring environment..."
    export PYTHONPATH=$PYTHONPATH:$PROJECT_ROOT
    
    if [ "$1" == "dev" ]; then
        export FLASK_ENV=development
        export FLASK_DEBUG=1
    fi
}

# Start service with retry
function start_service {
    local service_name=$1
    local retries=${2:-3}
    local delay=${3:-5}
    
    echo "Starting $service_name..."
    
    for ((i=1; i<=retries; i++)); do
        if systemctl is-active --quiet $service_name; then
            echo "$service_name is already running"
            return 0
        fi
        
        systemctl start $service_name
        if [ $? -eq 0 ]; then
            echo "$service_name started successfully"
            return 0
        fi
        
        echo "Attempt $i failed, retrying in $delay seconds..."
        sleep $delay
    done
    
    echo "Failed to start $service_name after $retries attempts"
    return 1
}

# Start development service
function start_dev_service {
    local service_name=$1
    local retries=${2:-3}
    local delay=${3:-5}
    
    echo "Starting $service_name in development mode..."
    
    # Skip if service command doesn't exist
    if ! command -v "$service_name" &> /dev/null; then
        echo "Skipping $service_name (not installed)"
        return 0
    fi
    
    for ((i=1; i<=retries; i++)); do
        case $service_name in
            "mongodb")
                # Use MongoDB configuration from config.yaml
                mongod --dbpath ./data/db --port 27017 --fork --logpath ./logs/mongodb.log
                ;;
            "influxdb")
                influxd
                ;;
            "elasticsearch")
                elasticsearch
                ;;
            "redis")
                redis-server
                ;;
            *)
                echo "Unknown service: $service_name"
                return 1
                ;;
        esac
        
        if [ $? -eq 0 ]; then
            echo "$service_name started successfully"
            return 0
        fi
        
        echo "Attempt $i failed, retrying in $delay seconds..."
        sleep $delay
    done
    
    echo "Failed to start $service_name after $retries attempts"
    return 1
}
