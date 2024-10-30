import sys
import os
sys_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, sys_path)

import unittest
from Consensus.GeocodeMerger import SmartLinker, GeoHelper


class TestSmartGeocoder(unittest.IsolatedAsyncioTestCase):

    async def test_1_smart_coding(self):
        self.gss = SmartLinker()
        await self.gss.initialise()
        self.gss.allow_geometry()
        self.gss.run_graph(starting_column='WD22CD', ending_column='LAD22CD', geographic_areas=['Lewisham', 'Southwark'], geographic_area_columns=['LAD22NM'])  # the starting and ending columns should end in CD

        codes = await self.gss.geodata(selected_path=9, chunk_size=5)
        print(codes['table_data'][0])
        assert self.gss.fs.chunk_size == 5
        assert codes['table_data'][0]['WD22CD'].nunique() == 42

    def test_2_geo_helper(self):
        geo_help = GeoHelper()
        print(geo_help.available_geographies())
        geo_keys = geo_help.geography_keys()
        print(geo_keys)
        print(geo_help.geographies_filter('WD'))


if __name__ == '__main__':
    unittest.main()
