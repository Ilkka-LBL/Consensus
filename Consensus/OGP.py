"""
Open Geography Portal
---------------------

This module provides a class `OpenGeography()` that connects to the Open Geography Portal API
and a subclass `OpenGeographyLookup()` that builds and updates a JSON lookup table for the portal's FeatureServers.

`OpenGeographyLookup()` is necessary if you want to make use of the `SmartLinker()` class from the GeocodeMerger module.

Classes:
    OpenGeography: A class to connect to the Open Geography Portal API.
    OpenGeographyLookup: A class to build and update a JSON lookup table for the Open Geography Portal's FeatureServers.



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

        Returns:
            None

        :meta private:
        """
        super().__init__(max_retries, retry_delay)
        self.base_url = "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services?f=json"
        print("Connecting to Open Geography Portal")

    async def build_lookup(self, parent_path: Path = Path(__file__).resolve().parent, included_services: List[str] = [], replace_old: bool = True) -> pd.DataFrame:
        """
        Build a lookup table from scratch and save it to a JSON file.
        """
        lookup_df = await self.metadata_as_pandas(included_services=included_services)
        if replace_old:
            async with aiofiles.open(parent_path / 'lookups/lookup.json', 'w') as f:
                await f.write(lookup_df.to_json())
        return lookup_df
