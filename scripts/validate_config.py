import yaml
import os
from pathlib import Path

def validate_config():
    """Validate configuration files"""
    config_files = [
        'config.yaml',
        os.path.join('config', 'database.yaml'),
        os.path.join('config', 'monitoring.yaml'),
        os.path.join('config', 'security.yaml')
    ]

    print("\n=== Configuration Validation ===\n")
    
    for config_file in config_files:
        if not os.path.exists(config_file):
            print(f"❌ Error: {config_file} not found")
            continue

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                print(f"✅ {config_file}: Valid YAML format")
        except yaml.YAMLError as e:
            print(f"❌ Error in {config_file}: {str(e)}")

    print("\n=== Environment Variables Validation ===\n")
    required_env_vars = [
        'MONGODB_URI',
        'INFLUXDB_URI',
        'ELASTICSEARCH_URI',
        'REDIS_URI',
        'SECRET_KEY'
    ]

    for env_var in required_env_vars:
        if env_var not in os.environ:
            print(f"❌ Missing environment variable: {env_var}")
        else:
            print(f"✅ {env_var} is set")

if __name__ == "__main__":
    validate_config()
