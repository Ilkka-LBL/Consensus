import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Consensus.EsriServers import OpenGeography
from Consensus.utils import where_clause_maker
from Consensus.EsriConnector import FeatureServer


class TestOGP(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.max_retries = 100

    def test_1_connection(self) -> None:
        print("\n Test 1 - Connecting to Open_Geography_Portal and printing all available services")
        og = OpenGeography(max_retries=self.max_retries, retry_delay=2)
        og.print_all_services()

    async def test_2_build_lookup(self) -> None:
        print("\n Test 2 - Building lookup table from Open_Geography_Portal. This should fail")
        og = OpenGeography(max_retries=1, retry_delay=2, matchable_fields_extension=['node_dist', 'stop_dist'])
        services = ['Bus_Shelters', 'Bus_Stops']
        with self.assertRaises(Exception) as context:
            await og.build_lookup(included_services=services, replace_old=True)
            self.assertTrue("No valid services found. Are you sure ['Bus_Shelters', 'Bus_Stops'] exist in Open_Geography_Portal?" == str(context.exception))

    async def test_3_build_lookup(self):
        print("\n Test 3 - Building lookup table from Open_Geography_Portal. This should work")
        og = OpenGeography(max_retries=self.max_retries)
        await og.build_lookup(replace_old=True)

    async def test_4_metadata(self):
        print("\n Test 4 - Getting metadata from Open_Geography_Portal")
        og = OpenGeography(max_retries=self.max_retries, retry_delay=2)
        metadata = await og.metadata_as_pandas(included_services=['Wards_December_2023_Boundaries_UK_BSC - WD_DEC_2023_UK_BSC'])
        print(metadata)

    async def test_5_download(self):
        print("\n Test 5 - Downloading data from FeatureServer")
        og = OpenGeography(max_retries=self.max_retries, retry_delay=2)
        service_name = 'WD11_LAD11_WD22_LAD22_EW_LU'
        layers = og.select_layers_by_service(service_name=service_name)
        layer_full_name = layers[0].full_name

        fs = FeatureServer()

        column_name = 'LAD22NM'
        geographic_areas = ['Lewisham']

        where_clause = where_clause_maker(values=geographic_areas, column=column_name)
        print(where_clause)
        await fs.setup(full_name=layer_full_name, esri_server=og._name, max_retries=self.max_retries, retry_delay=2, chunk_size=50)
        output = await fs.download(where_clause=where_clause, return_geometry=False)

        print(output)

    async def test_6_featureserver(self) -> None:
        print("\n Test 6 - Changing the conditions under which fields are matchable by SmartLinker()")
        og = OpenGeography(max_retries=self.max_retries, retry_delay=2)

        def matching_conditons(field):
            print(field)
            if field['type'].upper() == 'ESRIFIELDTYPESTRING' and field['name'].upper() not in ['GLOBALID', 'FID', 'ID', 'OBJECTID']:
                return True
            else:
                return False

        og.field_matching_condition = matching_conditons

        output = await og.metadata_as_pandas()
        print(output)


if __name__ == '__main__':
    unittest.main()
