import unittest
from LBLDataAccess.Nomis import DownloadFromNomis
from LBLDataAccess.ConfigManager import ConfigManager
from dotenv import load_dotenv
from pathlib import Path
from os import environ


class TestNomis(unittest.TestCase):
    def setUp(self) -> None:
        # get 
        dotenv_path = Path('.env')
        load_dotenv(dotenv_path)
        api_key = environ.get("NOMIS_API")
        proxy = environ.get("PROXY")

        self.conf = ConfigManager()
        self.conf.save_config({"nomis_api_key": api_key, "proxies.http": proxy, "proxies.https": proxy})
        
        self.conn = DownloadFromNomis()

    def test_1_connection(self) -> None:        
        self.conn.connect()

    def test_2_table_info(self) -> None:
        self.conn.connect()
        self.conn.print_table_info()
    
    def test_3_table_info_details(self) -> None:
        self.conn.connect()
        self.conn.detailed_info_for_table('NM_2072_1')  #  TS054 - Tenure

    def test_4_bulk_download(self) -> None:
        self.conn.connect()
        df = self.conn.bulk_download('NM_2072_1')
        print(df)
        self.assertEqual(df.shape, (240516, 33))

    def test_5_download(self) -> None:
        self.conn.connect()
        geography = {'geography': ['E92000001']}
        df = self.conn.download('NM_2072_1', params=geography)
        print(df)
        self.assertEqual(df.shape, (30, 28))

if __name__ == '__main__':
    unittest.main()
