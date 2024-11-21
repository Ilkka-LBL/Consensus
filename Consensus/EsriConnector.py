"""
Extending ``EsriConnector()`` class
---------------------------------

This module provides a class for interacting with the Esri REST API. It creates a dictionary of Service objects given the URL of the server and add methods to extract the metadata for any of them.
You can apply the ``EsriConnector()`` class to a new server by calling ``my_new_connection=EsriConnector(base_url=your_new_server)`` or by creating a separate class if you so wish:

.. code-block:: python

    from Consensus.EsriConnector import EsriConnector

    class NewClass(EsriConnector):
        def __init__(self, max_retries: int = 10, retry_delay: int = 2) -> None:
            super().__init__(max_retries, retry_delay)
            self.base_url = your_new_server
            print(f"Connecting to {your_new_server}")

        def field_matching_condition(self, field: Dict[str, str]) -> bool:
            # accept only fields that end with 'CD' or 'NM'
            if field['name'].upper().endswith(('CD', 'NM')):
                return True


This is the basic building block that the Consensus package uses to interact with Esri REST APIs such as Open Geography Portal and TfL Open Data Hub. It is designed to be extended to provide additional functionality, such as custom methods for specific use cases.


``FeatureServer()`` class example
-------------------------------

``FeatureServer()`` class on the other hand is used to download data from the Esri REST API. For example, to download the ward 2023 boundary data for Brockley in Lewisham from Open Geography Portal:

.. code-block:: python

    from Consensus.EsriConnector import FeatureServer
    from Consensus.EsriServers import OpenGeography
    from Consensus.utils import where_clause_maker
    import asyncio

    async def download_test_data():
        og = OpenGeography(max_retries=30, retry_delay=2)
        await og.initialise()

        fs_service_table = og.service_table
        fs = FeatureServer()

        column_name = 'WD23NM'
        geographic_areas = ['Brockley']
        service_name = 'Wards_December_2023_Boundaries_UK_BSC'
        layers = og.select_layers_by_service(service_name=service_name)  # choose the first layer of the 'Wards_December_2023_Boundaries_UK_BSC' service
        layer_full_name = layers[0].full_name  # use the layer's ``full_name`` attribute to select it in ``fs.setup()`` and when creating the ``where_clause``

        where_clause = where_clause_maker(string_list=geographic_areas, column_name=column_name, service_name=layer_full_name)  # a helper function that creates the SQL where clause for Esri Servers

        await fs.setup(full_name=layer_full_name, service_table=fs_service_table, max_retries=30, retry_delay=2, chunk_size=50)
        output = await fs.download(where_clause=where_clause, return_geometry=True)
        print(output)

    asyncio.run(download_test_data())
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Callable
from copy import deepcopy
import aiohttp
import asyncio
import geopandas as gpd
import pandas as pd
from Consensus.config_utils import load_config
from pathlib import Path
import aiofiles
import platform
import sys

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@dataclass
class Layer:
    """
    Dataclass for layers.

    Attributes:
        full_name (str): The full name of the layer.
        service_name (str): The name of the service the layer belongs to.
        layer_name (str): The name of the layer.
        id (int): The ID of the layer.
        fields (List[str]): The list of fields in the layer.
        url (str): The URL of the layer.
        description (str): The description of the layer.
        primary_key (str): The primary key of the layer.
        matchable_fields (List[str]): The list of matchable fields in the layer.
        lasteditdate (str): The last edit date of the layer.
        data_from_layers (bool): Whether the layer is from a data source.
        has_geometry (bool): Whether the layer has geometry.
        type (str): The type of the layer.

    Methods:
        _record_count(session: aiohttp.ClientSession, proxy: str): Helper method for asynchronous GET requests using aiohttp. This is used by the FeatureServer class.
        _fetch(session: aiohttp.ClientSession, url: str, params: Dict[str, str] = None, proxy: str = None): Helper method for asynchronous GET requests using aiohttp.
    """

    full_name: str
    service_name: str
    layer_name: str
    id: int
    fields: List[str]
    url: str
    description: str
    primary_key: str
    matchable_fields: List[str]
    lasteditdate: str
    data_from_layers: bool
    has_geometry: bool
    type: str

    async def _record_count(self, session: aiohttp.ClientSession, url: str, params: Dict[str, str], proxy: str) -> int:
        """
        Helper method for counting records.

        Args:
            session (aiohttp.ClientSession): The aiohttp session object.
            url (str): The URL to fetch.
            params (Dict[str, str]): Query parameters.
            proxy (str): Proxy string that is passed to ``_fetch()`` method.

        Returns:
            int: The count of records for the chosen FeatureService
        """
        temp_params = deepcopy(params)
        temp_params['returnCountOnly'] = True
        temp_params['f'] = 'json'
        response = await self._fetch(session=session, url=url, params=temp_params, proxy=proxy)
        return response.get('count', 0)

    async def _fetch(self, session: aiohttp.ClientSession, url: str, params: Dict[str, str] = None, proxy: str = None) -> Dict[str, Any]:
        """
        Helper method for asynchronous GET requests using aiohttp.

        Args:
            session (aiohttp.ClientSession): The aiohttp session object.
            url (str): The URL to fetch.
            params (Dict[str, str]): Query parameters. Defaults to None.
            proxy (str): Proxy string.

        Returns:
            Dict[str, Any]: The response as a JSON object.
        """
        if params:
            # Convert boolean values to strings for params created in _record_count() method.
            params = {k: (str(v) if isinstance(v, bool) else v) for k, v in params.items()}

        async with session.get(url, params=params, timeout=10, proxy=proxy) as response:
            return await response.json()


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
        field_matching_condition (Callable[[Dict[str, str]], bool]): Condition for matchable fields. This method is used by ``Service()`` to filter the fields that are added to the matchable_fields columns, which is subsequently used by ``SmartLinker()`` for matching data tables. You can define your own ``field_matching_condition()`` method for each Esri server by extending the relevant ``EsriConnector()`` sub-class.

    Methods:
        featureservers(): Self-filtering method.
        mapservers(): Self-filtering method.
        wfsservers(): Self-filtering method.
        _fetch(session: aiohttp.ClientSession, url: str, params: Dict[str, str] = None, proxy: str = None): Helper method for asynchronous GET requests using aiohttp.
        service_details(session: aiohttp.ClientSession, proxy: str): Helper method for asynchronous GET requests using aiohttp. Gets more details about the service.
        get_download_urls(): Helper method for getting download URLs.
        service_metadata(self, session: aiohttp.ClientSession, proxy: str):  Helper method for asynchronous GET requests using aiohttp. Gets the metadata for the service.
        _matchable_fields(): Gets the matchable fields for the service based on the ``field_matching_condition()`` method.
        _service_attributes(session: aiohttp.ClientSession, proxy): Helper method for asynchronous GET requests using aiohttp. Gets the attributes for the service.
        get_layers(session: aiohttp.ClientSession, proxy: str): Main method that creates the lookup data format for the service.

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
    field_matching_condition: Callable[[Dict[str, str]], bool] = None

    def __postinit__(self):
        """
        Post-initialisation method.

        Returns:
            None
        """
        self.feature_server = False
        self.map_server = False
        self.wfs_server = False
        self.field_matching_condition = self.field_matching_condition

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

    async def _fetch(self, session: aiohttp.ClientSession, url: str, params: Dict[str, str] = None, proxy: str = None) -> Dict[str, Any]:
        """
        Helper method for asynchronous GET requests using aiohttp.

        Args:
            session (aiohttp.ClientSession): The aiohttp session object.
            url (str): The URL to fetch.
            params (Dict[str, str]): Query parameters. Defaults to None.
            proxy (str): Proxy string.

        Returns:
            Dict[str, Any]: The response as a JSON object.
        """
        if params:
            # Convert boolean values to strings for params created in _record_count() method.
            params = {k: (str(v) if isinstance(v, bool) else v) for k, v in params.items()}

        async with session.get(url, params=params, timeout=10, proxy=proxy) as response:
            return await response.json()

    async def service_details(self, session: aiohttp.ClientSession, proxy: str) -> Dict[str, Any]:
        """
        Returns high-level details for the data as JSON.

        Args:
            session (aiohttp.ClientSession): The aiohttp session object.
            proxy (str): Proxy string that is passed to ``_fetch()`` method.

        Returns:
            Dict[str, Any]: The service details as a JSON object.
        """
        service_url = f"{self.url}?&f=json"
        return await self._fetch(session=session, url=service_url, proxy=proxy)

    async def get_download_urls(self) -> List[str]:
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
            print('Something is wrong - neither tables nor layers were found. Report the issue to package maintainer.')
            download_urls = [f"{self.url}/0/query"]  # This should never execute. If it does, code needs fixing.
        return download_urls

    async def service_metadata(self, session: aiohttp.ClientSession, proxy: str) -> Dict[str, Any]:
        """
        Returns metadata as JSON.

        Args:
            session (aiohttp.ClientSession): The aiohttp session object.
            proxy (str): Proxy string that is passed to ``_fetch()`` method.

        Returns:
            Dict[str, Any]: The metadata as a JSON object.
        """

        if self.layers:
            metadata_urls = [f"{self.url}/{layer['id']}?f=json" for layer in self.layers]
        elif self.tables:
            metadata_urls = [f"{self.url}/{table['id']}?f=json" for table in self.tables]
        else:
            print('Something is wrong - neither tables nor layers were found. Report the issue to package maintainer.')
            metadata_urls = [f"{self.url}/0/?f=json"]  # This should never execute. If it does, code needs fixing.

        tasks = [self._fetch(session=session, url=url, proxy=proxy) for url in metadata_urls]
        metadata_responses = await asyncio.gather(*tasks)

        return metadata_responses

    async def _matchable_fields(self, fields: List[str]) -> List[str]:
        """
        Returns a list of matchable fields for the service. It uses the field_matching_condition() method that can be defined for any Esri ArcGIS server.

        Returns:
            List[str]: List of matchable fields.
        """
        if not callable(self.field_matching_condition):
            raise ValueError("Condition must be a callable function")

        async def apply_condition(field):
            # Check if the condition is async or sync
            if asyncio.iscoroutinefunction(self.field_matching_condition):
                return await self.field_matching_condition(field)
            else:
                return self.field_matching_condition(field)

        return [i['name'].upper() for i in fields if await apply_condition(i)] if fields else []  # i['name'].upper() should not be changed - this enables SmartLinker() to function on standardised column names

    async def _service_attributes(self, session: aiohttp.ClientSession, proxy) -> None:
        """
        Fills attribute fields using the JSON information from service_details and service_metadata methods.

        Args:
            session (aiohttp.ClientSession): The aiohttp session object.
            proxy (str): Proxy string that is passed to ``_fetch()`` method.

        Returns:
            None
        """
        service_info = await self.service_details(session=session, proxy=proxy)

        self.description = service_info.get('description')
        self.layers = service_info.get('layers', [])
        self.tables = service_info.get('tables', [])
        self.output_formats = service_info.get('supportedQueryFormats', [])
        self.download_urls = await self.get_download_urls()

    async def get_layers(self, session: aiohttp.ClientSession, proxy: str) -> Dict[str, List]:
        """
        Returns a Pandas-ready dictionary of the service's metadata.

        Args:
            session (aiohttp.ClientSession): The aiohttp session object.
            proxy (str): Proxy string that is passed to ``_fetch()`` method.

        Returns:
            Dict[str, List]: A dictionary of the FeatureService's metadata.
        """
        await self._service_attributes(session=session, proxy=proxy)

        metadata = await self.service_metadata(session=session, proxy=proxy)

        data_collection = []
        layers_or_tables = self.layers if self.layers else self.tables
        for dataset, layer_or_table, download_url in zip(metadata, layers_or_tables, self.download_urls):

            fields = dataset.get('fields', [])
            description = dataset.get('description')
            primary_key = dataset.get('uniqueIdField')
            lastedit = dataset.get('editingInfo', {})
            lasteditdate = lastedit.get('lastEditDate', '')
            matchable_fields = await self._matchable_fields(fields)
            has_geometry = dataset.get('supportsReturningQueryGeometry', False)
            fields = [field['name'] for field in fields]
            if has_geometry:
                fields.append('geometry')
            if self.layers:
                data_from_layers = True
            else:
                data_from_layers = False
            try:
                layer_obj = Layer(f"{self.name} - {layer_or_table['name']}",
                                  self.name,
                                  layer_or_table['name'],
                                  layer_or_table['id'],
                                  fields,
                                  download_url,
                                  description,
                                  primary_key['name'],
                                  matchable_fields,
                                  lasteditdate,
                                  data_from_layers,
                                  has_geometry,
                                  self.type)
            except Exception:
                print(f"Error creating Layer object for {self.name} - {layer_or_table['name']}.")
                sys.exit()
            data_collection.append(layer_obj)
        return data_collection


class EsriConnector:
    """
    Main class for connecting to Esri servers. This class uses ``Consensus.ConfigManager.ConfigManager()`` to load the ``config.json`` file for proxies. Specifically, the class uses https proxy.

    Attributes:
        base_url (str): The base URL of the Esri server. Built-in modules that use ``EsriConnector()`` class set their own base_url.
        max_retries (int): The maximum number of retries for HTTP requests.
        retry_delay (int): The delay in seconds between retries.
        server_types (Dict[str, str]): A dictionary of server types and their corresponding suffixes.
        services (List[Service]): A list of Service objects.
        service_table (pd.DataFrame): A Pandas DataFrame containing the service metadata.

    Methods:
        __init__(max_retries: int = 10, retry_delay: int = 2, server_type: str = 'feature', base_url: str = "", proxy: str = None, matchable_fields_extension: List[str] = []): Initialise class.
        field_matching_condition(field: Dict[str, str]): Condition for matchable fields. This method is used by ``Service()`` to filter the fields that are added to the matchable_fields columns, which is subsequently used by ``SmartLinker()`` for matching data tables.
        initialise(): Initialise class. Must be called to initialise the async session and run the async tasks.
        _validate_response(): Validate the response from the Esri server.
        _fetch_response(session: aiohttp.ClientSession): Helper method to get response from Esri server.
        get_layer_obj(service: Dict[str, str], session: aiohttp.ClientSession): Call the ``get_layers()`` method for a Service object to get the list of Layer objects.
        _load_all_services(): Load all services from the Esri server into ``self.service_table``
        print_object_data(layer_obj: Layer): Print the object metadata.
        print_all_services(): Print all services from the Esri server.
        select_layers_by_service(service_name: str): Return the list of Layer objects for a given service.
        select_layers_by_layers(layer_name: str): Find all Layer objects that share the same name.
        metadata_as_pandas(included_services: List[str] = []): Return the metadata of the services as a Pandas DataFrame.
        build_lookup(parent_path: Path = Path(__file__).resolve().parent, included_services: List[str] = [], replace_old: bool = True): Build a lookup table of the services. This method will call ``metadata_as_pandas()`` for each service and return a Pandas DataFrame as well as builds a json lookup file.

    """
    def __init__(self, max_retries: int = 10, retry_delay: int = 2, server_type: str = 'feature', base_url: str = "", proxy: str = None, matchable_fields_extension: List[str] = []) -> None:
        """
        Initialise class.

        Args:
            max_retries (int): The maximum number of retries for HTTP requests. Defaults to 10.
            retry_delay (int): The delay in seconds between retries. Defaults to 2.
            base_url (str): The base URL of the Esri server. Defaults to "". Built-in modules that use ``EsriConnector()`` class set their own base_url.
            proxy (str): The proxy URL to use for requests. Defaults to None. Leave empty to make use of ``ConfigManager()``.

        Returns:
            None
        """
        self._name = ''
        self.base_url = base_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.server_type = server_type
        self.matchable_fields_extension = ([field.upper() for field in matchable_fields_extension] if matchable_fields_extension else [])

        self.server_types = {'feature': 'FeatureServer',
                             'map': 'MapServer',
                             'wfs': 'WFSServer'}
        assert self.server_type in self.server_types.keys(), "Service type must be one of: 'feature', 'map', 'wfs'"
        self.services = []
        self.service_table = None
        config = load_config()
        self.proxy = proxy if proxy is not None else config.get('proxies', None).get('https', None)

    async def field_matching_condition(self, field: Dict[str, str]) -> bool:
        """
        Condition for matchable fields. This method is used by ``Service()`` to filter the fields that are added to the matchable_fields columns, which is subsequently used by ``SmartLinker()`` for matching data tables.
        This method is meant to be overwritten by the user if they want to change the condition for matchable fields. Each Esri ArcGIS server will have its own rules, so this will be left for the user to deal with.
        If you are using a built-in server (e.g. TFL or Open Geography Portal), then you don't have to touch this method.

        Args:
            field (Dict[str, str]): The field dictionary. This is the input coming from ``Service()``. This method should always accept a metadata dictionary describing the field.

        Returns:
            bool: default is True if the field name is in ``matchable_fields_extension``, otherwise False.
        """
        if (field['type'].upper() == 'ESRIFIELDTYPESTRING' and field['name'].upper() not in ['GLOBALID', 'FID', 'ID', 'OBJECTID']) or (field['name'].upper() in self.matchable_fields_extension):
            return True

    async def initialise(self) -> None:
        """
        Run this method to initialise the class session.

        Returns:
            None
        """
        print(f"Connecting to {self._name}")
        await self._validate_response()

    async def _validate_response(self) -> None:
        """
        Validate access to the base URL asynchronously using aiohttp. When a response is received, call ``_load_all_services()`` to load services into a dictionary.

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

    async def _fetch_response(self, session: aiohttp.ClientSession) -> Dict:
        """
        Helper method to fetch the response from the Esri server.

        Args:
            session (aiohttp.ClientSession): The aiohttp.ClientSession object.

        Returns:
            Dict: The JSON response from the Esri server.
        """
        async with session.get(self.base_url, proxy=self.proxy) as response:
            return await response.json() if response.status == 200 else {}

    async def get_layer_obj(self, service: Dict[str, str], session: aiohttp.ClientSession) -> None:
        """
        Fetch metadata for a service and add it to the service table.

        Args:
            service (Dict[str, str]): Dictionary of services.
            session (aiohttp.ClientSession): The aiohttp.ClientSession object.

        Returns:
            None
        """
        print(f"Fetching metadata for service {service['name']}")
        serv_obj = Service(service['name'], service['type'], service['url'], field_matching_condition=self.field_matching_condition)
        layer_objects = await serv_obj.get_layers(session=session, proxy=self.proxy)
        for obj in layer_objects:
            print(f"Adding layer {obj.layer_name} to service table")
            self.service_table[obj.full_name] = obj

    async def _load_all_services(self) -> None:
        """
        Load services into a dictionary.

        Returns:
            None
        """
        self.service_table = {}
        async with aiohttp.ClientSession() as session:
            tasks = [self.get_layer_obj(service, session) for service in self.services if service['type'].lower() == self.server_types[self.server_type].lower()]
            await asyncio.gather(*tasks)

        print("All services loaded. Ready to go.")

    def print_object_data(self, layer_obj: Layer) -> None:
        """
        Print the data of a Layer object.

        Args:
            layer_obj (Layer): The Layer object to print.

        Returns:
            None

        Added in version 1.1.1.
        """
        print(f"Full name: {layer_obj.full_name}\nService name: {layer_obj.service_name}\nLayer name: {layer_obj.layer_name}\nURL: {layer_obj.url}\nAvailable fields: {layer_obj.fields}\nService type: {layer_obj.type}\n")

    def print_all_services(self) -> None:
        """
        Print name, type, and URL of all services available through Esri server.

        Returns:
            None
        """
        for _, layer_obj in self.service_table.items():
            self.print_object_data(layer_obj)

    def select_layers_by_service(self, service_name: str) -> List[Any]:
        """
        Print and output a subset of the service table.

        Args:
            service_name (str): The name of the service to print.

        Returns:
            List[Any]: A list of Layer objects for the selected service.

        Added in version 1.1.0
        """
        layer_objects = []
        for _, layer_obj in self.service_table.items():
            if layer_obj.service_name == service_name:
                self.print_object_data(layer_obj)
                layer_objects.append(layer_obj)
        return layer_objects

    def select_layers_by_layers(self, layer_name: str) -> List[Any]:
        """
        Print a subset of the service table.

        Args:
            layer_name (str): The name of the layer to print.

        Returns:
            List[Any]: A list of Layer objects for the selected service.

        Added in version 1.1.0
        """
        layer_objects = []
        for _, layer_obj in self.service_table.items():
            if layer_obj.layer_name == layer_name:
                self.print_object_data(layer_obj)
                layer_objects.append(layer_obj)
        return layer_objects

    async def metadata_as_pandas(self, included_services: List[str] = []) -> pd.DataFrame:
        """
        Asynchronously create a Pandas DataFrame of selected tables' metadata.

        Args:
            included_services (List[str]): A list of service names to include in the DataFrame. If empty, all services are included.

        Returns:
            pd.DataFrame: A DataFrame containing the metadata of the selected services.
        """
        service_table_to_loop = {k: self.service_table[k] for k in included_services if k in self.service_table} if included_services else self.service_table
        relevant_services = {name: obj for name, obj in service_table_to_loop.items() if obj.type.lower() == self.server_types[self.server_type].lower()}
        lookup_table = [service_obj for _, service_obj in relevant_services.items()]
        return lookup_table

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
        print("Transforming data to pandas")
        lookup_df = await self.metadata_as_pandas(included_services=included_services)
        lookup_df = pd.DataFrame().from_dict(lookup_df)
        print("Writing data")
        if replace_old:
            async with aiofiles.open(parent_path / f'lookups/{self._name}_lookup.json', 'w') as f:
                await f.write(lookup_df.to_json())
        return lookup_df


class FeatureServer():
    """
    Download data from an Esri Feature Server asynchronously. This class uses ``Consensus.ConfigManager.ConfigManager()`` to load the ``config.json`` file for proxies. Specifically, the class uses https proxy.

    Attributes:
        feature_service (Layer): The Layer object.
        max_retries (int): The maximum number of retries for a request.
        retry_delay (int): The delay in seconds between retries.
        chunk_size (int): The number of records to download in each chunk.

    Methods:
        __init__(proxy: str): Initialise class.
        setup(full_name: str, service_name: str, layer_name: str, service_table: Dict[str, Service], max_retries: int, retry_delay: int, chunk_size: int): Set up the FeatureServer Service object for downloading. You must give either the full_name or service_name and layer_name, as well as the service_table.
        looper(session: aiohttp.ClientSession, link_url: str, params: Dict[str, Any]): Method to keep attempting to download data if connection lost.
        chunker(session: aiohttp.ClientSession, params: Dict[str, Any]): Splits the download by ``chunk_size``
        download(fileformat: str, return_geometry: bool, where_clause: str, output_fields: str, params: Dict[str, str], n_sample_rows: int): Download data from the FeatureServer asynchronously.

    Usage:
        .. code-block:: python

            # In this example, we're using ``OpenGeography()`` sub-class

            from Consensus.EsriConnector import FeatureServer
            from Consensus.EsriServers import OpenGeography
            from Consensus.utils import where_clause_maker
            import asyncio

            async def download_test_data():
                og = OpenGeography(max_retries=30, retry_delay=2)
                await og.initialise()

                fs_service_table = og.service_table
                fs = FeatureServer()

                column_name = 'WD23NM'
                geographic_areas = ['Brockley']
                service_name = 'Wards_December_2023_Boundaries_UK_BSC'
                layers = og.select_layers_by_service(service_name=service_name)  # choose the first layer of the 'Wards_December_2023_Boundaries_UK_BSC' service
                layer_full_name = layers[0].full_name  # use the layer's ``full_name`` attribute to select it in ``fs.setup()`` and when creating the ``where_clause``

                where_clause = where_clause_maker(string_list=geographic_areas, column_name=column_name, service_name=layer_full_name)  # a helper function that creates the SQL where clause for Esri Servers

                await fs.setup(full_name=layer_full_name, service_table=fs_service_table, max_retries=30, retry_delay=2, chunk_size=50)
                output = await fs.download(where_clause=where_clause, return_geometry=True)
                print(output)

            asyncio.run(download_test_data())
    """
    def __init__(self, proxy: str = None) -> None:
        """
        Initialise class.

        Args:
            proxy (str): The proxy URL to use for requests. Defaults to None. Leave empty to make use of ``ConfigManager()``.

        Returns:
            None
        """
        config = load_config()
        self.proxy = proxy if proxy is not None else config.get('proxies', None).get('https', None)

    async def setup(self, full_name: str = None, service_name: str = None, layer_name: str = None, service_table: Dict[str, Layer] = {}, max_retries: int = 10, retry_delay: int = 20, chunk_size: int = 50) -> None:
        """
        Set up the FeatureServer Service object for downloading.

        Args:
            full_name (str): The full name of the Feature Server service. Provide a value for either this argument or alternatively to ``service_name`` and ``layer_name``, which the method builds the ``full_name``.
            service_name (str): The name of the Feature Server service. Provide a value together with ``layer_name``.
            layer_name (str): The name of the layer to download. Provide a value together with ``service_name``.
            service_table (Dict[str, Layer]): Mandatory. A dictionary of Feature Server Layer objects.
            max_retries (int): The maximum number of retries for a request.
            retry_delay (int): The delay in seconds between retries.
            chunk_size (int): The number of records to download in each chunk.

        Returns:
            None
        """
        try:
            if not full_name:
                full_name = f"{service_name} - {layer_name}"
            self.feature_service = service_table.get(full_name)

            self.max_retries = max_retries
            self.retry_delay = retry_delay
            self.chunk_size = chunk_size

        except AttributeError as e:
            print(f"{e} - the selected table does not appear to have a feature server. Check table name exists in list of services or your spelling.")

    async def looper(self, session: aiohttp.ClientSession, link_url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Keep trying to connect to Feature Service until max_retries or response.

        Args:
            session (aiohttp.ClientSession): The aiohttp session.
            link_url (str): The URL of the Feature Server service.
            params (Dict[str, Any]): The parameters for the query.

        Returns:
            Dict[str, Any]: The downloaded data as a dictionary.
        """
        retries = 0
        while retries < self.max_retries:
            try:
                async with session.get(url=link_url, params=params, timeout=self.retry_delay, proxy=self.proxy) as response:
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

    async def chunker(self, session: aiohttp.ClientSession, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download data in chunks asynchronously.

        Args:
            session (aiohttp.ClientSession): The aiohttp session.
            params (Dict[str, Any]): The parameters for the query.

        Returns:
            Dict[str, Any]: The downloaded data as a dictionary.
        """

        params['resultOffset'] = 0
        params['resultRecordCount'] = self.chunk_size
        link_url = self.feature_service.url
        print(f"Visiting link {link_url}")

        # Get the first response
        responses = await self.looper(session, link_url, params)

        # Get the total number of records
        count = await self.feature_service._record_count(session=session, url=link_url, params=params, proxy=self.proxy)
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

    async def download(self, fileformat: str = 'geojson', return_geometry: bool = False, where_clause: str = '1=1', output_fields: str = '*', params: Dict[str, Any] = None, n_sample_rows: int = -1) -> pd.DataFrame:
        """
        Download data from Esri server asynchronously.

        Args:
            fileformat (str): The format of the downloaded data ('geojson', 'json', or 'csv'). Perhaps best kept as geojson.
            return_geometry (bool): Whether to include geometry in the downloaded data.
            where_clause (str): The where clause to filter the data.
            output_fields (str): The fields to include in the downloaded data.
            params (Dict[str, Any]): Additional parameters for the query.
            n_sample_rows (int): The number of rows to sample for testing purposes.

        Returns:
            pd.DataFrame: The downloaded data as a pandas DataFrame or geopandas GeoDataFrame.
        """
        primary_key = self.feature_service.primary_key

        if n_sample_rows > 0:
            where_clause = f"{primary_key}<={n_sample_rows}"
        if hasattr(self.feature_service, 'type') and self.feature_service.type.lower() == 'featureserver':
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
