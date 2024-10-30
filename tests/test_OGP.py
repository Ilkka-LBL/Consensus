import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Consensus.OGP import OpenGeography
from Consensus.utils import where_clause_maker
from Consensus.EsriConnector import FeatureServer
import asyncio


class TestOGP(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.max_retries = 100

    async def test_1_connection(self) -> None:
        ogp = OpenGeography(max_retries=self.max_retries, retry_delay=2)
        await ogp.initialise()

        ogp.print_all_services()

    def test_2_lookup(self):
        def look():
            ogl = OpenGeography(max_retries=self.max_retries)
            asyncio.run(ogl.initialise())
            asyncio.run(ogl.build_lookup(replace_old=True))
        if __name__ == '__main__':
            look()

    async def test_3_metadata(self):
        ogp = OpenGeography(max_retries=self.max_retries, retry_delay=2)
        await ogp.initialise()
        metadata = await ogp.metadata_as_pandas(included_services=['WD11_LAD11_WD22_LAD22_EW_LU'])
        print(metadata)

    async def test_4_download(self):
        ogp = OpenGeography(max_retries=self.max_retries, retry_delay=2)
        await ogp.initialise()
        service_name = 'WD11_LAD11_WD22_LAD22_EW_LU'

        fs_service_table = ogp.service_table
        fs = FeatureServer()

        column_name = 'LAD22NM'
        geographic_areas = ['Lewisham']

        where_clause = where_clause_maker(string_list=geographic_areas, column_name=column_name, service_name=service_name)
        print(where_clause)
        await fs.setup(service_name=service_name, service_table=fs_service_table, max_retries=self.max_retries, retry_delay=2, chunk_size=50)
        output = await fs.download(where_clause=where_clause, return_geometry=False)

        print(output)


if __name__ == '__main__':
    unittest.main()
