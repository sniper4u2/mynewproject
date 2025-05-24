import yaml
import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

class ConfigLoader:
    def __init__(self, config_path: str = 'config/consolidated_config.yaml'):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load and merge configuration from YAML file and environment variables"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Merge with environment variables
            for section in config:
                for key in config[section]:
                    env_key = f"{section.upper()}_{key.upper()}"
                    env_value = os.getenv(env_key)
                    if env_value is not None:
                        config[section][key] = self._parse_env_value(env_value)
            
            return config
        except Exception as e:
            raise Exception(f"Failed to load configuration: {str(e)}")

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type"""
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

    def get(self, section: str, key: str) -> Any:
        """Get configuration value"""
        return self.config.get(section, {}).get(key)

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire section configuration"""
        return self.config.get(section, {})

# Initialize global config loader
config_loader = ConfigLoader()
