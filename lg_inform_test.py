import unittest
from Consensus.LGInform import LGInform
from Consensus.ConfigManager import ConfigManager
from Consensus.config_utils import load_config
from dotenv import load_dotenv
from pathlib import Path
from os import environ
import asyncio

class TestConfigManager(unittest.TestCase):
    def setUp(self) -> None:
        # get 
        dotenv_path = Path('.env')
        load_dotenv(dotenv_path)

        proxy = environ.get("PROXY")
        self.lg_key = environ.get("LG_KEY")  # public key to LG Inform Plus
        self.lg_secret = environ.get("LG_SECRET")  # secret to LG Inform Plus
        loaded_config = load_config()
        loaded_config['lg_inform_key'] = self.lg_key
        loaded_config['lg_inform_secret'] = self.lg_secret
        loaded_config['proxies.http'] = proxy
        loaded_config['proxies.https'] = proxy
        print(loaded_config)
        conf = ConfigManager()
        conf.update_config(loaded_config)

        self.datasets = {'IMD_2010': 841, 'IMD_2009': 842, 'Death_of_enterprises': 102}
    
    def test_1_download(self) -> None:

        api_call = LGInform(area='E09000023,Lewisham_CIPFA_Near_Neighbours')
        api_call.download(datasets=self.datasets, output_folder=Path('lg_inform_test_output'), latest_n=20, drop_discontinued=False)  # normal, single threaded download

    """def test_1_download(self) -> None:

        api_call = LGInform(area='E09000023,Lewisham_CIPFA_Near_Neighbours')
        api_call.mp_download(datasets=self.datasets, output_folder=Path('lg_inform_test_output'), latest_n=20, drop_discontinued=False)  # normal, single threaded download"""

if __name__ == '__main__':
    unittest.main()