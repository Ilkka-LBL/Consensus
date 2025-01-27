"""
Utility functions
-----------------

This module contains helper functions that can be used alone or they are used by more than one of the classes.

``where_clause_maker()`` function is used to create a SQL where clause for downloading data from Esri servers.
``read_lookup()`` is used by the ``SmartLinker()`` to build a graph and ``read_service_table()`` is used by ``FeatureServer()`` to select the right Esri service from a pickle file. Both the lookup and the pickle file are created during the lookup building.

"""

from typing import List, Dict, Any
import pandas as pd
from pathlib import Path
from Consensus import lookups
import sys
import json
import importlib.resources as pkg_resources
import pickle


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


def read_service_table(parent_path: Path = Path(__file__).resolve().parent, esri_server: str = None) -> Dict[str, Any]:
    """
    Read service table pickle file.

    Args:
        parent_path (Path): ``pathlib.Path()`` to the folder where the Esri server pickle file is currently saved.
        esri_server (str): The name of the Esri server. For instance, for Open Geography Portal, this would be Open_Geography_Portal. This can be output from any Esri server using the ``_name`` method.

    Returns:
        Dict[str, Layer]
    """
    try:
        with open(parent_path / f'PickleJar/{esri_server}.pickle', "rb") as f:
            unpickler = pickle.Unpickler(f)
            service_table = unpickler.load()
        return service_table
    except Exception as e:
        print(e)
        print("Service table not found. Please build one using the asynchronous build_lookup() method.")
        return {}
