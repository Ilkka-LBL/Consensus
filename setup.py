# -*- coding: utf-8 -*-
"""
Created on Wed Jan 25 10:44:34 2023

@author: ISipila
"""

import shutil
import os
from setuptools import setup, find_packages, Command

with open('README.md') as f:
    long_description = f.read()


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
all_files = extra_files + config

setup(
    name='Consensus',
    version='1.1.2',
    author='Ilkka Sipila',
    author_email='ilkka.sipila@lewisham.gov.uk',
    url='https://ilkka-lbl.github.io/Consensus/',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'Consensus': ['lookups/lookup.json', 'config/config.json'],
    },
    install_requires=[
        'pandas==1.5.2',
        'openpyxl==3.0.10',
        'geopandas==1.0.1',
        'more-itertools==10.4.0',
        'numpy==1.26.4',
        'aiofiles==24.1.0',
        'aiohttp==3.10.5',
        'aiosignal==1.3.1',
        'alabaster==0.7.16',
        'docutils==0.18.1',
        'm2r2==0.3.2',
        'python-dotenv==1.0.1',
        'PyYAML==6.0',
        'shapely==2.0.5',
        'Sphinx==7.3.7',
        'sphinx-autodoc-typehints==2.3.0',
        'sphinx-rtd-theme==3.0.1',
        'twine==5.1.1',
        'pytest==7.1.2',
        'duckdb==1.1.0'
    ],
    python_requires='>=3.9',  # Specify your supported Python versions
    cmdclass={
        'clean': CleanCommand,
    },
    long_description=long_description,
    long_description_content_type='text/markdown'
)
