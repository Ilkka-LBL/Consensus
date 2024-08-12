Note that the below documentation was created using ChatGPT 4.o and may therefore not be entirely accurate. Please report any mistakes. 

---

### `SmartGeocoder` Class

The `SmartGeocoder` class is designed to find the shortest path between two table columns using graph theory, specifically the Breadth-First Search (BFS) algorithm. The goal is to determine the shortest connection between data tables based on shared column names, with optional filtering by local authorities.

#### **Initialization**

```python
SmartGeocoder(end_column_max_value_search: bool = False, verbose: bool = False, lookup_location: Path = None, geometry_only: bool = False)
```

- **Parameters:**
  - `end_column_max_value_search` (bool, default: `False`): If `True`, restricts the search to tables with the maximum number of unique values.
  - `verbose` (bool, default: `False`): If `True`, provides detailed output during the execution of methods.
  - `lookup_location` (Path, optional): Path to the folder containing the `lookup.json` file.
  - `geometry_only` (bool, default: `False`): If `True`, filters the lookup table to include only entries with geometry data.

#### **Methods**

- **`run_graph(starting_column: str, ending_column: str, local_authorities: List[str] = None)`**
  - Constructs the graph and finds the shortest path between the starting and ending columns.
  - **Parameters:**
    - `starting_column` (str): The name of the starting column.
    - `ending_column` (str): The name of the ending column.
    - `local_authorities` (List[str], optional): A list of local authorities to filter the data by.

- **`geocodes(n_first_routes: int = 3) -> Dict[str, List]`**
  - Returns geocodes based on the shortest paths found by `run_graph()`.
  - **Parameters:**
    - `n_first_routes` (int, default: 3): The number of possible routes to return.
  - **Returns:** 
    - A dictionary containing the shortest paths and corresponding geocodes.

- **`read_lookup(lookup_folder: Path = None) -> pd.DataFrame`**
  - Reads the lookup table from a `lookup.json` file.
  - **Parameters:**
    - `lookup_folder` (Path, optional): Path to the folder containing the `lookup.json` file.
  - **Returns:** 
    - A pandas DataFrame containing the lookup data.

- **`create_graph() -> Tuple[Dict, List]`**
  - Creates a graph of connections between tables based on common column names.
  - **Returns:** 
    - A tuple containing the graph and a list of table-column pairs.

- **`get_starting_point_without_local_authority_constraint() -> Dict`**
  - Identifies starting points in the graph without local authority constraints.
  - **Returns:** 
    - A dictionary of starting points.

- **`get_starting_point() -> Dict`**
  - Identifies starting points in the graph with local authority constraints.
  - **Returns:** 
    - A dictionary of starting points.

- **`find_paths() -> Dict[str, List]`**
  - Finds all possible paths between the starting and ending columns using the BFS algorithm.
  - **Returns:** 
    - A dictionary containing all possible paths.

- **`find_shortest_paths() -> List[str]`**
  - Selects the shortest paths from the paths found by `find_paths()`.
  - **Returns:** 
    - A list of the shortest paths.

#### **Usage Example**

```python
gss = SmartGeocoder(end_column_max_value_search=False)
gss.run_graph(starting_column='LAD23CD', ending_column='OA21CD', local_authorities=['Lewisham', 'Southwark'])
codes = gss.geocodes(3)
```

---

### `GeoHelper` Class

The `GeoHelper` class is a subclass of `SmartGeocoder` that provides additional tools for working with geographic keys and geographies. It inherits all the methods of `SmartGeocoder` and adds some additional utility functions.

#### **Initialization**

```python
GeoHelper()
```

- Inherits all parameters from the `SmartGeocoder` class.

#### **Methods**

- **`geography_keys() -> Dict[str, str]`**
  - Provides a dictionary of shorthand descriptions for common geographic areas.
  - **Returns:** 
    - A dictionary where the keys are geographic abbreviations and the values are their full descriptions.

- **`available_geographies()`**
  - Lists all available geographies in the lookup data.
  - **Returns:** 
    - A list or dictionary of available geographic codes.

#### **Usage Example**

```python
geo_helper = GeoHelper()
geo_keys = geo_helper.geography_keys()
available_geos = geo_helper.available_geographies()
```

