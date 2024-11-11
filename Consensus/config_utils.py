"""
Load the config.json
--------------------

The main purpose of this module is to load the configuration from a file within the package.
This is a simple implementation that assumes the configuration file is named 'config.json' and
is located in a directory named 'config' within the package. The configuration is loaded
as a dictionary and returned.

This module uses the ``importlib.resources`` module to access the configuration file within
the package's resources. If the file is not found, an empty dictionary is returned.
Note that this implementation does not handle any potential exceptions that may occur during
the loading or parsing of the configuration file.
"""

import json
import importlib.resources as pkg_resources
from typing import Dict, Any


def load_config() -> Dict[str, Any]:
    """
    Load configuration from a file within the package.

    Returns:
        Dict[str, Any]: A dictionary containing the configuration settings.

    """
    try:
        with pkg_resources.files('Consensus').joinpath('config/config.json').open('r') as f:
            return json.load(f)

    except FileNotFoundError:
        return {}
