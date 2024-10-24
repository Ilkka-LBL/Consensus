from dataclasses import dataclass
from typing import Any, Dict, List
import geopandas as gpd
import pandas as pd 
from copy import deepcopy
from pathlib import Path
from Consensus import lookups
from Consensus.config_utils import load_config
from pkg_resources import resource_stream
import importlib.resources as pkg_resources
import aiohttp
import asyncio
import aiofiles



@dataclass
class Service:
    """
        Dataclass for services. 

        Attributes:
            name (str): Name of service.
            type (str): One of 'FeatureServer', 'MapServer', 'WFSServer'.
            url (str): URL.
            description (str): Description of the service.
            layers (List[Dict[str, Any]]): Data available through service. If empty, it is likely that the 'tables' attribute contains the desired data.
            tables (List[Dict[str, Any]]): Data available through service. If empty, it is likely that the 'layers' attribute contains the desired data.
            output_formats (List[str]): List of formats available for the data.
            metadata (json): Metadata as JSON.
            fields (List[str]): List of fields for the data.
            primary_key (str): Primary key for the data.
    """

    name: str = None
    type: str = None
    url: str = None
    description: str = None
    layers: List[Dict[str, Any]] = None
    tables: List[Dict[str, Any]] = None
    output_formats: List[str] = None
    metadata: Dict = None
    fields: List[str] = None
    primary_key: str = None

    def featureservers(self) -> 'Service':
        """
        Self-filtering method.

        :meta private:
        """
        if self.type == 'FeatureServer':
            self.feature_server = True
            return self

    def mapservers(self) -> 'Service':
        """
        Self-filtering method.

        :meta private:
        """
        if self.type == 'MapServer':
            self.map_server = True
            return self

    def wfsservers(self) -> 'Service':
        """
        Self-filtering method.

        :meta private:
        """
        if self.type == 'WFSServer':
            self.wfs_server = True
            return self


    async def _fetch(self, session: aiohttp.ClientSession, url: str, params: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Helper method for asynchronous GET requests using aiohttp.

        :meta private:
        """
        if params:
        # Convert boolean values to strings
            params = {k: (str(v) if isinstance(v, bool) else v) for k, v in params.items()}
        async with session.get(url, params=params, timeout=5) as response:
            return await response.json()

    async def service_details(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """
        Returns high-level details for the data as JSON.

        :meta private:
        """
        service_url = f"{self.url}?&f=json"
        return await self._fetch(session, service_url)
    
    async def service_metadata(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """
        Returns metadata as JSON.

        :meta private:
        """
        service_url = f"{self.url}/0?f=json"
        return await self._fetch(session, service_url)

    async def _service_attributes(self, session: aiohttp.ClientSession) -> None:
        """
        Fills attribute fields using the JSON information from service_details and service_metadata methods.

        Returns:
            None

        :meta private:
        """
        service_info = await self.service_details(session)
        self.description = service_info.get('description')
        self.layers = service_info.get('layers', [])
        self.tables = service_info.get('tables', [])
        self.output_formats = service_info.get('supportedQueryFormats', [])

        self.metadata = await self.service_metadata(session)
        if not self.description:
            self.description = self.metadata.get('description')
        self.fields = self.metadata.get('fields', [])
        self.primary_key = self.metadata.get('uniqueIdField')
        self.matchable_fields = [i['name'].upper() for i in self.fields if (i['name'].upper().endswith(tuple(['CD', 'NM', 'CDH', 'NMW'])) and i['name'].upper()[-4:-2].isnumeric()) or i['name'].upper() in ['PCD', 'PCDS', 'PCD2', 'PCD3', 'PCD4', 'PCD5', 'PCD6', 'PCD7', 'PCD8', 'PCD9']]
        lastedit = self.metadata.get('editingInfo', {})
        self.lasteditdate = lastedit.get('lastEditDate', '')
        self.schemalasteditdate = lastedit.get('schemaLastEditDate', '')
        self.datalasteditdate = lastedit.get('dataLastEditDate', '')

    async def lookup_format(self, session: aiohttp.ClientSession) -> Dict:
        """
        Returns a Pandas-ready dictionary of the service's metadata.

        Returns:
            Dict: A dictionary of the FeatureService's metadata.

        """
        await self._service_attributes(session)
        
        try:
            self.data = {'name': [self.name], 'fields': [[field['name'] for field in self.fields]], 
                         'url': [self.url], 'description': [self.description], 'primary_key': [self.primary_key['name']], 'matchable_fields': [self.matchable_fields], 'lasteditdate': [self.lasteditdate]}
        except TypeError:
            self.data = {'name': [self.name], 'fields': [[field['name'] for field in self.fields]], 
                         'url': [self.url], 'description': [self.description], 
                         'primary_key': [self.primary_key['name']], 'matchable_fields': [self.matchable_fields], 'lasteditdate': ['']}
            
        if self.layers:
            self.data['fields'][0].append('geometry')
            self.data['has_geometry'] = [True]
        else:
            self.data['has_geometry'] = [False]
        return self.data

    async def _record_count(self, session: aiohttp.ClientSession, url: str, params: Dict[str, str]) -> int:
        """
        Helper method for counting records.

        Returns:
            int: The count of records for the chosen FeatureService

        :meta private:
        """
        temp_params = deepcopy(params)
        temp_params['returnCountOnly'] = True
        temp_params['f'] = 'json'
        response = await self._fetch(session, url, params=temp_params)
        return response.get('count', 0)
    

class OpenGeography:
    """
    Main class for connecting to Open Geography API.
    """
    def __init__(self, max_retries:int =10, retry_delay:int =2) -> None:
        """
        Initialise class.

        Returns:
            None

        :meta private:
        """
        print("Connecting to Open Geography Portal")
        self.base_url = "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services?f=json"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.server_types = {'feature': 'FeatureServer', 'map': 'MapServer', 'wfs': 'WFSServer'}
        self.services = []
        self.service_table = None

    async def initialise(self) -> None:
        """ 
        Run this method to initialise the class session.
        
        Returns:
            None
        """
        await self._validate_response()

    async def _fetch_response(self, session: aiohttp.ClientSession) -> dict:
        """
        Helper method to fetch the response from the Open Geography API.
        """
        async with session.get(self.base_url) as response:
            return await response.json() if response.status == 200 else {}

    async def _validate_response(self) -> None:
        """
        Validate access to the base URL asynchronously using aiohttp.
        """
        print(f"Requesting services from URL: {self.base_url}")
        async with aiohttp.ClientSession() as session:
            for attempt in range(self.max_retries):
                try:
                    response = await self._fetch_response(session)
                    self.services = response.get('services', [])
                    if self.services:
                        await self._load_all_services(session)
                        return
                    print("No services found, retrying...")
                except Exception as e:
                    print(f"Error during request: {e}")
                print(f"Retry attempt {attempt + 1}/{self.max_retries}")
                await asyncio.sleep(self.retry_delay)
        print(f"Failed to retrieve services after {self.max_retries} attempts.")

    async def _load_all_services(self, session: aiohttp.ClientSession) -> None:
        """
        Load services into a dictionary asynchronously.
        """
        self.service_table = {service['name']: Service(service['name'], service['type'], service['url']) for service in self.services if service['type'] == self.server_types['feature']}
        print("Services loaded. Ready to go.")

    def print_all_services(self) -> None:
        """
        Print name, type, and URL of all services available through Open Geography Portal.
        """
        for service_name, service_obj in self.service_table.items():
            print(f"Service: {service_name}\nURL: {service_obj.url}\nService type: {service_obj.type}")

    def print_services_by_server_type(self, server_type: str = 'feature') -> None:
        """
        Print services given a server type.
        """
        try:
            server_type_key = self.server_types[server_type]
            for service_obj in self.service_table.values():
                if service_obj.type == server_type_key:
                    print(f"Service: {service_obj.name}\nURL: {service_obj.url}\nService type: {service_obj.type}")
        except KeyError:
            print(f"Invalid server type: {server_type}. Valid options are 'feature', 'map', or 'wfs'.")


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


    
class AsyncFeatureServer():
    def __init__(self) -> None:
        pass

    async def setup(self, service_name: str = None, service_table: dict = {}, max_retries: int = 10, retry_delay: int = 20, chunk_size: int = 50):
        try:
            self.feature_service = service_table.get(service_name).featureservers()
            
            self.max_retries = max_retries
            self.retry_delay = retry_delay
            self.chunk_size = chunk_size
            
        except AttributeError as e:
            print(f"{e} - the selected table does not appear to have a feature server. Check table name exists in list of services or your spelling.")
            
        async with aiohttp.ClientSession() as session:
            await self.feature_service.lookup_format(session)

    async def looper(self, session: aiohttp.ClientSession, link_url: str, params: dict) -> dict:
        """ Keep trying to connect to Feature Service until max_retries or response """
        retries = 0
        while retries < self.max_retries:
            try:
                async with session.get(link_url, params=params, timeout=self.retry_delay) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"Error: {response.status} - {await response.text()}")
                        return None
            except asyncio.TimeoutError:
                retries += 1
                print("No services found, retrying...")
                print(f"Retry attempt {retries}/{self.max_retries}")
                await asyncio.sleep(2)

        print("Max retries reached. Request failed. Smaller chunk size may help.")
        return None

    async def chunker(self, session: aiohttp.ClientSession, service_url: str, params: dict) -> dict:
        """ Download data in chunks asynchronously """
        print(params['where'])
        if self.feature_service.tables:
            links_to_visit = self.feature_service.tables
        elif self.feature_service.layers:
            links_to_visit = self.feature_service.layers

        params['resultOffset'] = 0
        params['resultRecordCount'] = self.chunk_size

        link_url = f"{service_url}/{str(links_to_visit[0]['id'])}/query"
        print(f"Visiting link {link_url}")

        # Get the first response
        responses = await self.looper(session, link_url, params)

        # Get the total number of records
        count = await self.feature_service._record_count(session, link_url, params=params)
        print(f"Total records to download: {count}")

        counter = len(responses['features'])
        print(f"Downloaded {counter} out of {count} ({100 * (counter / count):.2f}%) items")

        # Continue fetching data until all records are downloaded
        while counter < int(count):
            params['resultOffset'] += self.chunk_size
            additional_response = await self.looper(session, link_url, params)
            if not additional_response:
                break

            responses['features'].extend(additional_response['features'])
            counter += len(additional_response['features'])
            print(f"Downloaded {counter} out of {count} ({100 * (counter / count):.2f}%) items")

        return responses

    async def download(self, fileformat: str = 'geojson', return_geometry: bool = False, where_clause: str = '1=1', output_fields: str = '*', params: dict = None, n_sample_rows: int = -1) -> dict:
        """
        Download data from Open Geography Portal asynchronously.
        """
        primary_key = self.feature_service.primary_key['name']

        if n_sample_rows > 0:
            where_clause = f"{primary_key}<={n_sample_rows}"
        if hasattr(self.feature_service, 'feature_server'):
            service_url = self.feature_service.url

            if not params:
                params = {
                    'where': where_clause,
                    'objectIds': '',
                    'time': '',
                    'resultType': 'standard',
                    'outFields': output_fields,
                    'returnIdsOnly': False,
                    'returnUniqueIdsOnly': False,
                    'returnCountOnly': False,
                    'returnGeometry': return_geometry,
                    'returnDistinctValues': False,
                    'cacheHint': False,
                    'orderByFields': '',
                    'groupByFieldsForStatistics': '',
                    'outStatistics': '',
                    'having': '',
                    'resultOffset': 0,
                    'resultRecordCount': self.chunk_size,
                    'sqlFormat': 'none',
                    'f': fileformat
                }
            # Convert any boolean values to 'true' or 'false' in the params dictionary
            params = {k: str(v).lower() if isinstance(v, bool) else v for k, v in params.items()}
            async with aiohttp.ClientSession() as session:
                try:
                    responses = await self.chunker(session, service_url, params)
                except ZeroDivisionError:
                    print("No records found in this Service. Try another Feature Service.")

            if 'geometry' in responses['features'][0].keys():
                return gpd.GeoDataFrame.from_features(responses)
            else:
                df = pd.DataFrame(responses['features'])
                return df.apply(pd.Series)

        else:
            raise AttributeError("Feature service not found")