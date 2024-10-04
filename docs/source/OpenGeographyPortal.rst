FeatureServer Class
===================

This class supports downloading data from FeatureServers.

Methods
-------
- **download**: Download the data for the table or layer. Supports SQL commands as part of the `where_clause` argument.

Usage
-----
.. code-block:: python

    service_table = OpenGeography().service_table
    fs = FeatureServer(service_name, service_table)
    dl = fs.download()

Class Definition
----------------
.. code-block:: python

    class FeatureServer():

        def __init__(self, service_name: str = None, service_table: Dict[str, Any] = {}, max_retries: int = 10, timeout: int = 20, chunk_size: int = 50) -> None:
            """
            Initializes the FeatureServer class.

            Parameters:
                service_name (str): The name of the service to connect to.
                service_table (Dict[str, Any]): The service table to use.
                max_retries (int): The maximum number of retries in case of timeouts (default: 10).
                timeout (int): The timeout period for requests (default: 20 seconds).
                chunk_size (int): The number of records to fetch in each chunk (default: 50).
            """
            try:
                self.feature_service = service_table.get(service_name).featureservers()
                self.feature_service.lookup_format()
                self.max_retries = max_retries
                self.timeout = timeout
                self.chunk_size = chunk_size
            except AttributeError as e:
                print(f"{e} - the selected table does not appear to have a feature server. Check table name exists in list of services or your spelling.")

        def looper(self, link_url: str, params: Dict[str,str]) -> Any:
            """
            Handles retries and fetching data for a given URL.

            Parameters:
                link_url (str): The URL to fetch data from.
                params (Dict[str,str]): Parameters for the request.

            Returns:
                Any: JSON response from the server or None if the request fails.
            """
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

        def chunker(self, service_url: str, params: Dict[str,str]):
            """
            Downloads data in chunks from the service URL.

            Parameters:
                service_url (str): The base URL for the service.
                params (Dict[str,str]): Parameters for the query.

            Returns:
                Dict[str, Any]: The full set of downloaded data.
            """
            if self.feature_service.tables:
                links_to_visit = self.feature_service.tables
            elif self.feature_service.layers:
                links_to_visit = self.feature_service.layers
            
            params['resultOffset'] = 0
            params['resultRecordCount'] = self.chunk_size

            link_url = f"{service_url}/{str(links_to_visit[0]['id'])}/query"
            print(f"Visiting link {link_url}")

            responses = self.looper(link_url, params)
            count = self.feature_service._record_count(link_url, params=params)
            print(f"Total records to download: {count}")

            counter = len(responses['features'])
            print(f"Downloaded {counter} out of {count} ({100 * (counter / count):.2f}%) items")

            while counter < int(count):
                params['resultOffset'] += self.chunk_size
                additional_response = self.looper(link_url, params)
                if not additional_response:
                    break

                responses['features'].extend(additional_response['features'])
                counter += len(additional_response['features'])
                print(f"Downloaded {counter} out of {count} ({100 * (counter / count):.2f}%) items")

            return responses

        def download(self, fileformat: str = 'geojson', return_geometry: bool = False, where_clause: str = '1=1', output_fields: str = '*', params: Dict[str,str] = None, n_sample_rows: int = -1) -> Any:
            """
            Download data from the Open Geography Portal.

            Parameters:
                fileformat (str): The format in which to download the data (default: 'geojson').
                return_geometry (bool): Whether the query should return the geometry field.
                where_clause (str): SQL filter to apply to the rows (default: '1=1').
                output_fields (str): Fields to include in the output (default: '*').
                params (Dict[str,str]): Optional custom parameters for the request.
                n_sample_rows (int): For testing, limit the download to the first n rows (default: -1).

            Returns:
                List[Dict[str, Any]]: The downloaded data as a list of dictionaries.
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
                        'resultOffset': 0,
                        'resultRecordCount': self.chunk_size,
                        'returnGeometry': return_geometry,
                        'outFields': output_fields,
                        'f': fileformat
                    }

                try:
                    responses = self.chunker(service_url, params)
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
