import unittest
import sys
import os


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Consensus.LocalMerger import LocalMerger
from Consensus.ConfigManager import ConfigManager
from dotenv import load_dotenv
from pathlib import Path
from os import environ