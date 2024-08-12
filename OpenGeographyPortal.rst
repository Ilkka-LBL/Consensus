FeatureServer
=============

Overview
--------

The `FeatureServer` class is designed to interact with the Open Geography Portal's FeatureServers, allowing users to download and manage geospatial data from these servers.

Inheritance
-----------

`FeatureServer` inherits from the `OpenGeography` class.

Initialization
--------------

.. code-block:: python

    FeatureServer(service_name: str = None)

**Parameters:**

- **service_name** (`str`): The name of the service you want to interact with.

**Exceptions:**

- **AttributeError**: Raised if the provided `service_name` does not correspond to a valid FeatureServer in the service table.

Methods
-------

Data Download
~~~~~~~~~~~~~

- **download**

  .. code-block:: python

      download(fileformat: str = 'geojson', return_geometry: bool = False, where_clause: str = '1=1', output_fields: str = '*', params: Dict[str, str] = None, visit_all_links: bool = False, n_sample_rows: int = -1) -> Any

  Downloads data from the Open Geography Portal FeatureServer in the specified format.

  **Parameters:**
  
  - **fileformat** (`str`): The format in which to download the data. Default is `'geojson'`.
  - **return_geometry** (`bool`): If `True`, the geometry field will be included in the download. Default is `False`.
  - **where_clause** (`str`): SQL-like filter for rows. Default is `'1=1'`, which selects all rows.
  - **output_fields** (`str`): Fields to include in the output. Default is `'*'`, meaning all fields.
  - **params** (`Dict[str, str]`, optional): Dictionary of additional parameters for the request.
  - **visit_all_links** (`bool`): If `True`, it will traverse all pagination links to retrieve all data. Default is `False`.
  - **n_sample_rows** (`int`): Limits the number of rows to download. Default is `-1`, meaning all rows.

  **Returns:** 
  
  - Data in the specified format, such as a GeoJSON object, a CSV, or a DataFrame.

Example
-------

.. code-block:: python

    fs = FeatureServer("SomeServiceName")
    data = fs.download(fileformat='csv', where_clause="POPULATION > 10000")
