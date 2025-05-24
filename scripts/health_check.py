import os
import subprocess
import requests
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    filename='logs/health_check.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def check_service(service_name, port):
    """Check if a service is running"""
    try:
        result = subprocess.run(['systemctl', 'is-active', service_name],
                              capture_output=True, text=True)
        status = result.stdout.strip()
        
        if status == 'active':
            logging.info(f"{service_name} is running")
            return True
        else:
            logging.warning(f"{service_name} is not running")
            return False
    except Exception as e:
        logging.error(f"Error checking {service_name}: {str(e)}")
        return False

def check_web_server():
    """Check if the web server is responding"""
    try:
        response = requests.get('http://localhost:5000/health')
        if response.status_code == 200:
            logging.info("Web server is responding")
            return True
        else:
            logging.warning(f"Web server returned status {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"Error checking web server: {str(e)}")
        return False

def main():
    print("\n=== Starting Health Check ===\n")
    
    services = {
        'mongodb': 27017,
        'influxdb': 8086,
        'elasticsearch': 9200,
        'redis': 6379
    }

    # Check all services
    for service, port in services.items():
        print(f"Checking {service}...")
        if not check_service(service, port):
            print(f"❌ {service} is not running")
        else:
            print(f"✅ {service} is running")

    # Check web server
    print("Checking web server...")
    if not check_web_server():
        print("❌ Web server is not responding")
    else:
        print("✅ Web server is responding")

if __name__ == "__main__":
    main()
