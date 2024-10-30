import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Consensus.TFL import TFL
from Consensus.EsriConnector import FeatureServer
from Consensus.utils import where_clause_maker


class TestTFL(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.max_retries = 100

    async def test_1_connection(self) -> None:
        tfl = TFL(max_retries=self.max_retries, retry_delay=2)
        await tfl.initialise()

        tfl.print_all_services()

    async def test_2_metadata(self) -> None:
        tfl = TFL(max_retries=self.max_retries, retry_delay=2)
        await tfl.initialise()
        services = ['Bus_Shelters', 'Bus_Stops']
        metadata = await tfl.metadata_as_pandas(included_services=services)
        print(metadata)

    async def test_3_featureserver(self) -> None:
        tfl = TFL(max_retries=self.max_retries, retry_delay=2)
        await tfl.initialise()
        service_name = 'Bus_Shelters'

        print(tfl.service_table)

        fs_service_table = tfl.service_table
        fs = FeatureServer()

        column_name = 'ROAD_NAME'
        geographic_areas = ['Havering Road']

        where_clause = where_clause_maker(string_list=geographic_areas, column_name=column_name, service_name=service_name)
        print(where_clause)
        await fs.setup(service_name=service_name, service_table=fs_service_table, max_retries=self.max_retries, retry_delay=2, chunk_size=50)
        output = await fs.download(where_clause=where_clause, return_geometry=False)

        print(output)

    async def test_4_featureserver(self) -> None:
        tfl = TFL(max_retries=self.max_retries, retry_delay=2)
        await tfl.initialise()
        service_name = 'Bus_Stops'

        print(tfl.service_table)

        fs_service_table = tfl.service_table
        fs = FeatureServer()

        column_name = 'STOP_NAME'
        geographic_areas = ['Hazel Mead', 'Havering Road']

        where_clause = where_clause_maker(string_list=geographic_areas, column_name=column_name, service_name=service_name)
        print(where_clause)
        await fs.setup(service_name=service_name, service_table=fs_service_table, max_retries=self.max_retries, retry_delay=2, chunk_size=50)
        output = await fs.download(where_clause=where_clause, return_geometry=False)

        print(output)


if __name__ == '__main__':
    unittest.main()
