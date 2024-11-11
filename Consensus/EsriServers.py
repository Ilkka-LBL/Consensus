"""
This module contains classes that connect to Esri Servers and download data from them. It is designed to be used in conjunction with the ``Consensus.EsriConnector`` module's ``FeatureServer()`` class.


"""

from Consensus.EsriConnector import EsriConnector
from typing import Dict


class OpenGeography(EsriConnector):
    """
    Open Geography Portal
    ---------------------

    This module provides a class ``OpenGeography()`` that connects to the Open Geography Portal API.

    Running ``OpenGeography().build_lookup()`` is necessary if you want to make use of the ``SmartLinker()`` class from the GeocodeMerger module.

    Usage:
    ------
    This module works in the same way as the ``EsriConnector()`` class, but it is specifically designed for the Open Geography Portal API. It relis on ``build_lookup()`` method that creates a lookup table for the portal's FeatureServers and saves it to a JSON file.

    .. code-block:: python

        from Consensus.EsriServers import OpenGeography
        import asyncio

        async def build_ogp_lookup()
            ogp = OpenGeography()
            await ogp.initialise()
            await ogp.build_lookup()

        asyncio.run(build_ogp_lookup())

    Like with TFL module, you can combine ``OpenGeography()`` with the ``FeatureServer()`` class to download data from the portal's FeatureServers.

    .. code-block:: python

        from Consensus.EsriConnector import FeatureServer
        from Consensus.EsriServers import OpenGeography
        from Consensus.utils import where_clause_maker
        import asyncio

        async def download_test_data():
            og = OpenGeography(max_retries=30, retry_delay=2)
            await og.initialise()

            fs_service_table = og.service_table
            fs = FeatureServer()

            column_name = 'WD23NM'
            geographic_areas = ['Brockley']
            service_name = 'Wards_December_2023_Boundaries_UK_BSC'
            layers = og.select_layers_by_service(service_name=service_name)  # choose the first layer of the 'Wards_December_2023_Boundaries_UK_BSC' service
            layer_full_name = layers[0].full_name  # use the layer's ``full_name`` attribute to select it in ``fs.setup()``

            where_clause = where_clause_maker(values=geographic_areas, column=column_name)  # a helper function that creates the SQL where clause for Esri Servers

            await fs.setup(full_name=layer_full_name, service_table=fs_service_table, max_retries=30, retry_delay=2, chunk_size=50)
            output = await fs.download(where_clause=where_clause, return_geometry=True)
            print(output)

        asyncio.run(download_test_data())

    However, it is perhaps best to rely on the ``SmartLinker()`` class from the GeocodeMerger module for more complex operations.

    """
    def __init__(self, *args, **kwargs) -> None:
        """
        Initialise class.

        Args:
            *args: Arguments for the EsriConnector class.
            **kwargs: Keyword arguments for the EsriConnector class.

        Returns:
            None
        """
        super().__init__(*args, **kwargs)
        self._name = "Open_Geography_Portal"
        self.base_url = "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services?f=json"
        self.pre_built_list_of_extensions = ['PCD', 'PCDS', 'PCD2', 'PCD3', 'PCD4', 'PCD5', 'PCD6', 'PCD7', 'PCD8', 'PCD9']
        # Combine user-provided and built-in matchable fields, ensuring all are uppercase
        self.matchable_fields_extension = list(set(self.matchable_fields_extension + self.pre_built_list_of_extensions))

    async def field_matching_condition(self, field: Dict[str, str]) -> bool:
        """
        Condition for matchable fields. This method is used by ``Service()`` to filter the fields that are added to the matchable_fields columns, which is subsequently used by ``SmartLinker()`` for matching data tables.
        This method is meant to be overwritten by the user if they want to change the condition for matchable fields. Each Esri ArcGIS server will have its own rules, so this will be left for the user to deal with.
        If you are using a built-in server (e.g. TFL or Open Geography Portal), then you don't have to touch this method.

        Args:
            field (Dict[str, str]): The field dictionary. This is the input coming from ``Service()``.

        Returns:
            bool: True if the field ends with 'CD' or 'NM' and the last 4 characters before the end are numeric, or if the field is in the matchable_fields_extension list, False otherwise.
        """
        # matchable_fields_endswith = ['CD', 'NM', 'CDH', 'NMW']
        field_name_upper = field['name'].upper()
        not_in_list = ['BNG_E', 'BNG_N', 'GLOBALID', 'FID', 'LAT', 'LONG', 'OBJECTID', 'ID', 'SHAPE_LENG', 'SHAPE_LENGTH', 'SHAPE__LENGTH', 'SHAPE_AREA', 'SHAPE__AREA', 'WHOLE_PART', 'SD_TYPE', 'LABY', 'LABX', 'LATITUDE', 'LONGITUDE', 'DISTANCE', 'DIST', 'BUA_ID', 'HAS_SD']
        # Check custom endswith condition or if in the combined matchable fields
        return (field['type'].upper() == 'ESRIFIELDTYPESTRING' and field_name_upper not in not_in_list) or (field_name_upper in self.matchable_fields_extension)


class TFL(EsriConnector):
    """
    TFL
    ---

    This module contains the TFL class, which is a subclass of EsriConnector(). It is used to connect to the TfL Open Data Hub and retrieve data.

    Usage:
    ------

    .. code-block:: python

        from Consensus.EsriServers import TFL
        import asyncio

        async def print_all():
            tfl = TFL(max_retries=30, retry_delay=2)
            await tfl.initialise()  # initialise the connection
            tfl.print_all_services()  # a method to help you choose which service you'd like to download data for.

        asyncio.run(print_all())

    The above code will connect to the TfL Open Data Hub and print all available services. You select the service you want to connect to by copying the service name string that comes after "Service name:" in the output.

    Let's say you want to view the bus stops data and explore the metadata:

    .. code-block:: python

        from Consensus.EsriServers import TFL
        import asyncio

        async def minimal():
            tfl = TFL(max_retries=30, retry_delay=2)
            await tfl.initialise()
            metadata = await tfl.metadata_as_pandas(included_services=['Bus_Stops'])
            print(metadata)

        asyncio.run(minimal())

    This will connect to the TfL Open Data Hub and retrieve all available data for Bus_Stops service. From here, you can create a `where` clause to further fine-tune your query:

    .. code-block:: python

        from Consensus.EsriServers import TFL
        from Consensus.utils import where_clause_maker
        import asyncio

        async def download_test_data():
            tfl = TFL(max_retries=30, retry_delay=2)
            await tfl.initialise()

            fs_service_table = tfl.service_table
            fs = FeatureServer()

            service_name = 'Bus_Stops'
            layers = tfl.select_layers_by_service(service_name=service_name)  # choose the first layer of the 'Bus_Stops' service
            layer_full_name = layers[0].full_name  # use the layer's ``full_name`` attribute to select it in ``fs.setup()`` and when creating the ``where_clause``


            column_name = 'STOP_NAME'
            geographic_areas = ['Hazel Mead']
            where_clause = where_clause_maker(values=geographic_areas, column=column_name)  # a helper function that creates the SQL where clause for Esri Servers

            await fs.setup(full_name=layer_full_name, service_table=fs_service_table, max_retries=30, retry_delay=2, chunk_size=50)
            output = await fs.download(where_clause=where_clause, return_geometry=True)
            print(output)

        asyncio.run(download_test_data())
    """

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialise class.

        Args:
            *args: Arguments for the EsriConnector class.
            **kwargs: Keyword arguments for the EsriConnector class.

        Returns:
            None
        """
        super().__init__(*args, **kwargs)
        self._name = "TFL"
        self.base_url = "https://services1.arcgis.com/YswvgzOodUvqkoCN/ArcGIS/rest/services?f=json"

    async def field_matching_condition(self, field: Dict[str, str]) -> bool:
        """
        Condition for matchable fields. This method is used by ``Service()`` to filter the fields that are added to the matchable_fields columns, which is subsequently used by ``SmartLinker()`` for matching data tables.
        This method is meant to be overwritten by the user if they want to change the condition for matchable fields. Each Esri ArcGIS server will have its own rules, so this will be left for the user to deal with.
        If you are using a built-in server (e.g. TFL or Open Geography Portal), then you don't have to touch this method.

        The current implementation for this class will return no columns other than the columns listed in matchable_fields_extension.

        Args:
            field (Dict[str, str]): The field dictionary. This is the input coming from ``Service()``.

        Returns:
            bool: True if the field ends with 'CD' or 'NM' and the last 4 characters before the end are numeric, or if the field is in the matchable_fields_extension list, False otherwise.
        """
        self.matchable_fields_extension = [i.upper() for i in self.matchable_fields_extension]

        self.field_matching_condition = self.field_matching_condition if hasattr(self, 'field_matching_condition') else self.field_matching_condition
        return False or field['name'].upper() in self.matchable_fields_extension
