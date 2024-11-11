"""
API keys and connecting to NOMIS
--------------------------------
Get a NOMIS api key by registering with `NOMIS <https://www.nomisweb.co.uk>`. When initialising the DownloadFromNomis class, provide the api key as a parameter to the
api_key argument. If you need proxies to access the data, provide the information as a dictionary to proxies:

.. code-block:: python

    api_key = '02bdlfsjkd3idk32j3jeaasd2'                                # this is an example of an API key
    proxies = {'http': your_proxy_address, 'https': your_proxy_address}  # proxy dictionary must follow this pattern. If you only have http proxy, copy it to the https without changing it
    nomis = DownloadFromNomis(api_key=api_key, proxies=proxies)
    nomis.connect()

Alternatively, you can use the `ConfigManager` to store API keys:

.. code-block:: python

    dotenv_path = Path('.env')
    load_dotenv(dotenv_path)
    api_key = environ.get("NOMIS_API")
    proxy = environ.get("PROXY")

    conf = ConfigManager()
    conf.save_config({"nomis_api_key": api_key, "proxies.http": proxy, "proxies.https": proxy})


Example usage
-------------

.. code-block:: python

    from Consensus.Nomis import DownloadFromNomis
    from Consensus.ConfigManager import ConfigManager
    from dotenv import load_dotenv
    from pathlib import Path
    from os import environ

    # get your API keys and proxy settings from .env file
    dotenv_path = Path('.env')  # assuming .env file is in your working directory
    load_dotenv(dotenv_path)
    api_key = environ.get("NOMIS_API")  # assuming you've saved the API key to a variable called NOMIS_API
    proxy = environ.get("PROXY") # assuming you've saved the proxy address to a variable called PROXY

    # set up your config.json file - only necessary the first time you use the package
    config = {
              "nomis_api_key": api_key,  # the key for NOMIS must be 'nomis_api_key'
              "proxies.http": proxy,  # you may not need to provide anything for proxy
              "proxies.https": proxy  # the http and https proxies can be different if your setup requires it
              }
    conf = ConfigManager()
    conf.save_config()

    # establish connection
    nomis = DownloadFromNomis()
    nomis.connect()

    # print all tables from NOMIS
    nomis.print_table_info()

    # Get more detailed information about a specific table. Use the string starting with NM_* when selecting a table.
    # In this case, we choose TS054 - Tenure from Census 2021:
    nomis.detailed_info_for_table('NM_2072_1')  #  TS054 - Tenure

    # If you want the data for the whole country:
    df_bulk = nomis.bulk_download('NM_2072_1')
    print(df_bulk)

    # And if you want just an extract for a specific geography, in our case England:
    geography = {'geography': ['E92000001']}  # you can extend this list
    df_england = nomis.download('NM_2072_1', params=geography)
    print(df_england)

"""
from pathlib import Path
from requests import get as request_get
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from shutil import copyfileobj
import pandas as pd
from Consensus.config_utils import load_config


class ConnectToNomis:
    """
    Class to connect and retrieve data from the NOMIS API.

    Attributes:
        api_key (str): Attribute. NOMIS API key.
        proxies (Dict[str, str]): Attribute. HTTP and HTTPS proxy addresses as a dictionary {'http': http_addr, 'https': https_addr}.
        uid (str): Attribute. Unique identifier for API calls using the API key.
        base_url (str): Attribute. Base URL for the NOMIS API.
        url (str): Attribute. Complete URL for API requests.
        r (requests.Response): Attribute. Response object from API requests.
        config (dict): Attribute. Loaded configuration details from `Consensus.config_utils.load_config()`, including API key and proxies.
    """

    def __init__(self, api_key: str = None, proxies: Dict[str, str] = None):
        """
        Initialise ConnectToNomis with API key and proxies.

        Args:
            api_key (str): NOMIS API key. Defaults to None, in which case it loads from the config file.
            proxies (Dict[str, str]): Proxy addresses. Defaults to None, in which case it loads from the config file.

        Raises:
            AssertionError: If no API key is provided or found in the config.
        """
        self.config = load_config()
        self.api_key = api_key or self.config.get('nomis_api_key', '').strip()

        assert self.api_key, "nomis_api_key key not provided or found in config/config.json."

        self.uid = f"?uid={self.api_key}"  # This comes at the end of each API call
        self.base_url = "http://www.nomisweb.co.uk/api/v01/dataset/"
        self.url = None
        self.proxies = proxies or self.config.get('proxies', {})

    def url_creator(self, dataset: str, params: Dict[str, List[str]] = None, select_columns: List[str] = None) -> None:
        """
        Create a URL string for data download from NOMIS.

        Args:
            dataset (str): Name of the dataset to download.
            params (Dict[str, List[str]]): Dictionary of query parameters for filtering data. Defaults to None.
            select_columns (List[str]): List of columns to select in the API response. Defaults to None.

        Raises:
            AssertionError: If values for each key of params are not a list

        Returns:
            None

        """
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

    def connect(self, url: str = None) -> None:
        """
        Connect to the NOMIS API and fetch table structures.

        Args:
            url (str): Custom URL for API connection. Defaults to None.

        Raises:
            KeyError: If proxies are not set and the connection fails without proxies.

        Returns:
            None
        """
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
        """
        Get all available tables from NOMIS.

        Raises:
            AssertionError: If the API connection was not successful.

        Returns:
            List[Any]: List of NOMIS tables.
        """
        assert self.r.status_code == 200, "Connection not successful."
        main_dict = self.r.json()
        tables_data = main_dict['structure']['keyfamilies']['keyfamily']
        return [NomisTable(**table) for table in tables_data]

    def print_table_info(self) -> None:
        """
        Print brief information for all available tables.

        Returns:
            None
        """
        tables = self.get_all_tables()
        for table in tables:
            table.table_shorthand()

    def detailed_info_for_table(self, table_name: str) -> None:
        """
        Print detailed information for a specific table.

        Args:
            table_name (str): Name of the table to get details for.

        Returns:
            None
        """
        table = self._find_exact_table(table_name)
        table.detailed_description()

    def get_table_columns(self, table_name: str) -> List[Tuple[str, str]]:
        """
        Get the columns of a specific table as a list of tuples.

        Args:
            table_name (str): Name of the table to get details for.

        Returns:
            List[Tuple[str, str]]: List of tuples of columns and column codes.
        """
        table = self._find_exact_table(table_name)
        return table.get_table_cols()

    def _find_exact_table(self, table_name: str) -> Any:
        """
        Find and return the matching table for the given name.

        Args:
            table_name (str): Name of the table to search for.

        Returns:
            Any: The matching NOMIS table.
        """
        tables = self.get_all_tables()
        for table in tables:
            if table.id == table_name:
                return table

    def _geography_edges(self, nums: List[int]) -> List[Any]:
        """
        Find edges in a list of integers to create ranges for geography codes.

        Args:
            nums (List[int]): List of geographical codes.

        Returns:
            List[Any]: List of start and end pairs representing ranges.
        """
        nums = sorted(set(nums))
        gaps = [[s, e] for s, e in zip(nums, nums[1:]) if s + 1 < e]
        edges = iter(nums[:1] + sum(gaps, []) + nums[-1:])
        return list(zip(edges, edges))

    def _create_geography_e_code(self, val: int) -> str:
        """
        Create a nine-character GSS code.

        Args:
            val (int): Value for the GSS code.

        Returns:
            str: GSS code in the format 'Exxxxxxxx'.
        """
        return f"E{val:08}"

    def _unpack_geography_list(self, geographies: List[str]) -> str:
        """
        Unpack a list of GSS codes, find edges, and format them for a URL.

        Args:
            geographies (List[str]): List of geographical codes (as GSS codes).

        Returns:
            str: Formatted string for the URL.
        """
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
    """
    Wrapper class for downloading data from the NOMIS API.

    Inherits from ``ConnectToNomis()`` to utilize the NOMIS API for downloading datasets
    as CSV files or Pandas DataFrames.

    Attributes:
        api_key (str): NOMIS API key.
        proxies (Dict[str, str]): HTTP and HTTPS proxy addresses as a dictionary {'http': http_addr, 'https': https_addr}.
        uid (str): Unique identifier for API calls using the API key.
        base_url (str): Base URL for the NOMIS API.
        url (str): Complete URL for API requests.
        r (requests.Response): Response object from API requests.
        config (dict): Loaded configuration details, including API key and proxies.

    Methods:
        __init__(*args, **kwargs): Initializes the ``DownloadFromNomis()`` instance.
        _bulk_download_url(dataset: str): Creates a URL for bulk downloading a dataset.
        _download_checks(dataset: str, params: Dict[str, List], value_or_percent: str, table_columns: List[str]): Prepares the parameters and URL for downloading data.
        table_to_csv(dataset: str, params: Dict[str, List] = None, file_name: str = None, table_columns: List[str] = None, save_location: str = '../nomis_download/', value_or_percent: str = None): Downloads a dataset as a CSV file.
        bulk_download(dataset: str, save_location: str = '../nomis_download/'): Downloads a dataset as a Pandas DataFrame.

    Usage:

        Set up API key and proxies:

        .. code-block:: python

            from Consensus.ConfigManager import ConfigManager
            from Consensus.Nomis import DownloadFromNomis
            from dotenv import load_dotenv
            from pathlib import Path
            from os import environ

            dotenv_path = Path('.env')
            load_dotenv(dotenv_path)
            api_key = environ.get("NOMIS_API")
            proxy = environ.get("PROXY")

            self.conf = ConfigManager()
            self.conf.save_config({"nomis_api_key": api_key,
                                "proxies": {"http": proxy,
                                            "https": proxy}})

        View datasets:

        .. code-block:: python

            nomis = DownloadFromNomis()
            nomis_conn = nomis.connect()
            nomis.print_table_info()

        For bulk downloads:

        .. code-block:: python

            nomis = DownloadFromNomis()
            nomis_conn = nomis.connect()
            nomis.bulk_download('NM_2021_1')

        Downloading specific tables:

        .. code-block:: python

            geography = {'geography': ['E92000001']}
            df = self.conn.download('NM_2072_1', params=geography)
    """

    def __init__(self, *args, **kwargs):
        """
        Initialises the ``DownloadFromNomis()`` instance.

        Args:
            *args: Variable length argument list passed to the parent class.
            **kwargs: Arbitrary keyword arguments passed to the parent class.
        """
        super().__init__(*args, **kwargs)

    def _bulk_download_url(self, dataset: str) -> None:
        """
        Creates a URL for bulk downloading a dataset.

        Args:
            dataset (str): The dataset identifier (e.g., NM_2021_1).

        Returns:
            None
        """
        self.url = f"{self.base_url}{dataset}.bulk.csv{self.uid}"

    def _download_checks(self, dataset: str, params: Dict['str', List], value_or_percent: str, table_columns: List[str]) -> None:
        """
        Prepares the parameters and URL for downloading data.

        Args:
            dataset (str): The dataset identifier (e.g., NM_2021_1).
            params (Dict[str, List]): Dictionary of parameters for the query (e.g., {'geography': ['E00016136']}). Defaults to None.
            value_or_percent (str): Specifies whether to retrieve 'value' or 'percent' data.
            table_columns (List[str]): List of columns to include in the query.

        Returns:
            None
        """
        if params is None:
            params = {'geography': None}

        if value_or_percent == 'percent':
            params['measures'] = ['20301']
        elif value_or_percent == 'value':
            params['measures'] = ['20100']

        self.url_creator(dataset, params, table_columns)

    def table_to_csv(self, dataset: str, params: Dict[str, List] = None, file_name: str = None, table_columns: List[str] = None, save_location: str = '../nomis_download/', value_or_percent: str = None) -> None:
        """
        Downloads a dataset as a CSV file.

        Args:
            dataset (str): The dataset identifier (e.g., NM_2021_1).
            params (Dict[str, List]): Dictionary of parameters (e.g., {'geography': ['E00016136'], 'age': [0, 2, 3]}). Defaults to None.
            file_name (str): Custom name for the saved CSV file. Defaults to None.
            table_columns (List[str]): List of columns to include in the dataset. Defaults to None.
            save_location (str): Directory to save the downloaded CSV file. Defaults to '../nomis_download/'.
            value_or_percent (str): Specifies whether to download 'value' or 'percent'. Defaults to None.

        Returns:
            None
        """
        self._download_checks(dataset, params, value_or_percent, table_columns)

        if file_name is None:
            file_name = f"{dataset}_query.csv"

        save_path = Path(save_location)
        save_path.mkdir(parents=True, exist_ok=True)

        file_name = save_path.joinpath(file_name)
        self._download_file(file_name)

    def bulk_download(self, dataset: str, data_format: str = 'pandas', save_location: str = '../nomis_download/') -> pd.DataFrame:
        """
        Performs a bulk download of a dataset as either CSV or a Pandas DataFrame.

        Args:
            dataset (str): The dataset identifier (e.g., NM_2021_1).
            data_format (str): Format of the downloaded data. Can be 'csv', 'download', 'pandas', or 'df'. Defaults to 'pandas'.
            save_location (str): Directory to save the CSV file if `data_format` is 'csv'. Defaults to '../nomis_download/'.

        Raises:
            AssertionError: If data_format is not in the specified format

        Returns:
            pd.DataFrame: The downloaded data as a Pandas DataFrame if `data_format` is 'pandas'.
        """
        self._bulk_download_url(dataset)
        assert data_format in ['csv', 'download', 'pandas', 'df'], 'Data format must be one of "csv" (or "download") or "pandas" (or "df").'

        if data_format in ['csv', 'download']:
            file_name = f"{dataset}_bulk.csv"
            save_path = Path(save_location)
            save_path.mkdir(parents=True, exist_ok=True)
            file_name = save_path.joinpath(file_name)
            self._download_file(file_name)
        elif data_format in ['pandas', 'df']:
            return self._download_to_pandas()

    def download(self, dataset: str, params: Dict[str, List] = None, table_columns: List[str] = None, value_or_percent: str = None) -> pd.DataFrame:
        """
        Downloads a dataset as a Pandas DataFrame.

        Args:
            dataset (str): The dataset identifier (e.g., NM_2021_1).
            params (Dict[str, List]): Dictionary of parameters (e.g., {'geography': ['E00016136'], 'age': [0, 2, 3]}). Defaults to None.
            table_columns (List[str]): List of columns to include in the dataset. Defaults to None.
            value_or_percent (str): Specifies whether to download 'value' or 'percent'. Defaults to None.

        Returns:
            pd.DataFrame: The downloaded data as a Pandas DataFrame.
        """
        self._download_checks(dataset, params, value_or_percent, table_columns)
        df = self._download_to_pandas()

        if not df.empty:
            return df
        else:
            print('Trying to download the data using the bulk_download() method instead. ')
            print('Filtering to only relevant geographies. Other parameters untouched.')
            df = self.bulk_download(dataset)
            return df[df['geography code'].isin(params['geography'])]

    def _download_file(self, file_path: Path) -> None:
        """
        Downloads a file to the specified path.

        Args:
            file_path (Path): The file path where the downloaded file will be saved.

        Returns:
            None
        """

        try:
            with request_get(self.url, proxies=self.proxies, stream=True) as response:
                with open(file_path, 'wb') as file:
                    copyfileobj(response.raw, file)
        except AttributeError:
            with request_get(self.url, stream=True) as response:
                with open(file_path, 'wb') as file:
                    copyfileobj(response.raw, file)

    def _download_to_pandas(self) -> pd.DataFrame:
        """
        Downloads data directly into a Pandas DataFrame.

        Returns:
            pd.DataFrame: The downloaded data as a Pandas DataFrame.
        """
        try:
            with request_get(self.url, proxies=self.proxies, stream=True) as response:
                return pd.read_csv(response.raw)
        except AttributeError:
            with request_get(self.url, stream=True) as response:
                return pd.read_csv(response.raw)
        except Exception as e:
            print(self.url)
            print(e)
            return pd.DataFrame()


@dataclass
class NomisTable:
    """
    A dataclass representing a structured output from NOMIS.

    This class is designed to encapsulate the metadata and structure of a table retrieved from the NOMIS API.
    It provides methods for accessing detailed descriptions, annotations, and column information in a readable format.

    Attributes:
        agencyid (str): The ID of the agency that owns the table.
        annotations (Dict[str, Any]): A dictionary containing annotations related to the table.
        id (str): The unique identifier of the table.
        components (Dict[str, Any]): A dictionary containing information about the components (columns) of the table.
        name (Dict[str, Any]): A dictionary containing the name of the table.
        uri (str): The URI that links to more information about the table.
        version (str): The version number of the table.
        description (Optional[str]): An optional description of the table.
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
        """
        Prints a detailed and cleaned overview of the table, including its ID, description, annotations, and columns.

        Returns:
            None
        """
        print(f"\nTable ID: {self.id}\n")
        print(f"Table Description: {self.name['value']}\n")
        for table_annotation in self.clean_annotations():
            print(table_annotation)
        print("\n")
        for column_codes in self.table_cols():
            print(column_codes)

    def clean_annotations(self) -> List[str]:
        """
        Cleans the annotations for more readable presentation and returns them as a list of strings.

        Returns:
            List[str]: List of cleaned annotations
        """
        annotation_list = self.annotations['annotation']
        cleaned_annotations = []
        for item in annotation_list:
            text_per_line = f"{item['annotationtitle']}: {item['annotationtext']}"
            cleaned_annotations.append(text_per_line)
        return cleaned_annotations

    def table_cols(self) -> List[str]:
        """
        Cleans and returns the column information for the table in a readable format.

        Returns:
            List[str]: A list of column descriptions as strings
        """
        columns = self.components['dimension']
        col_descriptions_and_codes = []
        for col in columns:
            text_per_line = f"Column: {col['conceptref']}, column code: {col['codelist']}"
            col_descriptions_and_codes.append(text_per_line)
        return col_descriptions_and_codes

    def get_table_cols(self) -> List[Tuple[str, str]]:
        """
        Returns a list of tuples, where each tuple contains a column code and its corresponding description.

        Returns:
            List[Tuple[str, str]]: A list of tuples of columns
        """
        columns = self.components['dimension']
        list_of_columns = [(col['conceptref'], col['codelist']) for col in columns]
        return list_of_columns

    def table_shorthand(self) -> None:
        """Returns a shorthand description of the table, including its ID and name.

        Returns:
            None
        """
        print(f"{self.id}: {self.name['value']}")
