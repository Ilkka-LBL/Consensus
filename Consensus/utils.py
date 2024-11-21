from typing import List, Dict, Any
import pandas as pd
from pathlib import Path
from Consensus import lookups
import sys
import json
import importlib.resources as pkg_resources
from Consensus.EsriServers import OpenGeography, TFL


def where_clause_maker(values: List[str], column: str) -> str:
    """
    Create a SQL where clause for Esri ArcGIS servers based on a list of values in a column and that column's name.
    You must also include the layer's name.

    Args:
        values (List): A list of values in ``column`` to include in the where clause.
        column (str): The column name to use in the where clause.

    Returns:
        str: A SQL where clause.
    """
    assert column, "No column name provided"
    assert values, "No values provided"
    where_clause = f"{column} IN {str(tuple(values))}" if len(values) > 1 else f"{column} IN ('{str(values[0])}')"
    print(f"Selecting items based on SQL: {where_clause}")
    return where_clause


def read_lookup(lookup_folder: Path = None, server_name: str = None) -> pd.DataFrame:
    """
    Read lookup table.

    Args:
        lookup_folder (Path): ``pathlib.Path()`` to the folder where ``lookup.json`` file is currently saved.
        server_name (str): The name of the server. For ``EsriConnector()`` sub-classes, this is the same as ``self._name``.

    Returns:
        pd.DataFrame: Lookup table as a Pandas dataframe.
    """
    try:
        if lookup_folder:
            json_path = Path(lookup_folder) / f'lookups/{server_name}_lookup.json'
            return pd.read_json(json_path)
        else:
            with pkg_resources.open_text(lookups, f'{server_name}_lookup.json') as f:
                lookup_data = json.load(f)
            return pd.DataFrame(lookup_data)
    except FileNotFoundError:
        print('No lookup file found, please build one using the appropriate EsriConnector sub-class')
        sys.exit(1)


def _server_selector() -> Dict[str, Any]:
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
    d = _server_selector()  # get dictionary of servers
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
    d = _server_selector()  # get dictionary of servers
    if isinstance(d[key], type):
        d[key] = d[key](**kwargs)
    return d[key]
