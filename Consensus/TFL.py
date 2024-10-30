"""

This module contains the TFL class, which is a subclass of EsriConnector.
It is used to connect to the TfL Open Data Hub and retrieve data.

Usage:
------

.. code-block:: python

    from Consensus.TFL import TFL
    tfl = TFL(max_retries=30, retry_delay=2)
    await tfl.initialise()  # initialise the connection
    tfl.print_all_services()  # a method to help you choose which service you'd like to download data for.

The above code will connect to the TfL Open Data Hub and print all available services. You select the service you want to connect to by copying the service name string that comes after "Service name:" in the output.

Let's say you want to view the bus stops data and explore the metadata:

.. code-block:: python

    from Consensus.TFL import TFL
    tfl = TFL(max_retries=30, retry_delay=2)
    await tfl.initialise()
    metadata = await tfl.metadata_as_pandas(included_services=['Bus_Stops'])
    print(metadata)

This will connect to the TfL Open Data Hub and retrieve all available data for Bus_Stops service. From here, you can create a `where` clause to further fine-tune your query:

.. code-block:: python

    from Consensus.TFL import TFL
    from Consensus.utils import where_clause_maker

    tfl = TFL(max_retries=30, retry_delay=2)
    await tfl.initialise()

    fs_service_table = tfl.service_table
    fs = FeatureServer()

    service_name = 'Bus_Stops'
    column_name = 'STOP_NAME'
    geographic_areas = ['Hazel Mead']
    where_clause = where_clause_maker(string_list=geographic_areas, column_name=column_name, service_name=service_name)  # a helper function that creates the SQL where clause for Esri Servers

    await fs.setup(service_name='service_name', service_table=fs_service_table, max_retries=30, retry_delay=2, chunk_size=50)
    output = await fs.download(where_clause=where_clause, return_geometry=True)
    print(output)
"""


from Consensus.EsriConnector import EsriConnector


class TFL(EsriConnector):
    """
    Uses EsriConnector class to connect to TfL Open Data Hub.
    """
    def __init__(self, max_retries: int = 10, retry_delay: int = 2) -> None:
        """
        Initialise class.

        Returns:
            None

        :meta private:
        """
        super().__init__(max_retries, retry_delay)
        self.base_url = "https://services1.arcgis.com/YswvgzOodUvqkoCN/ArcGIS/rest/services?f=json"
        print("Connecting to TfL Open Data Hub")
