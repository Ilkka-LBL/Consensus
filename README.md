# A single package for accessing Nomis, Open Geography Portal, TfL Open Data Hub, and more
---
## New name
The package previously known as LBLDataAccess has now been rebranded as Consensus. The package aims to create a single pipeline from Open Geography Portal to Nomis and other UK public data APIs. Currently, there are six modules: 
1. EsriConnector (extendable module to connect to ESRI FeatureServers);
2. EsriServers, which contains two built-in servers that rely on Esri ArcGIS REST API: OpenGeography (Open Geography Portal connector) and TFL (TfL Open Data Hub connector);
3. Nomis (API tool to download data from www.nomisweb.co.uk);
4. GeocodeMerger (a graph theory-based tool that helps with downloading and merging multiple tables from Open Geography Portal);
5. LG Inform Plus API (can only be used if your institution is a subscriber); and
6. LocalMerger (a local version of GeocodeMerger designed to help you with building a DuckDB database from an assortment of local files based on shared column names) - this has not yet been fully implemented.

### TODO and help needed:
1. The next stage in the development is to create a DuckDB database cache backend that is searched before a query to Open Geography Portal is made and extended with every new call of `FeatureServer` class. Likewise, this database could be made use of to build a local storage of Nomis and other APIs.
2. Implement geometry search for Open Geography Portal.
3. Create tests for LocalMerger and improve its functionality.
4. Add more APIs, for instance ONS, EPC, MetOffice. Easy wins would be to add more ESRI servers as they can be easily plugged in with the EsriConnector class (see how it is done with TFL module, for instance).
5. Improve GeocodeMerger.py by adding the ability to choose additional nodes in the graph so that the graph is guided through these columns. 
6. Clean up code. I have relaxed the conditions to ignore PEP8:E501 and PEP8:E402 for flake8.
7. Improve documentation. This will be a forever job.
8. Add more test cases and examples.

### Purpose
The main purpose of this Python package is to allow easier navigation of the NOMIS API and easier collection of GSS geocodes from ONS Open Geography Portal. The GSS geocodes are necessary for selecting the right tables in the NOMIS API, which can otherwise be very difficult to navigate.

This package also includes a class to help with selecting data from LG Inform Plus, if your institution is a subscriber.

### The caveats
The current version of the package relies on access to Open Geography Portal, but their ESRI servers are not always available. The official response from ONS and ESRI was that we can only keep trying, and while the package automatically retries whenever connection is lost, the download times can be at times quite long.   

The second caveat is that the output from SmartLinker class is not guaranteed to contain the correct tables, but there is built-in capability to choose which tables you want to merge. This requires some knowledge of the data in the tables themselves, however. You may also be more interested in population weighted joins, which this package does not perform (only left joins are supported at the moment). However, the FeatureServer class does support downloading geometries from Open Geography Portal and NOMIS contains Census 2021 data for demographics, so in theory, you should be able to create your own population weighted joins using just this package.

Note that this package does not create any sort of file caches, so you should implement your own. This is in the todo pile for the package.

## Installation
To install this package:

`python -m pip install git+https://github.com/Ilkka-LBL/Consensus.git`

Or 

`python -m pip install --upgrade Consensus`

## Configuration
To begin using this package, you need to configure your API keys and proxies. To help with this, there is a `ConfigManager` class:

```
from Consensus.ConfigManager import ConfigManager
```

This class has three methods for saving, updating, and resetting the `config.json` file. The `config.json` file resides in the folder `config` inside the package installation folder.

The default `config.json` file contents are:
```
self.default_config = {
            "nomis_api_key": "",
            "lg_inform_key": "",
            "lg_inform_secret": "",
            "proxies": {
                "http": "",
                "https": ""
            }
        }
```
For the `DownloadFromNomis` class to function, you must provide at least the API key `nomis_api_key`, which you can get by signig up on www.nomisweb.co.uk and heading to your profile settings. 

Minimum example:
```
from Consensus.ConfigManager import ConfigManager

config_dict = {"nomis_api_key": "your_new_api_key_value"}

conf = ConfigManager()
conf.update_config(config_dict)
```

If you also want to add proxies:

```
from Consensus.ConfigManager import ConfigManager

config_dict = {
                "nomis_api_key": "your_new_api_key_value", 
                "proxies.http": "your_proxy",
                "proxies.https": "your_proxy"
              }

conf = ConfigManager()
conf.update_config(config_dict)
```

#### NB! The config.json file requirements
Note that the modules and classes in this package rely on the keys provided in this config file. However, you can extend the `config.json` file with the `.update_config()` method, just remember to pass in the old     


## Building a lookup table for an Esri server

Building a lookup file (e.g. `Open_Geography_Portal_lookup.json`) is very much recommended if you want to make full use of the capabilities of this package:

```
from Consensus.EsriServers import OpenGeography  # could import TFL as well
import asyncio

def main():
    ogl = OpenGeography(max_retries=30)
    asyncio.run(ogl.initialise())
    asyncio.run(ogl.build_lookup(replace_old=True))

if __name__ == "__main__":
    main()
```

or inside Jupyter notebook cells:

```
from Consensus.EsriServers import OpenGeography
async def main():
    ogl = OpenGeography(max_retries=30)
    await ogl.initialise()
    await ogl.build_lookup(replace_old=True)

# and then run the code in a new cell:
await main()
```

