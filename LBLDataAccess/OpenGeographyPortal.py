"""
@author: ISipila

OpenGeography class is for creating and updating a lookup table of the files in Open Geography Portal.

FeatureServer class is for downloading the content.

"""

from requests import get as request_get
from requests import request, exceptions
from dataclasses import dataclass
from typing import Any, Dict, List
import geopandas as gpd
import json
import re
from datetime import datetime
import pandas as pd 
from copy import deepcopy
import gc
from pathlib import Path
from LBLDataAccess import lookups
from LBLDataAccess.config_utils import load_config
from pkg_resources import resource_stream
import importlib.resources as pkg_resources
import time
import aiohttp
import asyncio

@dataclass
class Service:
    """
        Dataclass for services. 

        Attributes:
            name {str}  -   Name of service.
            type {str}  -   One of 'FeatureServer', 'MapServer', 'WFSServer'.
            url {str}   -   URL.
            description {str}   -   Description of the service.
            layers {List[Dict[str, Any]]}   -   Data available through service. If empty, it is likely that the 'tables' attribute contains the desired data.
            tables {List[Dict[str, Any]]}   -   Data available through service. If empty, it is likely that the 'layers' attribute contains the desired data.
            output_formats {List[str]}  -   List of formats available for the data.
            metadata {json} -   Metadata as JSON.
            fields {List[str]}  -   List of fields for the data.
            primary_key {str}   -   Primary key for the data.
    """

    name: str = None
    type: str = None
    url: str = None
    description: str = None
    layers: List[Dict[str, Any]] = None
    tables: List[Dict[str, Any]] = None
    output_formats: List[str] = None
    metadata: json = None
    fields: List[str] = None
    primary_key: str = None
            
    def featureservers(self) -> 'Service':
        """
            Self-filtering method.
        """
        if self.type == 'FeatureServer':
            self.feature_server = True
            return self

    def mapservers(self) -> 'Service':
        """
            Self-filtering method.
        """
        if self.type == 'MapServer':
            self.map_server = True
            return self

    def wfsservers(self) -> 'Service':
        """
            Self-filtering method.
        """
        if self.type == 'WFSServer':
            self.wfs_server = True
            return self

    def service_details(self) -> Any:
        """
            Returns high level details for the data as JSON.
        """
        service_url = f"{self.url}?&f=json"
        return request_get(service_url, timeout=5).json()
    
    def service_metadata(self) -> Any:
        """
            Returns metadata as JSON.
        """
        service_url = f"{self.url}/0?f=json"
        return request_get(service_url, timeout=5).json()
        
    def _service_attributes(self) -> None:
        """
            Fills attribute fields using the JSON information from service_details and service_metadata methods.
        """

        service_info = self.service_details()
        self.description = service_info.get('description')
        self.layers = service_info.get('layers', [])
        self.tables = service_info.get('tables', [])
        self.output_formats = service_info.get('supportedQueryFormats', [])

        self.metadata = self.service_metadata()
        if not self.description:
            self.description = self.metadata.get('description')
        self.fields = self.metadata.get('fields', [])
        self.primary_key = self.metadata.get('uniqueIdField')
        self.matchable_fields = [i['name'].upper() for i in self.fields if i['name'].upper() != self.primary_key]
        lastedit = self.metadata.get('editingInfo', {})
        try:
            self.lasteditdate = lastedit['lastEditDate']  # in milliseconds - to get time, use datetime.fromtimestamp(int(self.lasteditdate/1000)).strftime('%d-%m-%Y %H:%M:%S')
        except KeyError:
            self.lasteditdate = ''
        try:
            self.schemalasteditdate = lastedit['schemaLastEditDate']
        except KeyError:
            self.schemalasteditdate = ''        
        try:
            self.datalasteditdate = lastedit['dataLastEditDate']

        except KeyError:
            self.datalasteditdate = ''

    def lookup_format(self) -> Dict:
        """
            Returns a Pandas ready dictionary of the service's metadata 
        """
        self._service_attributes()
        
       
        
        try:
            self.data = {'name':[self.name], 'fields': [[field['name'] for field in self.fields]], 'url': [self.url], 'description': [self.description], 'primary_key': [self.primary_key['name']], 'lasteditdate': [self.lasteditdate]}
        except TypeError:
            self.data = {'name':[self.name], 'fields': [[field['name'] for field in self.fields]], 'url': [self.url], 'description': [self.description], 'primary_key': [self.primary_key['name']], 'lasteditdate': ['']}
         # add the field 'geometry' to services that are designated as layers as the underlying Esri REST API says: A feature service can contain datasets (for example, tables and views) with or without a spatial column. Datasets with a spatial column are considered layers; those without a spatial column are considered tables. A feature service allows clients to query and edit feature geometry and attributes.
        if self.layers:
            self.data['fields'][0].append('geometry')
            self.data['has_geometry'] = [True]
        else:
            self.data['has_geometry'] = [False]
        return self.data

    def print_service_attributes(self) -> None:
        """
            Prints key information about the service in an easily readable format.
        """
        self._service_attributes()
        print('Name:', self.name)
        print('Description:', self.description)
        print('Output formats:', self.output_formats)
        print('Layers:', self.layers)
        print('Tables:', self.tables)
        print('Fields:', self.fields)
        print('Primary key:', self.primary_key)

    

    def _record_count(self, url: str, params: Dict[str, str]) -> int:
        """
            Helper method for counting records.
        """
        temp_params = deepcopy(params)  # without deepcopy the changes in param propagates back to the download method
        temp_params['returnCountOnly'] = True
        #temp_params['where'] = '1=1'
        temp_params['f'] = 'json'
        try:
            return request_get(url, params=temp_params).json()['count']
        except KeyError:
            print(request_get(url, params=temp_params).json()['error']['details'][0])


class OpenGeography:
    """
        Main class for connecting to Open Geography API.

        Methods:
            print_all_services  -   Prints the name, URL, and server type of all services available through Open Geography API.
            print_services_by_server_type   -   Given a server type (one of 'feature', 'map' or 'wfs', default = 'feature'), print the services available. 

        Usage:
            Refer to FeatureServer class.


    """
    def __init__(self, max_retries=10, retry_delay=2) -> None:
        print("Connecting to Open Geography Portal")
        self.base_url = "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services?f=json"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.server_types = {'feature': 'FeatureServer', 'map': 'MapServer', 'wfs': 'WFSServer'}
        self.services = self._validate_response()
        

    def _validate_response(self) -> None:
        """
            Validate access to base URL.
        """
       
        print(f"Requesting services from URL: {self.base_url}")  # Debug statement
        
        attempts = 0
        while attempts < self.max_retries:
            response = request_get(self.base_url)
            if response.status_code == 200:
                print("Connection okay")
                services = response.json().get('services', [])
                if services:  # Check if the services list is not empty
                    print("Loading services")
                    self.services = services
                    self._load_all_services()
                    attempts += self.max_retries
                else:
                    print("Returned empty list of services, retrying...")
            else:
                print(f"Attempt {attempts + 1} failed with status code {response.status_code}. Retrying...")
            attempts += 1
            time.sleep(self.retry_delay)  # Wait before retrying
        if not services:
            print(f"Failed to retrieve services after {self.max_retries} attempts.")
                
    def _load_all_services(self) -> None:
        """
            Helper method to load services to a dictionary.
        """

        self.service_table = {}
        for service in self.services:
            service_obj = Service(service['name'], service['type'], service['url'])
            self.service_table[f"{service['name']}"] = service_obj
        print("Services loaded. You're good to go.")

    def print_all_services(self) -> None:
        """
            Print name, type, and url of all services available through Open Geography Portal.
        """
        for service_name, service_obj in self.service_table.items():
            print(f"Service: {service_name}\nURL: {service_obj.url}\nService type: {service_obj.type}\nService columns: {service_obj.fields}")

    def print_services_by_server_type(self, server_type: str = 'feature') -> None:
        """
            Print services given a server type. 

            Arguments:
                server_type {str}   -    The input to 'server_type' should be one of 'feature', 'map' or 'wfs' (default = 'feature'). Usually, it is enough to leave the server_type parameter unchanged, particularly as the MapServer and WFSServers are currently unsupported by this package.

        """
        try:            
            for service_name, service_obj in self.service_table.items():
                if service_obj.type == self.server_types[server_type]:
                    service_options = {
                                    'FeatureServer': service_obj.featureservers(), 
                                    'MapServer': service_obj.mapservers(), 
                                    'WFSServer': service_obj.wfsservers()
                                    }
                    service_info = service_options[self.server_types[server_type]]
                    print('Service:', service_info.name, '\nURL:', service_info.url, '\nServer type:', service_info.type, '\n Service columns:', {service_info.fields})
                else:
                    continue
        except KeyError:
            print(f"{server_type} is not an identifiable server type. Try one of 'feature', 'map', or 'wfs'")

class OpenGeographyLookup(OpenGeography):
    """
        Build and update a JSON lookup table for the Open Geography Portal's FeatureServers.

        Methods:
            metadata_as_pandas  -   This method can be used for comparing different data tables from Open Geography Portal as well as the basis for building a graph with SmartGeocodeLookup.
            build_lookup    -   Given a list of services, use this method to build a lookup JSON file that contains metadata about the services.
            update_lookup   -   Update the lookup JSON file by either adding new list of services

        Usage:

            ogl = OpenGeographyLookup()
            ogl.build_or_update_lookup()

            You can also provide a Path object to build_or_update_lookup() method as parent_path=Path(path_to_folder) if you want to specify where the lookup is stored, but the class will then always have to be provided that path for future updates. 

    """

    def __init__(self) -> None:
        super().__init__()

    def metadata_as_pandas(self, service_type: str = 'feature', included_services: List[str] = []) -> pd.DataFrame:
        """
            Make a Pandas Dataframe of selected tables. This method can be used for comparing different data tables from Open Geography Portal as well as the basis for building a graph with SmartGeocoder.

            Arguments:
                service_type {str}  -   Select the type of server. Must be one of 'feature', 'map', 'wfs'. (default = 'feature').
                included_services {List[str]}   -   An optional argument to select which services should be included in the set of tables to use for lookup. Each item of the list should be the name of the service (excluding the type of server in brackets). E.g. ['Age_16_24_TTWA'].
            
            Returns:
                pd.Dataframe    -   Pandas dataframe of the metadata.

        """
        
        assert service_type in ['feature', 'map', 'wfs'], "service_type not one of: 'feature', 'map', 'wfs'"

        if included_services:
            service_table_to_loop = {k: self.service_table.get(k, None) for k in included_services if k in self.service_table}

        else:
            service_table_to_loop = self.service_table

        relevant_service_table = {}
        for service_name, service_obj in service_table_to_loop.items():
            if str(service_obj.type).lower() == self.server_types[service_type].lower():
                relevant_service_table[service_name] = service_obj

        service_table_to_loop_copy = deepcopy(relevant_service_table)
        lookup_table = []
        
        services_need_adding = True
        while services_need_adding:
            print(f"Adding {len(service_table_to_loop_copy.keys())} services")
            for service_name, service_obj in relevant_service_table.items():
                if service_name in service_table_to_loop_copy.keys():
                    try:
                        print(f"Adding service {service_name}")
                        row_item = service_obj.lookup_format()
                        lookup_table.append(row_item)
                        service_table_to_loop_copy.pop(service_name)
                    except Exception as e:
                        print(f"Exception occurred for service {service_name}: {e}")
                        continue
            # To prevent infinite loop, let's add a break condition if no elements were removed
            if len(list(service_table_to_loop_copy.keys())) == 0:
                print("Finished adding all services")
                services_need_adding = False
        print("Creating Pandas dataframe")
        lookup_dfs = [pd.DataFrame.from_dict(item) for item in lookup_table]
        
        if len(lookup_dfs) == 0:
            print("No valid data found. Exiting.")
            return
        else:
            lookup_df = pd.concat(lookup_dfs)
            lookup_df.reset_index(inplace=True)
            lookup_df.drop(columns=['index'], inplace=True)
            """matchable_columns = []
            for field_item in lookup_df['fields']:
                fields = [i.upper() for i in field_item if i.upper().endswith('CD') and i.upper()[-4:-2].isnumeric()]
                matchable_columns.append(fields)
            lookup_df['matchable_fields'] = matchable_columns"""
            lookup_df['lasteditdate'] = lookup_df['lasteditdate']
            print("Pandas dataframe ready")
            return lookup_df
    
    def build_lookup(self, parent_path: Path = Path(__file__).resolve().parent, included_services: List[str] = [], replace_old: bool = True) -> pd.DataFrame:
        """
            Build lookup from scratch to a given path.

            Arguments:
                parent_path {Path}  -   pathlib object to folder where lookup.json is stored. This package uses Path(__file__).resolve().parent as default.
                included_services {List[str]}   -   List of names of services that a lookup should be built on. Default empty list will build a lookup based on all tables found in Open Geography Portal.
                replace_old {bool}  -   Change to False if you don't want to replace the old lookup table. If False, the method just returns a Pandas dataframe.
            
            Returns:
                pd.DataFrame    -   Lookup table as a Pandas dataframe.

        """
        # if lookup table hasn't been created, make one 
        lookup = self.metadata_as_pandas(included_services=included_services)
        
        if replace_old:
            # production version: 
            lookup.to_json(parent_path.joinpath('./lookups/lookup.json'))
            # testing version:
            #lookup.to_json(parent_path.joinpath('lookup.json'))

        return lookup

    def update_lookup(self, parent_path: Path = Path(__file__).resolve().parent, service_type:str = 'feature', full_check: bool = True) -> pd.DataFrame:
        """
            Update lookup.json file.

            Arguments:
                parent_path {Path}  -   pathlib object to folder where lookup.json is stored. This package uses Path(__file__).resolve().parent as default.
                service_type {str}  -   Select the type of server. Must be one of 'feature', 'map', 'wfs'. (default = 'feature').
                full_check {bool}   -   Set to False if you don't want to check when all tables were last updated.

            Returns:
                pd.DataFrame    -   An updated lookup table as Pandas dataframe.

        """
        
        # production version: 
        old_lookup = pd.read_json(resource_stream(__name__, 'lookups/lookup.json'))
        # testing version:
        # old_lookup = pd.read_json(parent_path.joinpath('lookup.json'))
        print("Found lookup.json, updating...")

        new_tables = []
        old_tables = []
        # first check which tables are old and if there are any new tables:
        print("Checking for any new tables")
        for service_name, service_obj in self.service_table.items():
            if str(service_obj.type).lower() == self.server_types[service_type].lower():
                if service_name not in old_lookup['name'].unique():
                    new_tables.append(service_name)
                else:
                    old_tables.append(service_name)
        print(f"Found {len(new_tables)} new tables")

        # check if an old table is still in use and if not, remove from old_table

        old_tables_copy = deepcopy(old_tables)
        for existing_table in old_tables_copy:
            if existing_table not in list(self.service_table.keys()):
                old_tables.remove(existing_table)

        tables_to_update = []
        # see if we also need to check when the the last update took place
        if full_check:
            # next, check if the last edit date in the lookup json is older than in the present data. 
            print("Checking which tables need updating")
            for enum, table in enumerate(old_tables):
                
                service_obj = self.service_table[table]
                metadata = service_obj.service_metadata()
                new_data_last_edit = metadata.get('editingInfo', {})['lastEditDate'] 

                try:
                    old_data_last_edit = old_lookup[old_lookup['name'] == table]['lasteditdate'].values[0]
                    if int(old_data_last_edit) < int(new_data_last_edit):
                        tables_to_update.append(table)
                except Exception as e:
                    print(f"No last editing date available for {table}, beware")
                    
            print(f"Checked {enum+1} of {len(old_tables_copy)} tables. {len(tables_to_update)} tables require updating. {len(old_tables_copy)-len(old_tables)} have been removed from the lookup")
            print(f"Found {len(tables_to_update)} tables that require updating")

        if len(new_tables) == 0 and len(tables_to_update) == 0 and len(old_tables_copy)-len(old_tables) == 0:
            print("No updates required, exiting.")
            return old_lookup
        
        else:
            # remove tables needing an update from the old lookup:
            old_lookup = old_lookup[~old_lookup['name'].isin(tables_to_update)] 
            # then create a Pandas dataframe from new tables and those needing an update:
            new_tables.extend(tables_to_update)
            print(f"\nUpdating or adding {len(new_tables)} tables to lookup.json:")
            new_lookup_df = self.metadata_as_pandas(included_services=new_tables)

            print("Combining old and new lookup data")
            updated_lookup = pd.concat([old_lookup, new_lookup_df], ignore_index=True)
            # production version: 
            updated_lookup.to_json(parent_path.joinpath('./lookups/lookup.json'))
            # testing version:
            #updated_lookup.to_json(parent_path.joinpath('lookup.json'))
            print(f"Finished updating lookup table (old lookup: {len(old_lookup)}, new lookup: {len(updated_lookup)})")

            return updated_lookup

    
    def build_or_update_lookup(self, **kwargs: Any) -> pd.DataFrame:
        """
            Quick method to build and update lookup.json.

            Arguments:
                **kwargs {Any}    -   Kwargs.

            Returns:
                pd.DataFrame    -   Lookup table as a Pandas dataframe.

        """

        parent_path = Path(__file__).resolve().parent
        try:
            return self.update_lookup(parent_path, **kwargs)

        except FileNotFoundError:
            print("Couldn't find lookup.json, building new lookup...")
            return self.build_lookup(parent_path, **kwargs)
    
    def read_lookup(self, lookup_folder: Path = None) -> pd.DataFrame:
        """
            Read lookup table.

            Arguments:
                lookup_folder {Path}    -   pathlib Path to the folder where lookup.json file is stored.
            
            Returns:
                pd.DataFrame    -   Lookup table as a Pandas dataframe.

        """

        if lookup_folder:
            json_path = Path(lookup_folder) / 'lookups' / 'lookup.json'
            return pd.read_json(json_path)
        else:
            with pkg_resources.open_text(lookups, 'lookup.json') as f:
                lookup_data = json.load(f)
            return pd.DataFrame(lookup_data)


class FeatureServer():

    """
        This class currently supports downloading data for FeatureServices.

        Methods:
            looper  -   Keep trying to connect to the Open Geography Portal's ESRI servers.
            chunker -   Don't overwhelm the servers, but make several smaller queries.
            download    -   Download the data for the table or layer. Supports SQL commands as part of the where_clause argument.
        
        Usage:
            max_retries = 10
            timeout = 20
            chunk_size = 50
            where_clause = '1=1' # SQL92 syntax - default means 'all'
            return_geometry = True  # default is False
            service_name = 'MSOA_2021_EW_BGC_V2'    # only an example - use OpenGeography().print_services_by_server_type() to view options

            service_table = OpenGeography().service_table
            fs = FeatureServer(service_name, service_table, max_retries, timeout, chunk_size)
            dl = fs.download(where_clause=where_clause, return_geometry=return_geometry)
            
    """

    def __init__(self, service_name: str = None, service_table: Dict[str, Any] = {}, max_retries: int = 10, timeout: int = 20, chunk_size: int = 50) -> None:
        try:
            
            self.feature_service = service_table.get(service_name).featureservers()
            self.feature_service.lookup_format()
            self.max_retries = max_retries
            self.timeout = timeout
            self.chunk_size = chunk_size

        except AttributeError as e:
            print(f"{e} - the selected table does not appear to have a feature server. Check table name exists in list of services or your spelling.")        

    def looper(self, link_url: str, params: Dict[str,str]) -> Any:
        """ Keep trying to connect to Feature Service until max_retries or response """
        retries = 0
        while retries < self.max_retries:
            try:
                response = request_get(link_url, params=params, timeout=self.timeout)
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"Error: {response.status_code} - {response.text}")
                    return None
            except exceptions.Timeout:
                retries += 1
                print(f"Timeout occurred. Retrying {retries}/{self.max_retries}...")
                time.sleep(2)

        print("Max retries reached. Request failed.")
        return None
    
    def chunker(self, service_url: str, params: Dict[str,str]) :
        """ Download data in chunks """
        if self.feature_service.tables:
            links_to_visit = self.feature_service.tables
        elif self.feature_service.layers:
            links_to_visit = self.feature_service.layers
        
        params['resultOffset'] = 0
        params['resultRecordCount'] = self.chunk_size

        # Visit first link
        link_url = f"{service_url}/{str(links_to_visit[0]['id'])}/query"
        print(f"Visiting link {link_url}")

        # Get the first response
        responses = self.looper(link_url, params)

        # Get the total number of records
        count = self.feature_service._record_count(link_url, params=params)
        print(f"Total records to download: {count}")

        counter = len(responses['features'])
        print(f"Downloaded {counter} out of {count} ({100 * (counter / count):.2f}%) items")

        # Continue fetching data until all records are downloaded
        while counter < int(count):
            params['resultOffset'] += self.chunk_size
            additional_response = self.looper(link_url, params)
            if not additional_response:
                break

            # Append features to the main response
            responses['features'].extend(additional_response['features'])
            counter += len(additional_response['features'])
            print(f"Downloaded {counter} out of {count} ({100 * (counter / count):.2f}%) items")

        return responses

    def download(self, fileformat: str = 'geojson', return_geometry: bool = False, where_clause: str = '1=1', output_fields: str = '*', params: Dict[str,str] = None, n_sample_rows: int = -1) -> Any:
        """
            Download data from Open Geography Portal.

            Arguments:
                fileformat {str}    -   The format in which to download the data (default: 'geojson').
                return_geometry {bool}  -   Whether the query should return the geometry field.
                where_clause {str}  -   SQL filter to apply to the rows (default: '1=1'). Open Geography Portal depends on Esri API, which uses SQL-92. This where clause can take the following instructions:

                    <COLUMN | LITERAL> '<=' | '>=' | '<' | '>' | '=' | '<>' <COLUMN | LITERAL>
                    <BOOLEAN EXPRESSION> AND | OR <BOOLEAN EXPRESSION>
                    NOT <BOOLEAN EXPRESSION>
                    <COLUMN> IS [ NOT ] NULL
                    <COLUMN> [ NOT ] LIKE <STRING>
                    <COLUMN> [ NOT ] IN ( <LITERAL, <LITERAL>, ... )
                    <COLUMN> [ NOT ] BETWEEN <COLUMN | LITERAL> AND <COLUMN | LITERAL>

                output_fields {str} -   Fields to include in the output (default: '*').
            
                params {Dict[str,str]}  -   If you want to manually override the search parameters. Only change if you cannot get the data otherwise or if you wish to do somethimg more sophisticated like use geometries as search terms. Some tables may allow you to send an input geometry as part of the parameter query and select the spatial relationship between the output and the input. For more information on how to format the 'geometry' attribute for the parameters, see https://developers.arcgis.com/rest/services-reference/enterprise/geometry-objects.htm. Note that polygons, envelopes, points, and lines all require slightly different formatting.

                n_sample_rows {int} -   This parameter helps with testing as it lets you quickly select the first n rows. It overrides the where_clause and uses the table's primary key to select top n rows. 

            Returns:
                List[Dict[str, Any]]    -   List of dictionaries representing the downloaded data.
        """
        self.feature_service._service_attributes()
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
            try:

                responses = self.chunker(service_url, params)
            except ZeroDivisionError:
                print("No records found in this Service. Try another Feature Service.")
            gc.collect()

            # Handle the response based on the data type
            if 'geometry' in responses['features'][0].keys():
                return gpd.GeoDataFrame.from_features(responses)
            else:
                df = pd.DataFrame(responses['features'])
                return df.apply(pd.Series)

        else:
            raise AttributeError("Feature service not found")


class AsyncFeatureServer():
    def __init__(self, service_name: str = None, service_table: dict = {}, max_retries: int = 10, timeout: int = 20, chunk_size: int = 50) -> None:
        try:
            self.feature_service = service_table.get(service_name).featureservers()
            self.feature_service.lookup_format()
            self.max_retries = max_retries
            self.timeout = timeout
            self.chunk_size = chunk_size
        except AttributeError as e:
            print(f"{e} - the selected table does not appear to have a feature server. Check table name exists in list of services or your spelling.")

    async def looper(self, session: aiohttp.ClientSession, link_url: str, params: dict) -> dict:
        """ Keep trying to connect to Feature Service until max_retries or response """
        retries = 0
        while retries < self.max_retries:
            try:
                async with session.get(link_url, params=params, timeout=self.timeout) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"Error: {response.status} - {await response.text()}")
                        return None
            except asyncio.TimeoutError:
                retries += 1
                print(f"Timeout occurred. Retrying {retries}/{self.max_retries}...")
                await asyncio.sleep(2)

        print("Max retries reached. Request failed.")
        return None

    async def chunker(self, session: aiohttp.ClientSession, service_url: str, params: dict) -> dict:
        """ Download data in chunks asynchronously """
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
        count = self.feature_service._record_count(link_url, params=params)
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
        self.feature_service._service_attributes()
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
                gc.collect()

                if 'geometry' in responses['features'][0].keys():
                    return gpd.GeoDataFrame.from_features(responses)
                else:
                    df = pd.DataFrame(responses['features'])
                    return df.apply(pd.Series)

        else:
            raise AttributeError("Feature service not found")