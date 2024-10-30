import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Consensus.EsriConnector import EsriConnector, FeatureServer
from Consensus.OGP import OpenGeography
from Consensus.utils import where_clause_maker


class TestEsriConnector(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.max_retries = 100

    async def test_1_esri_connector(self) -> None:
        esri = EsriConnector(max_retries=self.max_retries, retry_delay=2)
        assert esri.base_url == ""
        assert esri.services == []
        assert esri.service_table is None

    async def test_2_featureserver(self) -> None:
        og = OpenGeography(max_retries=self.max_retries, retry_delay=2)
        await og.initialise()

        fs_service_table = og.service_table
        fs = FeatureServer()
        service_name = 'Wards_December_2023_Boundaries_UK_BSC'
        await fs.setup(service_name=service_name, service_table=fs_service_table, max_retries=self.max_retries, retry_delay=2, chunk_size=50)
        column_name = 'WD23NM'
        geographic_areas = ['Brockley']
        where_clause = where_clause_maker(string_list=geographic_areas, column_name=column_name, service_name=service_name)
        output = await fs.download(where_clause=where_clause, return_geometry=True)
        assert output['WD23NM'].nunique() == 1
        print(output)

    async def test_3_featureserver_layer_number(self) -> None:
        og = OpenGeography(max_retries=self.max_retries, retry_delay=2)
        await og.initialise()

        fs_service_table = og.service_table
        fs = FeatureServer()
        service_name = 'Wards_December_2023_Boundaries_UK_BSC'
        await fs.setup(service_name=service_name, service_table=fs_service_table, max_retries=self.max_retries, retry_delay=2, chunk_size=50, layer_number=1)
        column_name = 'WD23NM'
        geographic_areas = ['Brockley']
        where_clause = where_clause_maker(string_list=geographic_areas, column_name=column_name, service_name=service_name)
        output = await fs.download(where_clause=where_clause, return_geometry=True)
        assert output['WD23NM'].nunique() == 1
        print(output)


if __name__ == '__main__':
    unittest.main()
