from dataclasses import dataclass
from typing import Any, Dict, List
from copy import deepcopy
import aiohttp
import asyncio
import geopandas as gpd
import pandas as pd


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
            self.data = {'name': [self.name],
                         'fields': [[field['name'] for field in self.fields]],
                         'url': [self.url],
                         'description': [self.description],
                         'primary_key': [self.primary_key['name']],
                         'matchable_fields': [self.matchable_fields],
                         'lasteditdate': [self.lasteditdate]}
        except TypeError:
            self.data = {'name': [self.name],
                         'fields': [[field['name'] for field in self.fields]],
                         'url': [self.url],
                         'description': [self.description],
                         'primary_key': [self.primary_key['name']],
                         'matchable_fields': [self.matchable_fields],
                         'lasteditdate': ['']}

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


class EsriConnector:
    """
    Main class for connecting to Esri servers.
    """
    def __init__(self, max_retries: int = 10, retry_delay: int = 2, base_url: str = "") -> None:
        """
        Initialise class.

        Returns:
            None

        :meta private:
        """
        self.base_url = ""
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.server_types = {'feature': 'FeatureServer',
                             'map': 'MapServer',
                             'wfs': 'WFSServer'}
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
        Helper method to fetch the response from the Esri server.
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
        Print name, type, and URL of all services available through Esri server.
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


class AsyncFeatureServer():
    """
        Download data from an Esri Feature Server asynchronously.

        Attributes:
            feature_service (Service): The FeatureServer object.
            max_retries (int): The maximum number of retries for a request.
            retry_delay (int): The delay in seconds between retries.
            chunk_size (int): The number of records to download in each chunk.

        Usage:
            .. code-block:: python

                og = OpenGeography(max_retries=30, retry_delay=2)
                await og.initialise()

                fs_service_table = og.service_table
                fs = AsyncFeatureServer()

                await fs.setup(service_name='Wards_December_2023_Boundaries_UK_BSC', service_table=fs_service_table, max_retries=30, retry_delay=2, chunk_size=50)
                column_name = 'WD23NM'
                geographic_areas = ['Brockley']
                where_clause = f"{column_name} IN ('{str(geographic_areas[0])}')"
                output = await fs.download(where_clause=where_clause, return_geometry=True)
    """
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
        Download data from Esri server asynchronously.
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
