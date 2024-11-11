"""
Usage:
------
To use the ConfigManager class, import it from the Consensus package, create an instance, and call its methods to load, save, update, and reset the configuration.

Example:

.. code-block:: python

    # Import the ConfigManager class
    from Consensus.ConfigManager import ConfigManager

    # Create an instance of ConfigManager
    config_manager = ConfigManager()

    # Access the current configuration file path
    config_file_path = config_manager.config_file

    # Access the default configuration
    default_config = config_manager.DEFAULT_CONFIG

    # Define a new configuration
    new_config = {
        'nomis_api_key': 'your_api_key',
        'lg_inform_key': 'your_lg_inform_key',
        'lg_inform_secret': 'your_lg_inform_secret',
        'proxies': {
            'http': 'your_http_proxy',
            'https': 'your_https_proxy'
        }
    }

    # Save the new configuration
    config_manager.save_config(new_config)

    # Update specific values in the configuration
    updates = {
        'nomis_api_key': 'new_api_key',
        'proxies.http': 'new_http_proxy'
    }
    config_manager.update_config(updates)

    # Reset the configuration to default values
    config_manager.reset_config()

Note that new configuration files are always saved in ``Consensus/config/config.json``.
"""

import json
import os
from typing import Dict, Any
import importlib.resources as pkg_resources
from Consensus.config_utils import load_config  # Import the load_config function


class ConfigManager:
    """
    A class to manage loading, saving, updating, and resetting a JSON configuration file.

    This class provides an interface to manage a configuration file stored in JSON format,
    allowing users to define their configuration settings and update them as needed.

    Attributes:
        config_file (str): The path to the configuration file.
        DEFAULT_CONFIG (Dict[str, Any]): The default configuration values.

    Methods:
        __init__(config_file: str = None): Initializes the ConfigManager with a specified or default config file.
        save_config(config: Dict[str, Any]): Saves a configuration dictionary to the config file.
        update_config(updates: Dict[str, Any]): Updates configuration with specified key-value pairs, supporting nested keys.
        reset_config(): Resets the configuration file to default values.
    """

    DEFAULT_CONFIG = {
        "nomis_api_key": "",
        "lg_inform_key": "",
        "lg_inform_secret": "",
        "proxies": {
            "http": "",
            "https": ""
        }
    }

    def __init__(self, config_file: str = None) -> None:
        """
        Initializes the ConfigManager with a specified or default config file.

        Args:
            config_file (str): Path to the configuration file. If not provided,
                defaults to 'config/config.json' within the package.
        """
        self.config_file = config_file or pkg_resources.files('Consensus').joinpath('config/config.json')
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

        # Initialize the config file with default values if it does not exist
        if not os.path.exists(self.config_file):
            self.reset_config()

    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Saves a configuration dictionary to the config file.

        Args:
            config (Dict[str, Any]): The configuration dictionary to save.

        Returns:
            None
        """
        with self.config_file.open('w') as f:
            json.dump(config, f, indent=4)

    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        Updates the configuration with specified key-value pairs, supporting nested keys
        using dot notation.

        Args:
            updates (Dict[str, Any]): A dictionary of key-value pairs to update in the config.
                Nested keys can be specified in dot notation (e.g., 'proxies.http').

        Returns:
            None
        """
        config = load_config()  # Load the existing config
        for key, value in updates.items():
            keys = key.split('.')
            d = config
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            d[keys[-1]] = value
        self.save_config(config)

    def reset_config(self) -> None:
        """
        Resets the configuration file to default values.

        Returns:
            None
        """
        self.save_config(self.DEFAULT_CONFIG)
