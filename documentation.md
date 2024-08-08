# `LBLToNomis` Class Documentation

## Overview
The `LBLToNomis` class provides a Python interface to interact with the NOMIS data API. It allows users to retrieve data from the NOMIS web service, manage API keys, configure proxy settings, and generate URLs for downloading datasets.

## Initialization

### `__init__(api_key: str = None, proxies: Dict[str, str] = None, memorize: bool = False)`
Initializes the `LBLToNomis` object.

#### Parameters:
- **`api_key`** (`str`, optional): The NOMIS API key. If not provided, the class attempts to load it from a configuration file.
- **`proxies`** (`Dict[str, str]`, optional): A dictionary of proxy settings. The dictionary should have keys `'http'` and/or `'https'` with their respective proxy addresses as values.
- **`memorize`** (`bool`, optional): If `True`, the API key and proxy settings are stored in a configuration file for future use.

#### Example:
```python
nomis = LBLToNomis(api_key="your_api_key", proxies={'http': 'http://proxy.example.com:8080'}, memorize=True)
```

## Methods

### Configuration Management

#### `reset_config()`
Deletes the configuration file and clears the stored API key and proxies from the instance.

#### `update_config(api_key: str = None, proxies: Dict[str, str] = None)`
Updates the configuration file with a new API key and/or proxy settings.

#### Parameters:
- **`api_key`** (`str`, optional): The new NOMIS API key to be saved.
- **`proxies`** (`Dict[str, str]`, optional): A dictionary with new proxy settings.

#### Example:
```python
nomis.update_config(api_key="new_api_key", proxies={'https': 'https://proxy.example.com:8080'})
```

### Data Retrieval

#### `bulk_download(dataset: str)`
Generates a URL for bulk downloading a specific dataset.

#### Parameters:
- **`dataset`** (`str`): The dataset identifier for the data you wish to download.

#### Example:
```python
nomis.bulk_download(dataset="NM_1_1")
print(nomis.url)  # Output the generated URL
```

#### `url_creator(dataset: str, qualifiers: Dict[str, List[str]] = None, select_columns: List[str] = None, for_download: bool = False)`
Creates a URL string to query or download data based on specific criteria.

#### Parameters:
- **`dataset`** (`str`): The dataset identifier.
- **`qualifiers`** (`Dict[str, List[str]]`, optional): A dictionary where keys are qualifiers (like 'geography') and values are lists of corresponding codes.
- **`select_columns`** (`List[str]`, optional): A list of columns to select in the data download.
- **`for_download`** (`bool`, optional): If `True`, the URL is tailored for downloading data.

#### Example:
```python
nomis.url_creator(dataset="NM_1_1", qualifiers={'geography': ['E09000023']}, select_columns=['AGE', 'SEX'])
print(nomis.url)  # Output the generated URL
```

#### `connect(url: str = None)`
Connects to the NOMIS API using the generated or provided URL to retrieve data or metadata.

#### Parameters:
- **`url`** (`str`, optional): The URL to use for connecting to the API. If not provided, the URL is generated based on the dataset and other parameters.

#### Example:
```python
nomis.connect()
```

### Data Parsing and Information Retrieval

#### `get_all_tables() -> List[Any]`
Retrieves all available tables from the NOMIS API and returns them as a list of `NomisTable` objects.

#### Returns:
- **`List[Any]`**: A list of `NomisTable` objects containing metadata about available tables.

#### Example:
```python
tables = nomis.get_all_tables()
for table in tables:
    print(table.name)
```

#### `print_table_info()`
Prints basic information about all available tables.

#### Example:
```python
nomis.print_table_info()
```

#### `detailed_info_for_table(table_name: str)`
Prints detailed information for a specific table identified by `table_name`.

#### Parameters:
- **`table_name`** (`str`): The identifier for the table you want detailed information about.

#### Example:
```python
nomis.detailed_info_for_table(table_name="NM_1_1")
```

### Internal Helper Methods

#### `_load_config() -> Dict[str, Any]`
Loads the configuration from the `config/config.json` file.

#### Returns:
- **`Dict[str, Any]`**: A dictionary containing the configuration data.

#### `_write_config_file(api_key: str = None, proxies: Dict[str, str] = None)`
Writes the configuration data (API key and proxies) to the `config/config.json` file.

#### Parameters:
- **`api_key`** (`str`, optional): The API key to save in the configuration file.
- **`proxies`** (`Dict[str, str]`, optional): The proxy settings to save in the configuration file.

#### `_find_exact_table(table_name: str)`
Finds and returns the exact table matching `table_name` from the list of available tables.

#### Parameters:
- **`table_name`** (`str`): The identifier of the table to find.

#### Returns:
- **`NomisTable`**: The table object matching the `table_name`.

#### `_geography_edges(nums: List[int]) -> List[Any]`
Finds the edges in a sorted list of integers, used internally for processing geography codes.

#### Parameters:
- **`nums`** (`List[int]`): A list of integers representing geography codes.

#### Returns:
- **`List[Any]`**: A list of tuples representing the start and end of contiguous ranges in the list.

#### `_create_geography_e_code(val: int) -> str`
Creates a nine-character GSS code (e.g., `Exxxxxxxx`) based on an integer value.

#### Parameters:
- **`val`** (`int`): The integer value to convert to a GSS code.

#### Returns:
- **`str`**: The formatted GSS code.

#### `_unpack_geography_list(geographies: List[str]) -> str`
Unpacks a list of GSS codes, finds the edges, and formats them into a string suitable for a URL.

#### Parameters:
- **`geographies`** (`List[str]`): A list of GSS codes as strings.

#### Returns:
- **`str`**: A formatted string representing the range of geography codes.

## Usage Examples

```python
# Initialize the LBLToNomis object
nomis = LBLToNomis(api_key="your_api_key", memorize=True)

# Create a URL for bulk downloading a dataset
nomis.bulk_download("NM_1_1")
print(nomis.url)

# Generate a URL for specific data retrieval
nomis.url_creator(dataset="NM_1_1", qualifiers={'geography': ['E09000023']}, select_columns=['AGE', 'SEX'])
print(nomis.url)

# Connect to the NOMIS API
nomis.connect()

# Print information about all available tables
nomis.print_table_info()

# Get detailed information for a specific table
nomis.detailed_info_for_table("NM_1_1")
```



---

### `DownloadFromNomis`

`class DownloadFromNomis(LBLToNomis)`

This class provides a wrapper for downloading data from the NOMIS API, offering functionalities to save data directly as CSV files or load it into Pandas DataFrames.

#### Methods

---

#### `__init__(self, *args, **kwargs)`

**Description**:
Initializes the `DownloadFromNomis` class by calling the initializer of the parent class `LBLToNomis`.

**Parameters**:
- `*args`: Positional arguments to be passed to the parent class.
- `**kwargs`: Keyword arguments to be passed to the parent class.

---

#### `table_to_csv(self, dataset: str, qualifiers: Dict[str, List] = None, file_name: str = None, table_columns: List[str] = None, save_location: str = '../nomis_download/', value_or_percent: str = None)`

**Description**:
Downloads a table from the NOMIS API and saves it as a CSV file.

**Parameters**:
- `dataset` (str): The dataset identifier string (e.g., "NM_2021_1").
- `qualifiers` (Dict[str, List], optional): A dictionary of qualifiers for filtering data (e.g., `{'geography': [E00016136], 'age': [0, 2, 3]}`). Defaults to `None`.
- `file_name` (str, optional): The name of the file to save the data. If not provided, a default name will be generated based on the dataset identifier.
- `table_columns` (List[str], optional): List of specific columns to include in the download. Defaults to `None`.
- `save_location` (str, optional): Directory path where the CSV file will be saved. Defaults to `'../nomis_download/'`.
- `value_or_percent` (str, optional): Specify `'value'` to download raw data or `'percent'` to download percentage data. Leave empty to download both. Defaults to `None`.

---

#### `get_bulk(self, dataset: str, data_format: str = 'pandas', save_location: str = '../nomis_download/')`

**Description**:
Downloads bulk data from the NOMIS API, either as a CSV file or a Pandas DataFrame.

**Parameters**:
- `dataset` (str): The dataset identifier string (e.g., "NM_2021_1").
- `data_format` (str, optional): Specifies the format of the downloaded data. Options are `'csv'`, `'download'`, `'pandas'`, or `'df'`. Defaults to `'pandas'`.
- `save_location` (str, optional): Directory path where the CSV file will be saved if `data_format` is `'csv'` or `'download'`. Defaults to `'../nomis_download/'`.

**Returns**:
- `pd.DataFrame`: If `data_format` is `'pandas'` or `'df'`, returns the downloaded data as a Pandas DataFrame. Otherwise, saves the data as a CSV file.

---

#### `table_to_pandas(self, dataset: str, qualifiers: Dict[str, List] = None, table_columns: List[str] = None, value_or_percent: str = None)`

**Description**:
Downloads a table from the NOMIS API and returns it as a Pandas DataFrame.

**Parameters**:
- `dataset` (str): The dataset identifier string (e.g., "NM_2021_1").
- `qualifiers` (Dict[str, List], optional): A dictionary of qualifiers for filtering data (e.g., `{'geography': [E00016136], 'age': [0, 2, 3]}`). Defaults to `None`.
- `table_columns` (List[str], optional): List of specific columns to include in the download. Defaults to `None`.
- `value_or_percent` (str, optional): Specify `'value'` to download raw data or `'percent'` to download percentage data. Leave empty to download both. Defaults to `None`.

**Returns**:
- `pd.DataFrame`: The downloaded data as a Pandas DataFrame.

---

#### `_download_file(self, file_path: Path)`

**Description**:
Helper method to download data from the created URL and save it as a file.

**Parameters**:
- `file_path` (Path): The path to save the downloaded file.

---

#### `_download_to_pandas(self) -> pd.DataFrame`

**Description**:
Helper method to download data from the created URL and return it as a Pandas DataFrame.

**Returns**:
- `pd.DataFrame`: The downloaded data as a Pandas DataFrame.

---

