"""
Open Geography Portal
---------------------

This module provides a class `OpenGeography()` that connects to the Open Geography Portal API
and a subclass `OpenGeographyLookup()` that builds and updates a JSON lookup table for the portal's FeatureServers.

`OpenGeographyLookup()` is necessary if you want to make use of the `SmartLinker()` class from the GeocodeMerger module.

Usage:
------
This module works in the same way as the `EsriConnector` class, but it is specifically designed for the Open Geography Portal API. It provides a `build_lookup()` method that creates a lookup table for the portal's FeatureServers and saves it to a JSON file.

.. code-block:: python

    from Consensus.OGP import OpenGeography
    ogp = OpenGeography()
    await ogp.initialise()
    await ogp.build_lookup()

Like with TFL module, you can combine OpenGeography with the FeatureServer() class to download data from the portal's FeatureServers.

.. code-block:: python

    from Consensus.OGP import OpenGeography
    from Consensus.EsriConnector import FeatureServer
    from Consensus.utils import where_clause_maker

    ogp = OpenGeography(max_retries=30, retry_delay=2)
    await ogp.initialise()

    fs_service_table = ogp.service_table
    fs = FeatureServer()

    service_name = 'Wards_December_2022_Boundaries_GB_BFC'
    column_name = 'WD22NM'
    geographic_areas = ['Brockley', 'Sydenham']
    where_clause = where_clause_maker(string_list=geographic_areas, column_name=column_name, service_name=service_name)  # a helper function that creates the SQL where clause for Esri Servers

    await fs.setup(service_name=service_name, service_table=fs_service_table, max_retries=30, retry_delay=2, chunk_size=50)
    output = await fs.download(where_clause=where_clause, return_geometry=True)
    print(output)

However, it is perhaps best to rely on the `SmartLinker()` class from the GeocodeMerger module for more complex operations.
"""

from Consensus.EsriConnector import EsriConnector
from pathlib import Path
from typing import List
import pandas as pd
import aiofiles


class OpenGeography(EsriConnector):
    """
    Uses EsriConnector class to connect to Open Geography Portal API.
    """
    def __init__(self, max_retries: int = 10, retry_delay: int = 2) -> None:
        """
        Initialise class.

        Args:
            max_retries (int): Maximum number of retries for HTTP requests. Defaults to 10.
            retry_delay (int): Delay in seconds between retries. Defaults to 2.

        Returns:
            None
        """
        super().__init__(max_retries, retry_delay)
        self.base_url = "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services?f=json"
        print("Connecting to Open Geography Portal")

    async def build_lookup(self, parent_path: Path = Path(__file__).resolve().parent, included_services: List[str] = [], replace_old: bool = True) -> pd.DataFrame:
        """
        Build a lookup table from scratch and save it to a JSON file.

        Args:
            parent_path (Path): Parent path to save the lookup file.
            included_services (List[str]): List of services to include in the lookup. Defaults to [], which is interpreted as as 'all'.
            replace_old (bool): Whether to replace the old lookup file. Defaults to True.

        Returns:
            pd.DataFrame: The lookup table as a pandas DataFrame.
        """
        lookup_df = await self.metadata_as_pandas(included_services=included_services)
        if replace_old:
            async with aiofiles.open(parent_path / 'lookups/lookup.json', 'w') as f:
                await f.write(lookup_df.to_json())
        return lookup_df
