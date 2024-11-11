
import sys
import os
sys_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, sys_path)

from Consensus.ConfigManager import ConfigManager
from Consensus.GeocodeMerger import SmartLinker, GeoHelper
from Consensus.Nomis import DownloadFromNomis

import unittest
import platform
import asyncio

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


from dotenv import load_dotenv
from pathlib import Path
from os import environ
import asyncio


class TestNomis(unittest.TestCase):
    def setUp(self) -> None:
        dotenv_path = Path('.env')
        load_dotenv(dotenv_path)
        api_key = environ.get("NOMIS_API")
        proxy = environ.get("PROXY")

        self.conf = ConfigManager()
        self.conf.save_config({"nomis_api_key": api_key,
                               "proxies": {"http": proxy,
                                           "https": proxy}})

    def test_download(self):
        async def get_data():
            gss = SmartLinker()
            await gss.initialise()
            gss.allow_geometry('geometry_only')  # use this method to restrict the graph search space to tables with geometry

            gss.run_graph(starting_column='WD22CD', ending_column='LAD22CD', geographic_areas=['Lewisham', 'Southwark'], geographic_area_columns=['LAD22NM'])  # you can choose the starting and ending columns using ``GeoHelper().geographies_filter()`` method.
            codes = await gss.geodata(selected_path=0, chunk_size=50)  # the selected path is the ninth in the list of potential paths output by ``run_graph()`` method. Increase chunk_size if your download is slow and try decreasing it if you are being throttled (or encounter weird errors).
            print(codes['table_data'][0])  # the output is a dictionary of ``{'path': [[table1_of_path_1, table2_of_path1], [table1_of_path2, table2_of_path2]], 'table_data':[data_for_path1, data_for_path2]}``
            return codes['table_data'][0]
        output = asyncio.run(get_data())

        # establish connection
        nomis = DownloadFromNomis()
        nomis.connect()

        # print all tables from NOMIS
        nomis.print_table_info()

        # Get more detailed information about a specific table. Use the string starting with NM_* when selecting a table.
        # In this case, we choose TS054 - Tenure from Census 2021:
        nomis.detailed_info_for_table('NM_2072_1')  # TS054 - Tenure

        # If you want the data for the whole country:
        #df_bulk = nomis.bulk_download('NM_2072_1')
        #print(df_bulk)

        # And if you want just an extract for a specific geography, in our case all wards in Lewisham and Southwark:
        geography = {'geography': list(output['WD22CD'].unique())}  # you can extend this list
        df_lewisham_and_southwark_wards = nomis.download('NM_2072_1', params=geography)
        print(df_lewisham_and_southwark_wards)


if __name__ == '__main__':
    unittest.main()
