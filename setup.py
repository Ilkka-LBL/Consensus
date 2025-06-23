# -*- coding: utf-8 -*-
"""
Created on Wed Jan 25 10:44:34 2023

@author: ISipila
"""

import shutil
import os
from setuptools import setup, find_packages, Command

try:
    with open('README.md', 'r', encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = ""


class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        directories_to_remove = ['build', 'dist', 'Consensus.egg-info']
        for directory in directories_to_remove:
            if os.path.exists(directory):
                print(f"Removing {directory} directory")
                shutil.rmtree(directory)


def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths


extra_files = package_files('Consensus/lookups')
config = package_files('Consensus/config')
pickles = package_files('Consensus/PickleJar')

all_files = extra_files + config + pickles

setup(
    name='Consensus',
    version='1.2.2',
    author='Ilkka Sipila',
    author_email='ilkka.sipila@lewisham.gov.uk',
    url='https://ilkka-lbl.github.io/Consensus/',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'Consensus': ['lookups/*.json', 'config/config.json', 'PickleJar/*.pickle'],
    },
    install_requires=[
        'pandas>=1.5',
        'openpyxl>=3.0',
        'geopandas>=1.0',
        'more-itertools>=10.4',
        'numpy>=1.26',
        'aiofiles>=24.1',
        'aiohttp>=3.10',
        'aiosignal>=1.3',
        'alabaster>=0.7',
        'docutils>=0.18',
        'm2r2>=0.3',
        'python-dotenv>=1.0',
        'PyYAML>=6.0',
        'shapely>=2.0',
        'Sphinx>=7.3',
        'sphinx-autodoc-typehints>=2.3',
        'sphinx-rtd-theme>=3.0',
        'twine>=5.1',
        'pytest>=7.1',
        'duckdb>=1.1',
        'networkx>=3.2'
    ],
    python_requires='>=3.9',  # Specify your supported Python versions
    cmdclass={
        'clean': CleanCommand,
    },
    long_description=long_description,
    long_description_content_type='text/markdown'
)
