import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Consensus.EsriServers import TFL
from Consensus.EsriConnector import FeatureServer
from Consensus.utils import where_clause_maker


class TestTFL(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.max_retries = 100

    async def test_1_connection(self) -> None:
        tfl = TFL(max_retries=self.max_retries, retry_delay=2)
        await tfl.initialise()

        tfl.print_all_services()

    async def test_2_build_lookup(self) -> None:
        tfl = TFL(max_retries=self.max_retries, retry_delay=2, matchable_fields_extension=['ROAD_NAME'])
        await tfl.initialise()
        await tfl.build_lookup()
        services = ['Bus_Shelters - Bus Shelters', 'Bus_Stops - Bus Stops']
        metadata = await tfl.metadata_as_pandas(included_services=services)
        print(metadata)

    async def test_3_metadata(self) -> None:
        tfl = TFL(max_retries=self.max_retries, retry_delay=2)
        await tfl.initialise()
        services = ['Bus_Shelters - Bus Shelters', 'Bus_Stops - Bus Stops']
        metadata = await tfl.metadata_as_pandas(included_services=services)
        print(metadata)

    async def test_4_featureserver(self) -> None:
        tfl = TFL(max_retries=self.max_retries, retry_delay=2)
        await tfl.initialise()
        service_name = 'Bus_Shelters - Bus Shelters'

        print(tfl.service_table)

        fs_service_table = tfl.service_table
        fs = FeatureServer()

        column_name = 'ROAD_NAME'
        geographic_areas = ['Havering Road']

        where_clause = where_clause_maker(string_list=geographic_areas, column_name=column_name, service_name=service_name)
        print(where_clause)
        await fs.setup(full_name=service_name, service_table=fs_service_table, max_retries=self.max_retries, retry_delay=2, chunk_size=50)
        output = await fs.download(where_clause=where_clause, return_geometry=False)

        print(output)

    async def test_5_featureserver(self) -> None:
        tfl = TFL(max_retries=self.max_retries, retry_delay=2)
        await tfl.initialise()
        service_name = 'Bus_Stops - Bus Stops'

        print(tfl.service_table)

        fs_service_table = tfl.service_table
        fs = FeatureServer()

        column_name = 'STOP_NAME'
        geographic_areas = ['Hazel Mead', 'Havering Road']

        where_clause = where_clause_maker(string_list=geographic_areas, column_name=column_name, service_name=service_name)
        print(where_clause)
        await fs.setup(full_name=service_name, service_table=fs_service_table, max_retries=self.max_retries, retry_delay=2, chunk_size=50)
        output = await fs.download(where_clause=where_clause, return_geometry=False)

        print(output)

    async def test_6_featureserver(self) -> None:
        tfl = TFL(max_retries=self.max_retries, retry_delay=2)
        await tfl.initialise()

        output = await tfl.metadata_as_pandas()
        print(output)

    async def test_7_featureserver(self) -> None:
        tfl = TFL(max_retries=self.max_retries, retry_delay=2)

        def matching_conditons(field):
            print(field)
            if field['name'].upper() == 'ROAD_NAME':
                return True
            else:
                return False

        tfl.field_matching_condition = matching_conditons

        await tfl.initialise()

        output = await tfl.metadata_as_pandas()
        print(output)


if __name__ == '__main__':
    unittest.main()
