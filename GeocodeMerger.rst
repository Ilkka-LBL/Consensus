SmartGeocoder
=============

Overview
--------

The `SmartGeocoder` class is designed to find the shortest path between two table columns using graph theory, specifically the Breadth-First Search (BFS) algorithm. It determines the shortest connection between data tables based on shared column names, with optional filtering by local authorities.

Initialization
--------------

.. code-block:: python

    SmartGeocoder(end_column_max_value_search: bool = False, verbose: bool = False, lookup_location: Path = None, geometry_only: bool = False)

**Parameters:**

- **end_column_max_value_search** (`bool`, default: `False`): Restricts the search to tables with the maximum number of unique values.
- **verbose** (`bool`, default: `False`): Provides detailed output during the execution of methods.
- **lookup_location** (`Path`, optional): Path to the folder containing the `lookup.json` file.
- **geometry_only** (`bool`, default: `False`): Filters the lookup table to include only entries with geometry data.

Methods
-------

Graph Operations
~~~~~~~~~~~~~~~~

- **run_graph**

  .. code-block:: python

      run_graph(starting_column: str, ending_column: str, local_authorities: List[str] = None)

  Constructs the graph and finds the shortest path between the starting and ending columns.

  **Parameters:**
  
  - **starting_column** (`str`): The name of the starting column.
  - **ending_column** (`str`): The name of the ending column.
  - **local_authorities** (`List[str]`, optional): A list of local authorities to filter the data by.

Geocoding
~~~~~~~~~

- **geocodes**

  .. code-block:: python

      geocodes(n_first_routes: int = 3) -> Dict[str, List]

  Returns geocodes based on the shortest paths found by `run_graph()`.

  **Parameters:**

  - **n_first_routes** (`int`, default: `3`): The number of possible routes to return.

  **Returns:** 
  
  - A dictionary containing the shortest paths and corresponding geocodes.

Example
-------

.. code-block:: python

    gss = SmartGeocoder(end_column_max_value_search=False)
    gss.run_graph(starting_column='LAD23CD', ending_column='OA21CD', local_authorities=['Lewisham', 'Southwark'])
    codes = gss.geocodes(3)



GeoHelper
=========

Overview
--------

The `GeoHelper` class is a subclass of `SmartGeocoder` that provides additional tools for working with geographic keys and geographies. It inherits all the methods of `SmartGeocoder` and adds some additional utility functions.

Initialization
--------------

.. code-block:: python

    GeoHelper()

Inherits all parameters from the `SmartGeocoder` class.

Methods
-------

Geography Utilities
~~~~~~~~~~~~~~~~~~~

- **geography_keys**

  .. code-block:: python

      geography_keys() -> Dict[str, str]

  Provides a dictionary of shorthand descriptions for common geographic areas.

  **Returns:** 
  
  - A dictionary where the keys are geographic abbreviations and the values are their full descriptions.

- **available_geographies**

  .. code-block:: python

      available_geographies()

  Lists all available geographies in the lookup data.

  **Returns:** 
  
  - A list or dictionary of available geographic codes.

Example
-------

.. code-block:: python

    geo_helper = GeoHelper()
    geo_keys = geo_helper.geography_keys()
    available_geos = geo_helper.available_geographies()
