DownloadFromNomis
=================

Overview
--------

The `DownloadFromNomis` class is a Python interface designed for interacting with the NOMIS data API. It allows users to download data in various formats, including CSV files and Pandas DataFrames. This class provides functionality for connecting to the NOMIS API, querying datasets, and retrieving data in a user-friendly format.

**Note:** While `DownloadFromNomis` inherits from the `LBLToNomis` class, users are only intended to interact with the `DownloadFromNomis` class directly.

Initialization
--------------

.. code-block:: python

    DownloadFromNomis(api_key: str = None, proxies: Dict[str, str] = None, memorize: bool = False)

**Parameters:**

- **api_key** (`str`, optional): NOMIS API key. If not provided, the class attempts to load it from a configuration file.
- **proxies** (`Dict[str, str]`, optional): A dictionary of proxy settings, with keys `'http'` and/or `'https'` and their respective proxy addresses as values.
- **memorize** (`bool`, optional): If `True`, the API key and proxy settings are stored in a configuration file for future use.

Methods
-------

Data Download
~~~~~~~~~~~~~

- **table_to_csv**

  .. code-block:: python

      table_to_csv(dataset: str, qualifiers: Dict[str, List] = None, file_name: str = None, table_columns: List[str] = None, save_location: str = '../nomis_download/', value_or_percent: str = None)

  Downloads a table from the NOMIS API and saves it as a CSV file.

  **Parameters:**
  
  - **dataset** (`str`): The dataset identifier string (e.g., `"NM_2021_1"`).
  - **qualifiers** (`Dict[str, List]`, optional): A dictionary of qualifiers for filtering data (e.g., `{'geography': ['E00016136'], 'age': [0, 2, 3]}`).
  - **file_name** (`str`, optional): The name of the file to save the data. If not provided, a default name is generated based on the dataset identifier.
  - **table_columns** (`List[str]`, optional): List of specific columns to include in the download.
  - **save_location** (`str`, optional): Directory path where the CSV file will be saved. Defaults to `'../nomis_download/'`.
  - **value_or_percent** (`str`, optional): Specify `'value'` to download raw data or `'percent'` to download percentage data. Leave empty to download both.

  **Example:**
  
  .. code-block:: python
  
      nomis.table_to_csv(dataset="NM_2021_1", qualifiers={'geography': ['E00016136'], 'age': [0, 2, 3]}, file_name="output.csv")

- **get_bulk**

  .. code-block:: python

      get_bulk(dataset: str, data_format: str = 'pandas', save_location: str = '../nomis_download/')

  Downloads bulk data from the NOMIS API, either as a CSV file or a Pandas DataFrame.

  **Parameters:**
  
  - **dataset** (`str`): The dataset identifier string (e.g., `"NM_2021_1"`).
  - **data_format** (`str`, optional): Specifies the format of the downloaded data. Options are `'csv'`, `'download'`, `'pandas'`, or `'df'`.
  - **save_location** (`str`, optional): Directory path where the CSV file is saved if `data_format` is `'csv'` or `'download'`.

  **Returns:** 
  
  - `pd.DataFrame`: If `data_format` is `'pandas'` or `'df'`, returns the downloaded data as a Pandas DataFrame.

  **Example:**
  
  .. code-block:: python
  
      data = nomis.get_bulk(dataset="NM_2021_1", data_format="pandas")
      print(data.head())

- **table_to_pandas**

  .. code-block:: python

      table_to_pandas(dataset: str, qualifiers: Dict[str, List] = None, table_columns: List[str] = None, value_or_percent: str = None)

  Downloads a table from the NOMIS API and returns it as a Pandas DataFrame.

  **Parameters:**
  
  - **dataset** (`str`): The dataset identifier string (e.g., `"NM_2021_1"`).
  - **qualifiers** (`Dict[str, List]`, optional): A dictionary of qualifiers for filtering data (e.g., `{'geography': ['E00016136'], 'age': [0, 2, 3]}`).
  - **table_columns** (`List[str]`, optional): List of specific columns to include in the download.
  - **value_or_percent** (`str`, optional): Specify `'value'` to download raw data or `'percent'` to download percentage data. Leave empty to download both.

  **Returns:** 
  
  - `pd.DataFrame`: The downloaded data as a Pandas DataFrame.

  **Example:**
  
  .. code-block:: python
  
      df = nomis.table_to_pandas(dataset="NM_2021_1", qualifiers={'geography': ['E00016136'], 'age': [0, 2, 3]})
      print(df.head())

Configuration Management
~~~~~~~~~~~~~~~~~~~~~~~~~

- **reset_config**

  .. code-block:: python

      reset_config()

  Deletes the configuration file and clears the stored API key and proxies from the instance.

  **Example:**
  
  .. code-block:: python
  
      nomis.reset_config()

- **update_config**

  .. code-block:: python

      update_config(api_key: str = None, proxies: Dict[str, str] = None)

  Updates the configuration file with a new API key and/or proxy settings.

  **Parameters:**
  
  - **api_key** (`str`, optional): The new NOMIS API key to save.
  - **proxies** (`Dict[str, str]`, optional): A dictionary with new proxy settings.

  **Example:**
  
  .. code-block:: python
  
      nomis.update_config(api_key="new_api_key", proxies={'https': 'https://proxy.example.com:8080'})
