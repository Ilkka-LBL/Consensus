LGInform
=========

Note that the below documentation was created using ChatGPT 4.o and may therefore not be entirely accurate. Please report any mistakes. 



Overview
--------

The `LGInform` class provides access to data from the LG Inform API, which offers various datasets related to local authorities. This class facilitates querying and retrieving data from the API, including handling parameters and managing requests.

Initialization
--------------

.. code-block:: python

    LGInform(api_key: str = None, base_url: str = 'https://api.lginform.local.gov.uk/', timeout: int = 10)

**Parameters:**

- **api_key** (`str`, optional): API key for authentication with the LG Inform API. If not provided, the class attempts to load it from a configuration file.
- **base_url** (`str`, default: `'https://api.lginform.local.gov.uk/'`): Base URL for the LG Inform API.
- **timeout** (`int`, default: `10`): Timeout for API requests, in seconds.

Methods
-------

Data Retrieval
~~~~~~~~~~~~~

- **get_data**

  .. code-block:: python

      get_data(endpoint: str, params: Dict[str, str] = None) -> Dict[str, Any]

  Retrieves data from a specified endpoint of the LG Inform API.

  **Parameters:**
  
  - **endpoint** (`str`): The API endpoint to query (e.g., `"/data"`).
  - **params** (`Dict[str, str]`, optional): Additional query parameters for the API request.

  **Returns:**
  
  - A dictionary containing the data retrieved from the API.

  **Example:**
  
  .. code-block:: python
  
      lgi = LGInform(api_key="your_api_key")
      data = lgi.get_data("/data", params={"filter": "value"})
      print(data)

Configuration Management
~~~~~~~~~~~~~~~~~~~~~~~~~

- **load_config**

  .. code-block:: python

      load_config(config_file: str)

  Loads API key and other configuration settings from a specified file.

  **Parameters:**
  
  - **config_file** (`str`): Path to the configuration file.

  **Example:**
  
  .. code-block:: python
  
      lgi.load_config("config.json")

- **save_config**

  .. code-block:: python

      save_config(config_file: str)

  Saves the current API key and configuration settings to a specified file.

  **Parameters:**
  
  - **config_file** (`str`): Path to the configuration file.

  **Example:**
  
  .. code-block:: python
  
      lgi.save_config("config.json")
