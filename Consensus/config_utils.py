# config_utils.py

import json
import importlib.resources as pkg_resources
from typing import Dict, Any


def load_config() -> Dict[str, Any]:
    """Load configuration from a file within the package."""
    try:
        with pkg_resources.files('Consensus').joinpath('config/config.json').open('r') as f:
            return json.load(f)
    
    except FileNotFoundError:
        return {}
