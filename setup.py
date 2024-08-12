# -*- coding: utf-8 -*-
"""
Created on Wed Jan 25 10:44:34 2023

@author: ISipila
"""

import shutil
import os
from setuptools import setup, find_packages, Command

class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        directories_to_remove = ['build', 'dist', 'LBLDataAccess.egg-info']
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

extra_files = package_files('LBLDataAccess/lookups')
config = package_files('LBLDataAccess/config')
all_files = extra_files + config

setup(
    name='LBLDataAccess',
    version='1.0.0',
    author='Ilkka Sipila',
    author_email='ilkka.sipila@lewisham.gov.uk',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'LBLDataAccess': ['lookups/lookup.json', 'config/config.json'],
    },
    install_requires=[
        'requests',
        'pandas',
        'openpyxl',
        'typing', 
        'dataclasses', 
        'geopandas',
        'datetime',
        'more-itertools',
        'numpy==1.26.4'
    ],
    python_requires='>=3.9',  # Specify your supported Python versions
    cmdclass={
        'clean': CleanCommand,
    },
)