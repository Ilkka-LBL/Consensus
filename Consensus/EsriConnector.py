"""
Extending `EsriConnector()` class
---------------------------------

This module provides a class for interacting with the Esri REST API. It creates a dictionary of Service objects given the URL of the server and add methods to extract the metadata for any of them.
You can apply the `EsriConnector()` class to a new server by calling `my_new_connection=EsriConnector(base_url=your_new_server)` or by creating a separate class if you so wish:

.. code-block:: python

    from Consensus.EsriConnector import EsriConnector

    class NewClass(EsriConnector):
        def __init__(self, max_retries: int = 10, retry_delay: int = 2) -> None:
            super().__init__(max_retries, retry_delay)
            self.base_url = your_new_server
            print(f"Connecting to {your_new_server}")

This is the basic building block that the Consensus package uses to interact with Esri REST APIs such as Open Geography Portal and TfL Open Data Hub. It is designed to be extended to provide additional functionality, such as custom methods for specific use cases.


`FeatureServer()` class example
-------------------------------

`FeatureServer()` class on the other hand is used to download data from the Esri REST API. For example, to download the ward 2023 boundary data for Brockley in Lewisham from Open Geography Portal:

.. code-block:: python

    from Consensus.EsriConnector import FeatureServer
    from Consensus.OGP import OpenGeography
    from Consensus.utils import where_clause_maker

    og = OpenGeography(max_retries=30, retry_delay=2)
    await og.initialise()

    fs_service_table = og.service_table
    fs = FeatureServer()

    column_name = 'WD23NM'
    geographic_areas = ['Brockley']
    service_name = 'Wards_December_2023_Boundaries_UK_BSC'
    where_clause = where_clause_maker(string_list=geographic_areas, column_name=column_name, service_name=service_name)  # a helper function that creates the SQL where clause for Esri Servers

    await fs.setup(service_name=service_name, service_table=fs_service_table, max_retries=30, retry_delay=2, chunk_size=50)
    output = await fs.download(where_clause=where_clause, return_geometry=True)
    print(output)

"""


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

        Returns:
            Service: Self if type is 'FeatureServer' else None.
        """
        if self.type == 'FeatureServer':
            self.feature_server = True
            return self

    def mapservers(self) -> 'Service':
        """
        Self-filtering method. Currently unused.

        Returns:
            Service: Self if type is 'MapServer' else None.
        """
        if self.type == 'MapServer':
            self.map_server = True
            return self

    def wfsservers(self) -> 'Service':
        """
        Self-filtering method. Currently unused.

        Returns:
            Service: Self if type is 'WFSServer' else None.
        """
        if self.type == 'WFSServer':
            self.wfs_server = True
            return self

    async def _fetch(self, session: aiohttp.ClientSession, url: str, params: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Helper method for asynchronous GET requests using aiohttp.

        Args:
            session (aiohttp.ClientSession): The aiohttp session object.
            url (str): The URL to fetch.
            params (Dict[str, str], optional): Query parameters. Defaults to None.

        Returns:
            Dict[str, Any]: The response as a JSON object.
        """
        if params:
            # Convert boolean values to strings for params created in _record_count() method.
            params = {k: (str(v) if isinstance(v, bool) else v) for k, v in params.items()}
        async with session.get(url, params=params, timeout=5) as response:
            return await response.json()

    async def service_details(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """
        Returns high-level details for the data as JSON.

        Args:
            session (aiohttp.ClientSession): The aiohttp session object.

        Returns:
            Dict[str, Any]: The service details as a JSON object.
        """
        service_url = f"{self.url}?&f=json"
        return await self._fetch(session, service_url)

    def download_urls(self) -> List[str]:
        """
        Returns the download URL for the service.

        Args:
            session (aiohttp.ClientSession): The aiohttp session object.

        Returns:
            List[str]: List of download URLs to visit.
        """
        if self.layers:
            download_urls = [f"{self.url}/{layer['id']}/query" for layer in self.layers]
        elif self.tables:
            download_urls = [f"{self.url}/{table['id']}/query" for table in self.tables]
        else:
            download_urls = [f"{self.url}/0/query"]
        # print(download_urls)
        return download_urls

    async def service_metadata(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """
        Returns metadata as JSON.

        Args:
            session (aiohttp.ClientSession): The aiohttp session object.

        Returns:
            Dict[str, Any]: The metadata as a JSON object.
        """
        
        """if not self.layers and not self.tables:
            service_url = f"{self.url}/0?f=json"
        elif self.layers and not self.tables:
            service_url = f"{self.url}/{self.layers[0]['id']}?f=json"
        elif self.tables and not self.layers:
            service_url = f"{self.url}/{self.tables[0]['id']}?f=json"
        else:
            service_url = f"{self.url}/0?f=json"
        print(service_url)"""
        if self.layers:
            metadata_urls = [f"{self.url}/{layer['id']}?f=json" for layer in self.layers]
        elif self.tables:
            metadata_urls = [f"{self.url}/{table['id']}?f=json" for table in self.tables]
        else:
            metadata_urls = [f"{self.url}/0/?f=json"]
        for i in metadata_urls:
            try:
                return await self._fetch(session, i)
            except Exception as e:
                print(e)
                continue

    async def _service_attributes(self, session: aiohttp.ClientSession) -> None:
        """
        Fills attribute fields using the JSON information from service_details and service_metadata methods.

        Args:
            session (aiohttp.ClientSession): The aiohttp session object.

        Returns:
            None
        """
        service_info = await self.service_details(session)
        self.description = service_info.get('description')
        self.layers = service_info.get('layers', [])
        self.tables = service_info.get('tables', [])
        self.output_formats = service_info.get('supportedQueryFormats', [])

        self.download_urls = self.download_urls()
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

    async def lookup_format(self, session: aiohttp.ClientSession) -> Dict[str, List]:
        """
        Returns a Pandas-ready dictionary of the service's metadata.

        Args:
            session (aiohttp.ClientSession): The aiohttp session object.

        Returns:
            Dict[str, List]: A dictionary of the FeatureService's metadata.
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

        Args:
            session (aiohttp.ClientSession): The aiohttp session object.
            url (str): The URL to fetch.
            params (Dict[str, str]): Query parameters.

        Returns:
            int: The count of records for the chosen FeatureService
        """
        temp_params = deepcopy(params)
        temp_params['returnCountOnly'] = True
        temp_params['f'] = 'json'
        response = await self._fetch(session, url, params=temp_params)
        return response.get('count', 0)


class EsriConnector:
    """
    Main class for connecting to Esri servers.

    Attributes:
        base_url (str): The base URL of the Esri server. Built-in modules that use `EsriConnector()` class set their own base_url.
        max_retries (int): The maximum number of retries for HTTP requests.
        retry_delay (int): The delay in seconds between retries.
        server_types (dict): A dictionary of server types and their corresponding suffixes.
        services (list): A list of Service objects.
        service_table (DataFrame): A Pandas DataFrame containing the service metadata.
    """
    def __init__(self, max_retries: int = 10, retry_delay: int = 2, base_url: str = "") -> None:
        """
        Initialise class.

        Args:
            max_retries (int): The maximum number of retries for HTTP requests. Defaults to 10.
            retry_delay (int): The delay in seconds between retries. Defaults to 2.
            base_url (str): The base URL of the Esri server. Defaults to "". Built-in modules that use `EsriConnector()` class set their own base_url.

        Returns:
            None
        """
        self.base_url = base_url
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

    async def _fetch_response(self, session: aiohttp.ClientSession) -> Dict:
        """
        Helper method to fetch the response from the Esri server.

        Args:
            session (aiohttp.ClientSession): The aiohttp.ClientSession object.

        Returns:
            Dict: The JSON response from the Esri server.
        """
        async with session.get(self.base_url) as response:
            return await response.json() if response.status == 200 else {}

    async def _fetch_service_metadata(self, service_obj: Service, lookup_table: List[pd.DataFrame], service_name: str, session: aiohttp.ClientSession) -> None:
        """
        Fetch service metadata for a specific service.

        Args:
            service_obj (Service): The Service object to fetch metadata for.
            lookup_table (List[pd.DataFrame]): The list to append the metadata to.
            service_name (str): The name of the service.
            session (aiohttp.ClientSession): The aiohttp.ClientSession object.

        Returns:
            None
        """
        try:
            print(f"Fetching metadata for service {service_name}")
            lookup_table.append(await service_obj.lookup_format(session))
        except Exception as e:
            print(f"Error fetching metadata for service {service_name}: {e}")

    async def _validate_response(self) -> None:
        """
        Validate access to the base URL asynchronously using aiohttp. When a response is received, call `_load_all_services()` to load services into a dictionary.

        Returns:
            None
        """
        print(f"Requesting services from URL: {self.base_url}")
        async with aiohttp.ClientSession() as session:
            for attempt in range(self.max_retries):
                try:
                    response = await self._fetch_response(session)
                    self.services = response.get('services', [])
                    if self.services:
                        await self._load_all_services()
                        return
                    print("No services found, retrying...")
                except Exception as e:
                    print(f"Error during request: {e}")
                print(f"Retry attempt {attempt + 1}/{self.max_retries}")
                await asyncio.sleep(self.retry_delay)
        print(f"Failed to retrieve services after {self.max_retries} attempts.")

    async def _load_all_services(self) -> None:
        """
        Load services into a dictionary.

        Returns:
            None
        """
        self.service_table = {service['name']: Service(service['name'], service['type'], service['url']) for service in self.services if service['type'] == self.server_types['feature']}
        print("Services loaded. Ready to go.")

    def print_all_services(self) -> None:
        """
        Print name, type, and URL of all services available through Esri server.

        Returns:
            None
        """
        for service_name, service_obj in self.service_table.items():
            print(f"Service name: {service_name}\nURL: {service_obj.url}\nService type: {service_obj.type}\n")

    def print_services_by_server_type(self, server_type: str = 'feature') -> None:
        """
        Print services given a server type.

        Args:
            server_type (str): The type of server to filter by ('feature', 'map', or 'wfs').

        Returns:
            None
        """
        try:
            server_type_key = self.server_types[server_type]
            for service_obj in self.service_table.values():
                if service_obj.type == server_type_key:
                    print(f"Service: {service_obj.name}\nURL: {service_obj.url}\nService type: {service_obj.type}")
        except KeyError:
            print(f"Invalid server type: {server_type}. Valid options are 'feature', 'map', or 'wfs'.")

    async def metadata_as_pandas(self, service_type: str = 'feature', included_services: List[str] = []) -> pd.DataFrame:
        """
        Asynchronously create a Pandas DataFrame of selected tables' metadata.

        Args:
            service_type (str): The type of service to include in the DataFrame ('feature', 'map', or 'wfs').
            included_services (List[str]): A list of service names to include in the DataFrame. If empty, all services are included.

        Returns:
            pd.DataFrame: A DataFrame containing the metadata of the selected services.
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


class FeatureServer():
    """
        Download data from an Esri Feature Server asynchronously.

        Attributes:
            feature_service (Service): The FeatureServer object.
            max_retries (int): The maximum number of retries for a request.
            retry_delay (int): The delay in seconds between retries.
            chunk_size (int): The number of records to download in each chunk.

        Usage:
            .. code-block:: python

                from Consensus.EsriConnector import FeatureServer
                from Consensus.OGP import OpenGeography
                from Consensus.utils import where_clause_maker

                og = OpenGeography(max_retries=30, retry_delay=2)
                await og.initialise()

                fs_service_table = og.service_table
                fs = FeatureServer()

                column_name = 'WD23NM'
                geographic_areas = ['Brockley']
                service_name = 'Wards_December_2023_Boundaries_UK_BSC'
                where_clause = where_clause_maker(string_list=geographic_areas, column_name=column_name, service_name=service_name)  # a helper function that creates the SQL where clause for Esri Servers

                await fs.setup(service_name=service_name, service_table=fs_service_table, max_retries=30, retry_delay=2, chunk_size=50)
                output = await fs.download(where_clause=where_clause, return_geometry=True)
                print(output)
    """
    def __init__(self) -> None:
        """
        Initialise class.

        Returns:
            None
        """
        pass

    async def setup(self, service_name: str = None, service_table: Dict[str, Service] = {}, max_retries: int = 10, retry_delay: int = 20, chunk_size: int = 50, layer_number: int = 0) -> None:
        """
        Set up the FeatureServer Service object for downloading.

        Args:
            service_name (str): The name of the Feature Server service.
            service_table (Dict[str, Service]): A dictionary of Feature Server Service objects.
            max_retries (int): The maximum number of retries for a request.
            retry_delay (int): The delay in seconds between retries.
            chunk_size (int): The number of records to download in each chunk.
            layer_number (int): The layer number to download (default: 0). Some feature services can have multiple layers (such as this: https://services1.arcgis.com/ESMARspQHYMw9BZ9/ArcGIS/rest/services/Pollution_Removal_2007_2011_2015_2030_GeoPackage/FeatureServer) and you may wish to download a specific version.

        Returns:
            None
        """
        try:
            self.feature_service = service_table.get(service_name).featureservers()

            self.max_retries = max_retries
            self.retry_delay = retry_delay
            self.chunk_size = chunk_size
            self.layer_number = layer_number

        except AttributeError as e:
            print(f"{e} - the selected table does not appear to have a feature server. Check table name exists in list of services or your spelling.")

        async with aiohttp.ClientSession() as session:
            await self.feature_service.lookup_format(session)

    async def looper(self, session: aiohttp.ClientSession, link_url: str, params: Dict[str, Any]) -> Dict:
        """
        Keep trying to connect to Feature Service until max_retries or response.

        Args:
            session (aiohttp.ClientSession): The aiohttp session.
            link_url (str): The URL of the Feature Server service.
            params (Dict[str, Any]): The parameters for the query.

        Returns:
            Dict: The downloaded data as a dictionary.
        """
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

    async def chunker(self, session: aiohttp.ClientSession, params: Dict[str, Any]) -> Dict:
        """
        Download data in chunks asynchronously.

        Args:
            session (aiohttp.ClientSession): The aiohttp session.
            params (Dict[str, Any]): The parameters for the query.

        Returns:
            Dict: The downloaded data as a dictionary.
        """

        params['resultOffset'] = 0
        params['resultRecordCount'] = self.chunk_size
        try:
            link_url = self.feature_service.download_urls[self.layer_number]
        except IndexError:
            link_url = self.feature_service.download_urls[0]
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

    async def download(self, fileformat: str = 'geojson', return_geometry: bool = False, where_clause: str = '1=1', output_fields: str = '*', params: dict = None, n_sample_rows: int = -1) -> pd.DataFrame:
        """
        Download data from Esri server asynchronously.

        Args:
            fileformat (str): The format of the downloaded data ('geojson', 'json', or 'csv').
            return_geometry (bool): Whether to include geometry in the downloaded data.
            where_clause (str): The where clause to filter the data.
            output_fields (str): The fields to include in the downloaded data.
            params (dict): Additional parameters for the query.
            n_sample_rows (int): The number of rows to sample for testing purposes.

        Returns:
            pd.DataFrame: The downloaded data as a pandas DataFrame or geopandas GeoDataFrame.
        """
        primary_key = self.feature_service.primary_key['name']

        if n_sample_rows > 0:
            where_clause = f"{primary_key}<={n_sample_rows}"
        if hasattr(self.feature_service, 'feature_server'):
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
                    responses = await self.chunker(session, params)
                except ZeroDivisionError:
                    print("No records found in this Service. Try another Feature Service.")

            if 'geometry' in responses['features'][0].keys():
                return gpd.GeoDataFrame.from_features(responses)
            else:
                df = pd.DataFrame(responses['features'])
                return df.apply(pd.Series)

        else:
            raise AttributeError("Feature service not found")
