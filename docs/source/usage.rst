Usage
=====

.. _installation:

Installation
------------
To use Consensus, first install it using pip directly:

.. code-block:: console

   (.venv) $ pip install Consensus

 
or from Github:

.. code-block:: console

   (.venv) $ python -m pip install git+https://github.com/Ilkka-LBL/Consensus.git


Configuration
-------------
To make full use of this package, you need to do two things: 1) configure your API keys and proxies. To help with this, there is a `ConfigManager` class. And 2) build a lookup file of the tables stored in Open Geography Portal. 


Creating the config.json file
"""""""""""""""""""""""""""""
Note that the modules and classes in Consensus rely on the keys provided in this config file. However, you can extend the `config.json` file with the `update_config()` method to use any other API keys and secrets that you may want. The file is stored as a json file and in Python you can work with nested dictionaries. 

.. code-block:: python

   from Consensus.ConfigManager import ConfigManager

This class has three methods for saving, updating, and resetting the `config.json` file. The `config.json` file resides in the folder `config` inside the package installation folder.

The default `config.json` contents are:

.. code-block:: python

   self.default_config = {
               "nomis_api_key": "",
               "lg_inform_key": "",
               "lg_inform_secret": "",
               "proxies": {
                  "http": "",
                  "https": ""
               }
         }

For the `DownloadFromNomis` class to function, you must provide at least the `nomis_api_key` API key, which you can get by signing up on www.nomisweb.co.uk and heading to your profile settings. 
Likewise, for `LGInform` class to function, you must provide the `lg_inform_key` and `lg_inform_secret`, although your institution must also have signed up to use their platform. 

Minimum configuration example using Nomis:

.. code-block:: python

   from Consensus.ConfigManager import ConfigManager

   config_dict = {"nomis_api_key": "your_new_api_key_value"}

   conf = ConfigManager()
   conf.update_config(config_dict)


If you also want to add proxies:

.. code-block:: python
   
   from Consensus.ConfigManager import ConfigManager

   config_dict = {
                  "nomis_api_key": "your_new_api_key_value", 
                  "proxies.http": "your_proxy",
                  "proxies.https": "your_proxy"
               }

   conf = ConfigManager()
   conf.update_config(config_dict)


Building a lookup table for Open Geography Portal
"""""""""""""""""""""""""""""""""""""""""""""""""
Building a `lookup.json` file is necessary if you want to make use of the capabilities of this package. The `lookup.json` file is used by the `SmartGeocoder` class in `GeocodeMerger` module to search for the quickest path from your starting column to the ending column. 

You can create `lookup.json` (or update it) by running the below snippet:

.. code-block:: python

   from Consensus.AsyncOGP import OpenGeographyLookup
   import asyncio

   def main():
      ogl = OpenGeographyLookup(max_retries=30)
      asyncio.run(ogl.initialize())
      asyncio.run(ogl.build_lookup(replace_old=True))

   if __name__ == "__main__":
      main()

or inside Jupyter notebook cells:

.. code-block:: python

   from Consensus.AsyncOGP import OpenGeographyLookup
   import asyncio

   async def main():
      ogl = OpenGeographyLookup(max_retries=30)
      await ogl.initialize()
      await ogl.build_lookup(replace_old=True)

   # and then run the code in a new cell:
   await main()

Note that Open Geography Portal uses ESRI web servers and they do not always respond to queries. To circumnvent the non-responsiveness, we set `max_retries=30`. On rare occasions, this is not enough and you may have to increase the number of retries. 
Another, related idiosyncrasy with this approach is that the connection may drop during the building of the `lookup.json` file resulting in some, but not all, datasets being left out of the final lookup file. In these cases, the package will report failures, but will not try to rectify it. We may fix this behaviour later.  



