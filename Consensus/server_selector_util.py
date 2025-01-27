"""
Purpose of server_selector_util
-------------------------------

This utility module has one purpose; to serve EsriServers.

The available servers are listed in the ``server_selector()`` function and this dictionary should be manually expanded when new EsriServers are added as built-in options.
The ``get_server()`` function is then used by the ``SmartLinker()`` class to select the server to create a graph on.

"""

from Consensus.EsriServers import OpenGeography, TFL
from typing import Dict, Any


def server_selector() -> Dict[str, Any]:
    """
    Select the server based on the provided name.

    Returns:
        Dict[str, Any]: Dictionary of servers.
    """
    servers = {'OGP': OpenGeography, 'TFL': TFL}
    return servers


def get_server_name(server: str = None) -> str:
    """
    Get the name of the server.

    Args:
        server (str): Name of the server.

    Returns:
        str: Name of the server.
    """
    d = server_selector()  # get dictionary of servers
    return d[server]._name


def get_server(key: str, **kwargs: Dict[str, Any]) -> Any:
    """
    Helper function to get the server based on the provided name.

    Args:
        key (str): Name of the server.
        **kwargs: Keyword arguments to pass to the server class.

    Returns:
        Any: Instance of the server class.
    """
    d = server_selector()  # get dictionary of servers
    if isinstance(d[key], type):
        d[key] = d[key](**kwargs)
    return d[key]
