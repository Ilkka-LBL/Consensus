import json
import os
from typing import Dict, Any
import importlib.resources as pkg_resources
from Consensus.config_utils import load_config  # Import the load_config function


class ConfigManager:
    def __init__(self, config_file: str = None):
        # Determine the path for the config file within the package
        if config_file is None:
            self.config_file = os.path.join(
                pkg_resources.files('Consensus').joinpath('config/config.json')
            )
        else:
            self.config_file = config_file

        self.default_config = {
            "nomis_api_key": "",
            "lg_inform_key": "",
            "lg_inform_secret": "",
            "proxies": {
                "http": "",
                "https": ""
            }
        }

        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

        # Create the config file if it doesn't exist
        if not os.path.exists(self.config_file):
            self.reset_config()

    def save_config(self, config: Dict[str, Any]) -> None:
        """Save the current configuration to the config file."""
        config_file = pkg_resources.files('Consensus').joinpath('config/config.json')
        with config_file.open('w') as f:
            json.dump(config, f, indent=4)

    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with multiple keys and values. Supports nested keys using dot notation."""
        config = load_config()  # No arguments needed
        for key, value in updates.items():
            keys = key.split('.')
            d = config
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            d[keys[-1]] = value
        self.save_config(config)


    def reset_config(self) -> None:
        """Reset configuration to the default values."""
        self.default_config = {
            "nomis_api_key": "",
            "lg_inform_key": "",
            "lg_inform_secret": "",
            "proxies": {
                "http": "",
                "https": ""
            }
        }
        self.save_config(self.default_config)
