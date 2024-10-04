import unittest
from LBLDataAccess.GeocodeMerger import SmartGeocoder, GeoHelper
from LBLDataAccess.OpenGeographyPortal import FeatureServer
from LBLDataAccess.Nomis import DownloadFromNomis
from LBLDataAccess.LGInform import LGInform
from LBLDataAccess.ConfigManager import ConfigManager
from LBLDataAccess import lookups
from LBLDataAccess.config_utils import load_config
import json
import pandas as pd
import importlib.resources as pkg_resources



class TestConfigManager(unittest.TestCase):
    def setUp(self) -> None:
        self.conf_dict = {"nomis_api_key":"xxx",
                    "proxies.http": "proxy",
                    "proxies.https": "proxy"}
        
        self.conf = ConfigManager()
        self.conf.default_config = self.conf_dict

    def test_reset(self) -> None:
        loaded_config = load_config()
        self.conf.reset_config()
        reset_config = load_config()
        self.assertEqual(reset_config['nomis_api_key'], "")
        self.assertNotEqual(loaded_config, reset_config)

    def test_update(self) -> None:
        loaded_config = load_config()
        self.conf.update_config(self.conf_dict)
        updated_config = load_config()
        self.assertEqual(updated_config['nomis_api_key'], "xxx")
        self.assertNotEqual(loaded_config, updated_config)


class TestSmartGeocoder(unittest.TestCase):
    def setUp(self) -> None:
        self.sg = SmartGeocoder()

    def test_lookups(self):
        with pkg_resources.open_text(lookups, 'lookup.json') as f:
            lookup_data = json.load(f)
            df = pd.DataFrame(lookup_data)
        self.assertEqual(len(df[df['name']=='Age_16_24_TTWA']), 1)
    
    def test_local_authorities(self):
        
        self.sg.run_graph(starting_column='OA11CD', ending_column='OA21CD', local_authorities=['Lewisham', 'Greenwich'])
        geocodes = self.sg.geocodes(3)
        self.assertEqual(len(geocodes), 3, "Length of returned paths is wrong")

    def test_without_local_authorities(self):
        self.sg.run_graph(starting_column='OA11CD', ending_column='OA21CD')
        geocodes = self.sg.geocodes(3)
        self.assertEqual(len(geocodes), 3, "Length of returned paths is wrong")


if __name__ == '__main__':
    unittest.main()
