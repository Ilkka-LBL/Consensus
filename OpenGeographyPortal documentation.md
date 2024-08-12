Note that the below documentation was created using ChatGPT 4.o and may therefore not be entirely accurate. Please report any mistakes. 

---
# FeatureServer Documentation

---

## Class: `FeatureServer`

The `FeatureServer` class is designed to interact with the Open Geography Portal's FeatureServers, allowing users to download and manage geospatial data from these servers.

---

### Inheritance:
`FeatureServer` inherits from the `OpenGeography` class.

---

### Constructor: `__init__(self, service_name: str = None) -> None`

- **Purpose**: Initializes a `FeatureServer` instance.
  
- **Parameters**:
  - `service_name` (str): The name of the service you want to interact with.
  
- **Exceptions**:
  - `AttributeError`: Raised if the provided `service_name` does not correspond to a valid FeatureServer in the service table.

- **Usage**:
  ```python
  fs = FeatureServer("SomeServiceName")
  ```

---

### Method: `download(self, fileformat: str = 'geojson', return_geometry: bool = False, where_clause: str = '1=1', output_fields: str = '*', params: Dict[str, str] = None, visit_all_links: bool = False, n_sample_rows: int = -1) -> Any`

- **Purpose**: Downloads data from the Open Geography Portal FeatureServer in the specified format.

- **Parameters**:
  - `fileformat` (str): The format in which to download the data. Default is 'geojson'. Other supported formats might include 'csv', 'shapefile', etc.
  - `return_geometry` (bool): If `True`, the geometry field will be included in the download. Default is `False`.
  - `where_clause` (str): SQL-like filter for rows. Default is '1=1', which selects all rows.
  - `output_fields` (str): Fields to include in the output. Default is '*', meaning all fields.
  - `params` (Dict[str, str]): Dictionary of additional parameters for the request.
  - `visit_all_links` (bool): If `True`, it will traverse all pagination links to retrieve all data. Default is `False`.
  - `n_sample_rows` (int): If provided, limits the number of rows to download. Default is `-1`, meaning all rows.
  
- **Returns**:
  - Data in the specified format, such as a GeoJSON object, a CSV, or a DataFrame.

- **Usage**:
  ```python
  fs = FeatureServer("SomeServiceName")
  data = fs.download(fileformat='csv', where_clause="POPULATION > 10000")
  ```

---

# `OpenGeography` Class Documentation

## Class: `OpenGeography`

The `OpenGeography` class provides methods to connect to the Open Geography API and manage the various services available through it.

---

### Constructor: `__init__(self) -> None`

- **Purpose**: Initializes the connection to the Open Geography Portal and loads all available services.
  
- **Usage**:
  ```python
  og = OpenGeography()
  ```

---

### Method: `print_all_services(self) -> None`

- **Purpose**: Prints the name, URL, and server type of all services available through the Open Geography Portal.

- **Usage**:
  ```python
  og.print_all_services()
  ```

---

### Method: `print_services_by_server_type(self, server_type: str = 'feature') -> None`

- **Purpose**: Prints services available for a given server type.

- **Parameters**:
  - `server_type` (str): The type of server to filter by. Should be one of 'feature', 'map', or 'wfs'. Default is 'feature'.

- **Usage**:
  ```python
  og.print_services_by_server_type('map')
  ```

---

# `Service` Class Documentation

## Class: `Service`

The `Service` class represents a service available through the Open Geography Portal.

---

### Attributes:

- `name` (str): Name of the service.
- `type` (str): Type of service, such as 'FeatureServer', 'MapServer', 'WFSServer'.
- `url` (str): URL of the service.
- `description` (str): Description of the service.
- `layers` (List[Dict[str, Any]]): Data layers available through the service.
- `tables` (List[Dict[str, Any]]): Tables available through the service.
- `output_formats` (List[str]): List of formats available for the data.
- `metadata` (json): Metadata as JSON.
- `fields` (List[str]): List of fields for the data.
- `primary_key` (str): Primary key for the data.

---

### Method: `featureservers(self) -> 'Service'`

- **Purpose**: Returns the service if it is a FeatureServer.

---

### Method: `mapservers(self) -> 'Service'`

- **Purpose**: Returns the service if it is a MapServer.

---

### Method: `wfsservers(self) -> 'Service'`

- **Purpose**: Returns the service if it is a WFSServer.

---

### Method: `service_details(self) -> Any`

- **Purpose**: Returns high-level details for the data as JSON.

---

### Method: `service_metadata(self) -> Any`

- **Purpose**: Returns metadata as JSON.

---

### Method: `lookup_format(self) -> Dict`

- **Purpose**: Returns a dictionary of the service's metadata suitable for creating a Pandas DataFrame.

---

# `OpenGeographyLookup` Class Documentation

## Class: `OpenGeographyLookup`

Inherits from `OpenGeography` and provides additional methods to build, update, and manage a lookup table for the Open Geography Portal's FeatureServers.

---

### Method: `metadata_as_pandas(self, service_type: str = 'feature', included_services: List[str] = []) -> pd.DataFrame`

- **Purpose**: Creates a Pandas DataFrame from selected tables.

---

### Method: `build_lookup(self, parent_path: Path = Path(__file__).resolve().parent, included_services: List[str] = [], replace_old: bool = True) -> pd.DataFrame`

- **Purpose**: Builds a lookup table from scratch and saves it to the specified path.

---

### Method: `update_lookup(self, parent_path: Path = Path(__file__).resolve().parent, service_type: str = 'feature', full_check: bool = True) -> pd.DataFrame`

- **Purpose**: Updates the lookup table with new or updated services.

---
