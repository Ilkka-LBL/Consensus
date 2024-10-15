"""
Created on Wed Dec 14 10:50:56 2022.

@author: ISipila

Get a NOMIS api key by registering with NOMIS. When initialising the DownloadFromNomis class, provide the api key as a parameter to the 
api_key argument. If you need proxies to access the data, provide the information as a dictionary to proxies. There is also a convenience 
argument to memorize these settings for later. For example:
    
    api_key = '02bdlfsjkd3idk32j3jeaasd2'                                # this is an example of random string from NOMIS website
    proxies = {'http': your_proxy_address, 'https': your_proxy_address}  # proxy dictionary must follow this pattern. If you only have http
                                                                         # proxy, copy it to the https without changing it

    connect_to_nomis = DownloadFromNomis(api_key=api_key, proxies=proxies, memorize=True)
    connect_to_nomis.connect()


"""
from pathlib import Path
from requests import get as request_get
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from shutil import copyfileobj
import pandas as pd
from Consensus.config_utils import load_config

class ConnectToNomis:
    """ Get NOMIS data.
        api_key: Nomis API key
        proxies: HTTP and HTTPS proxy addresses as a dictionary {'http': http_addr, 'https': https_addr} (optional)
        memorize: Set to True to save API key and proxies in a plain text file.
    """
    
    def __init__(self, api_key: str = None, proxies: Dict[str, str] = None):
        """Initialize ConnectToNomis."""
        self.config = load_config()
        self.api_key = api_key or self.config.get('nomis_api_key', '').strip()
        
        assert self.api_key, "nomis_api_key key not provided or found in config/config.json."

        self.uid = f"?uid={self.api_key}"  # This comes at the end of each API call
        self.base_url = "http://www.nomisweb.co.uk/api/v01/dataset/"
        self.url = None
        self.proxies = proxies or self.config.get('proxies', {})
        
    

    def url_creator(self, dataset: str, params: Dict[str, List[str]] = None, 
                    select_columns: List[str] = None, for_download: bool = False):
        """Create a URL string for data download."""
        if not dataset:
            self.url = f"{self.base_url}def.sdmx.json{self.uid}"
            return
        
        table_url = f"{self.base_url}{dataset}.data.csv?"
        
        if params:
            for keyword, qualifier_codes in params.items():
                assert isinstance(qualifier_codes, list), "params should be of type Dict[str, List[str]]."
                if keyword == 'geography':
                    search_string = self._unpack_geography_list(qualifier_codes)
                else:
                    search_string = ','.join(qualifier_codes)
                table_url += f"{keyword}={search_string}&"
                    
        if select_columns:
            selection = 'select=' + ','.join(select_columns) + '&'
            table_url += selection
        
        self.url = f"{table_url}{self.uid[1:]}".strip()

    def connect(self, url: str = None):
        """Connect to NOMIS data to get the table structures."""
        if url:
            self.url = url
        else:
            self.url_creator(dataset=None)
            
        try:
            self.r = request_get(self.url, proxies=self.proxies)
        except KeyError:
            print("Proxies not set, attempting to connect without proxies.")
            self.r = request_get(self.url)
        
        if self.r.status_code == 200:
            print("Connection successful.")
        else:
            print("Could not connect to NOMIS. Check your API key and proxies.")

    def get_all_tables(self) -> List[Any]:
        """Get all available tables."""
        assert self.r.status_code == 200, "Connection not successful."
        main_dict = self.r.json()
        tables_data = main_dict['structure']['keyfamilies']['keyfamily']
        return [NomisTable(**table) for table in tables_data]

    def print_table_info(self):
        """Print information for all tables."""
        tables = self.get_all_tables()
        for table in tables:
            table.table_shorthand()

    def detailed_info_for_table(self, table_name: str):
        """Print information for a chosen table."""
        table = self._find_exact_table(table_name)
        table.detailed_description()

    def _find_exact_table(self, table_name: str):
        """Return the matching table for the given name."""
        tables = self.get_all_tables()
        for table in tables:
            if table.id == table_name:
                return table
            
    def _geography_edges(self, nums: List[int]) -> List[Any]:
        """Find edges in a list of integers."""
        nums = sorted(set(nums))
        gaps = [[s, e] for s, e in zip(nums, nums[1:]) if s + 1 < e]
        edges = iter(nums[:1] + sum(gaps, []) + nums[-1:])
        return list(zip(edges, edges))

    def _create_geography_e_code(self, val: int) -> str:
        """Create a nine-character GSS code (e.g., Exxxxxxxx)."""
        return f"E{val:08}"

    def _unpack_geography_list(self, geographies: List[str]) -> str:
        """Unpack a list of GSS codes, find the edges, and format for URL."""
        edited_geo = [int(i[1:]) for i in sorted(geographies)]
        edges_list = self._geography_edges(edited_geo)
        list_to_concat = []

        for edge in edges_list:
            if edge[1] == edge[0]:
                list_to_concat.append(self._create_geography_e_code(edge[0]))
            elif edge[1] - edge[0] == 1:
                list_to_concat.extend([self._create_geography_e_code(edge[0]), self._create_geography_e_code(edge[1])])
            else:
                list_to_concat.append(f"{self._create_geography_e_code(edge[0])}...{self._create_geography_e_code(edge[1])}")

        return ','.join(list_to_concat)


class DownloadFromNomis(ConnectToNomis):
    """Wrapper class for downloading data from the NOMIS API."""

    def __init__(self, *args, **kwargs):
        """Initialize DownloadFromNomis."""
        super().__init__(*args, **kwargs)

    def _bulk_download_url(self, dataset: str):
        """Create a URL string for bulk download."""
        self.url = f"{self.base_url}{dataset}.bulk.csv{self.uid}"

    def _download_checks(self, dataset: str, params: Dict['str', List], value_or_percent: str, table_columns: List[str]):
        if params is None:
            params = {'geography': None}

        if value_or_percent == 'percent':
            params['measures'] = [20301]
        elif value_or_percent == 'value':
            params['measures'] = [20100]

        self.url_creator(dataset, params, table_columns, for_download=True)

    def table_to_csv(self,
                     dataset: str,
                     params: Dict[str, List] = None,
                     file_name: str = None,
                     table_columns: List[str] = None,
                     save_location: str = '../nomis_download/',
                     value_or_percent: str = None):
        """
        Download tables as CSV files.

        Parameters:
        - dataset (str): The dataset string (e.g., NM_2021_1).
        - params (Dict[str, List], optional): Qualifier dictionary (e.g., {'geography': [E00016136], 'age': [0, 2, 3]}). Defaults to None.
        - file_name (str, optional): Custom file name for saving. Defaults to None.
        - table_columns (List[str], optional): List of columns to include. Defaults to None.
        - save_location (str, optional): Directory to save the CSV file. Defaults to '../nomis_download/'.
        - value_or_percent (str, optional): Specify 'value' or 'percent' to download only values or percentages. Defaults to None.
        """


        self._download_checks(dataset, params, value_or_percent, table_columns)

        if file_name is None:
            file_name = f"{dataset}_query.csv"

        save_path = Path(save_location)
        save_path.mkdir(parents=True, exist_ok=True)

        file_name = save_path.joinpath(file_name)
        self._download_file(file_name)

    def bulk_download(self, dataset: str, data_format: str = 'pandas', save_location: str = '../nomis_download/'):
        """
        Download bulk data as CSV or as a Pandas DataFrame.

        Parameters:
        - dataset (str): The dataset string (e.g., NM_2021_1).
        - data_format (str, optional): 'csv', 'download', 'pandas', or 'df'. Defaults to 'pandas'.
        - save_location (str, optional): Directory to save the CSV file. Defaults to '../nomis_download/'.
        """
        self._bulk_download_url(dataset)
        assert data_format in ['csv', 'download', 'pandas', 'df'], \
            'Data format must be one of "csv" (or "download") or "pandas" (or "df").'

        if data_format in ['csv', 'download']:
            file_name = f"{dataset}_bulk.csv"
            save_path = Path(save_location)
            save_path.mkdir(parents=True, exist_ok=True)
            file_name = save_path.joinpath(file_name)
            self._download_file(file_name)
        elif data_format in ['pandas', 'df']:
            return self._download_to_pandas()

    def download(self,
                 dataset: str,
                 params: Dict[str, List] = None,
                 table_columns: List[str] = None,
                 value_or_percent: str = None):
        """
        Download tables to a Pandas DataFrame.

        Parameters:
        - dataset (str): The dataset string (e.g., NM_2021_1).
        - params (Dict[str, List], optional): Parameter dictionary (e.g., {'geography': [E00016136], 'age': [0, 2, 3]}). Defaults to None.
        - table_columns (List[str], optional): List of columns to include. Defaults to None.
        - value_or_percent (str, optional): Specify 'value' or 'percent' to download only values or percentages. Defaults to None.

        Returns:
        - pd.DataFrame: The downloaded data as a Pandas DataFrame.
        """
        self._download_checks(dataset, params, value_or_percent, table_columns)
        return self._download_to_pandas()

    def _download_file(self, file_path: Path):
        """Helper method to download a file from the created URL."""
        try:
            with request_get(self.url, proxies=self.proxies, stream=True) as response:
                with open(file_path, 'wb') as file:
                    copyfileobj(response.raw, file)
        except AttributeError:
            with request_get(self.url, stream=True) as response:
                with open(file_path, 'wb') as file:
                    copyfileobj(response.raw, file)

    def _download_to_pandas(self) -> pd.DataFrame:
        """Helper method to download data as a Pandas DataFrame."""
        try:
            with request_get(self.url, proxies=self.proxies, stream=True) as response:
                return pd.read_csv(response.raw)
        except AttributeError:
            with request_get(self.url, stream=True) as response:
                return pd.read_csv(response.raw)
        except Exception as e:
            print(e)
            print('Try using the get_bulk() method instead.')



    
@dataclass
class NomisTable:
    """
    A dataclass representing a structured output from NOMIS, a UK-based data source.

    This class is designed to encapsulate the metadata and structure of a table retrieved from the NOMIS API. 
    It provides methods for accessing detailed descriptions, annotations, and column information in a readable format.

    Attributes:
    -----------
    agencyid : str
        The ID of the agency that owns the table.
    annotations : Dict[str, Any]
        A dictionary containing annotations related to the table.
    id : str
        The unique identifier of the table.
    components : Dict[str, Any]
        A dictionary containing information about the components (columns) of the table.
    name : Dict[str, Any]
        A dictionary containing the name of the table.
    uri : str
        The URI that links to more information about the table.
    version : str
        The version number of the table.
    description : Optional[str]
        An optional description of the table.

    Methods:
    --------
    detailed_description() -> None:
        Prints a detailed and cleaned overview of the table, including its ID, description, annotations, and columns.

    clean_annotations() -> List[str]:
        Cleans the annotations for more readable presentation and returns them as a list of strings.

    table_cols() -> List[str]:
        Cleans and returns the column information for the table in a readable format.

    get_table_cols() -> List[Tuple[str, str]]:
        Returns a list of tuples, where each tuple contains a column code and its corresponding description.

    table_shorthand() -> str:
        Returns a shorthand description of the table, including its ID and name.
    """

    agencyid: str
    annotations: Dict[str, Any]
    id: str 
    components: Dict[str, Any]
    name: Dict[str, Any]
    uri: str
    version: str
    description: Optional[str] = None
    
    def detailed_description(self) -> None:
        """Prints a detailed and cleaned overview of the table, including its ID, description, annotations, and columns."""
        print(f"\nTable ID: {self.id}\n")
        print(f"Table Description: {self.name['value']}\n")
        for table_annotation in self.clean_annotations():
            print(table_annotation)
        print("\n")
        for column_codes in self.table_cols():
            print(column_codes)
    
    def clean_annotations(self) -> List[str]:
        """Cleans the annotations for more readable presentation and returns them as a list of strings."""
        annotation_list = self.annotations['annotation']
        cleaned_annotations = []
        for item in annotation_list:
            text_per_line = f"{item['annotationtitle']}: {item['annotationtext']}"
            cleaned_annotations.append(text_per_line)
        return cleaned_annotations
    
    def table_cols(self) -> List[str]:
        """Cleans and returns the column information for the table in a readable format."""
        columns = self.components['dimension']
        col_descriptions_and_codes = []
        for col in columns:
            text_per_line = f"Column: {col['conceptref']}, column code: {col['codelist']}"
            col_descriptions_and_codes.append(text_per_line)
        return col_descriptions_and_codes
    
    def get_table_cols(self) -> List[Tuple[str, str]]:
        """Returns a list of tuples, where each tuple contains a column code and its corresponding description."""
        columns = self.components['dimension']
        list_of_columns = [(col['codelist'], col['conceptref']) for col in columns]
        return list_of_columns
        
    def table_shorthand(self) -> None:
        """Returns a shorthand description of the table, including its ID and name."""
        print(f"{self.id}: {self.name['value']}")
