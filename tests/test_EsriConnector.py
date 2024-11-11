import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Consensus.EsriConnector import EsriConnector, FeatureServer
from Consensus.EsriServers import OpenGeography
from Consensus.utils import where_clause_maker


class TestEsriConnector(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.max_retries = 100
        self.full_name = 'Wards_December_2023_Boundaries_UK_BSC - WD_DEC_2023_UK_BSC'
        self.column_name = 'WD23NM'
        self.geographic_areas = ['Brockley']

    def test_1_esri_connector(self) -> None:
        esri = EsriConnector(max_retries=self.max_retries, retry_delay=2)
        assert esri.base_url == ""
        assert esri.services == []
        assert esri.service_table is None

    async def test_2_check_proxies_work(self) -> None:
        og = OpenGeography(max_retries=5, retry_delay=2)
        print(os.environ.get('PROXY'))
        assert og.proxy == os.environ.get('PROXY')
        with self.assertRaises(Exception) as context:
            og.proxy = "make_proxies_fail"
            await og.initialise()
            self.assertTrue('Error during request: make_proxies_fail' in str(context.exception))

    async def test_3_featureserver(self) -> None:
        og = OpenGeography(max_retries=self.max_retries, retry_delay=2)
        await og.initialise()

        fs_service_table = og.service_table
        fs = FeatureServer()
        await fs.setup(full_name=self.full_name, service_table=fs_service_table, max_retries=self.max_retries, retry_delay=2, chunk_size=50)
        where_clause = where_clause_maker(values=self.geographic_areas, column=self.column_name)
        output = await fs.download(where_clause=where_clause, return_geometry=True)
        assert output['WD23NM'].nunique() == 1
        print(output)

    async def test_4_featureserver_layer_number(self) -> None:
        og = OpenGeography(max_retries=self.max_retries, retry_delay=2)
        await og.initialise()

        fs_service_table = og.service_table
        fs = FeatureServer()
        await fs.setup(full_name=self.full_name, service_table=fs_service_table, max_retries=self.max_retries, retry_delay=2, chunk_size=50)
        where_clause = where_clause_maker(values=self.geographic_areas, column=self.column_name)
        output = await fs.download(where_clause=where_clause, return_geometry=True)
        assert output['WD23NM'].nunique() == 1
        print(output)


if __name__ == '__main__':
    unittest.main()
