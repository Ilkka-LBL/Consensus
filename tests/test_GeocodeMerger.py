import sys
import os
sys_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, sys_path)

import unittest
from Consensus import SmartLinker, GeoHelper
from Consensus.EsriServers import TFL, OpenGeography
import platform
import asyncio

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class TestSmartGeocoder(unittest.IsolatedAsyncioTestCase):

    async def main():
        retries = 100
        tfl = TFL(max_retries=retries)
        await tfl.build_lookup(replace_old=True)

        ogl = OpenGeography(max_retries=retries)
        await ogl.build_lookup(replace_old=True)

    async def test_1_TFL_lookup(self):
        gss = SmartLinker(server='TFL', max_retries=25, retry_delay=3)
        print(gss.lookup)

    async def test_2_OGP_lookup(self):
        gss = SmartLinker(server='OGP', max_retries=25, retry_delay=3)
        print(gss.lookup)

    async def test_3_smart_coding(self):
        gss = SmartLinker(server='OGP')
        gss.allow_geometry('connected_tables')
        gss.run_graph(starting_columns=['LAD21NM'], ending_columns=['OA21CD'], geographic_areas=['Lewisham'], geographic_area_columns=['LAD21NM'])  # the starting and ending columns should end in CD

    async def test_4_smart_coding(self):
        gss = SmartLinker(server='OGP', max_retries=25)
        gss.allow_geometry()
        gss.run_graph(starting_columns=['WD22CD'], ending_columns=['LAD22CD'], geographic_areas=['Lewisham', 'Southwark'], geographic_area_columns=['LAD22NM'])  # the starting and ending columns should end in CD

        codes = await gss.geodata(selected_path=9, chunk_size=5)
        print(codes['table_data'][0])
        assert gss.fs.chunk_size == 5
        assert codes['table_data'][0]['WD22CD'].nunique() == 42

    async def test_5_smart_coding(self):
        gss = SmartLinker(server='OGP', max_retries=25)
        gss.allow_geometry()
        gss.run_graph(starting_columns=['LAD21CD'], ending_columns=['OA21CD'])  # the starting and ending columns should end in CD

        codes = await gss.geodata(selected_path=0, chunk_size=2500)
        print(codes['table_data'][0])
        print(codes['table_data'][0]['OA21CD'].nunique())
        assert codes['table_data'][0]['OA21CD'].nunique() == 188880

    def test_6_geo_helper(self):
        geo_help = GeoHelper(server='OGP')
        print(geo_help.available_geographies())
        geo_keys = geo_help.geography_keys()
        print(geo_keys)
        print(geo_help.geographies_filter('WD'))

    async def test_7_multiple_start_points(self):
        gss = SmartLinker(server='OGP', max_retries=25)
        gss.allow_geometry()
        gss.run_graph(starting_columns=['WD22CD', 'LSOA21CD'], ending_columns=['LAD22CD'], geographic_areas=['Lewisham', 'Southwark'], geographic_area_columns=['LAD22NM'])  # the starting and ending columns should end in CD

        codes = await gss.geodata(selected_path=0, chunk_size=5)
        print(codes['table_data'][0])
        assert gss.fs.chunk_size == 5
        assert codes['table_data'][0]['WD22CD'].nunique() == 42
        assert codes['table_data'][0]['LSOA21NM'].nunique() == 348


if __name__ == '__main__':
    unittest.main()
