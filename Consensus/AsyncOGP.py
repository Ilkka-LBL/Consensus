from Consensus.EsriConnector import EsriConnector
from pathlib import Path
from typing import List
import pandas as pd
import aiohttp
import asyncio
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


class OpenGeographyLookup(OpenGeography):
    """
    Class to build and update a JSON lookup table for the Open Geography Portal's FeatureServers.
    """
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    async def _fetch_services(self) -> None:
        """
        Fetch services from the base URL and load them into the service table asynchronously.
        """
        async with aiohttp.ClientSession() as session:
            for _ in range(self.max_retries):
                try:
                    async with session.get(self.base_url) as response:
                        if response.status == 200:
                            print("Connection successful")
                            data = await response.json()
                            self.services = data.get('services', [])
                            if self.services:
                                print("Loading services")
                                await self._load_all_services(session)
                                return
                        else:
                            print(f"Failed with status code {response.status}. Retrying...")
                except Exception as e:
                    print(f"Exception occurred: {e}. Retrying...")
                await asyncio.sleep(self.retry_delay)
            print(f"Failed to retrieve services after {self.max_retries} attempts.")

    async def metadata_as_pandas(self, service_type: str = 'feature', included_services: List[str] = []) -> pd.DataFrame:
        """
        Asynchronously create a Pandas DataFrame of selected tables based on the service type.
        """
        assert service_type in ['feature', 'map', 'wfs'], "Service type must be one of: 'feature', 'map', 'wfs'"

        service_table_to_loop = {k: self.service_table[k] for k in included_services if k in self.service_table} if included_services else self.service_table
        relevant_services = {name: obj for name, obj in service_table_to_loop.items() if obj.type.lower() == self.server_types[service_type].lower()}

        lookup_table = []
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_service_metadata(service_obj, lookup_table, name, session) for name, service_obj in relevant_services.items()]
            await asyncio.gather(*tasks)

        if not lookup_table:
            print("No valid data found.")
            return pd.DataFrame()

        return pd.concat([pd.DataFrame(item) for item in lookup_table]).reset_index(drop=True)

    async def _fetch_service_metadata(self, service_obj, lookup_table, service_name, session: aiohttp.ClientSession):
        """
        Fetch service metadata for a specific service.
        """
        try:
            print(f"Fetching metadata for service {service_name}")
            lookup_table.append(await service_obj.lookup_format(session))
        except Exception as e:
            print(f"Error fetching metadata for service {service_name}: {e}")

    async def build_lookup(self, parent_path: Path = Path(__file__).resolve().parent, included_services: List[str] = [], replace_old: bool = True) -> pd.DataFrame:
        """
        Build a lookup table from scratch and save it to a JSON file.
        """
        lookup_df = await self.metadata_as_pandas(included_services=included_services)
        if replace_old:
            async with aiofiles.open(parent_path / 'lookups/lookup.json', 'w') as f:
                await f.write(lookup_df.to_json())
        return lookup_df
