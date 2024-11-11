import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Consensus.ConfigManager import ConfigManager
from Consensus.config_utils import load_config


class TestConfigManager(unittest.TestCase):
    def setUp(self) -> None:
        self.conf_dict = {"nomis_api_key": "xxx",
                          "proxies": {"http": "proxy",
                                      "https": "proxy"}}

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


if __name__ == '__main__':
    unittest.main()
