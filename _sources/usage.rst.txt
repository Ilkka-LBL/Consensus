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
To make full use of this package, you need to do two things: 1) configure your API keys and proxies. To help with this, there is a ``ConfigManager()`` class. And 2) build a lookup file of the tables stored in Open Geography Portal. 


Creating the config.json file
"""""""""""""""""""""""""""""
Note that the modules and classes in Consensus rely on the keys provided in this config file. However, you can extend the ``config.json`` file with the ``update_config()`` method to use any other API keys and secrets that you may want. The file is stored as a json file and in Python you can work with nested dictionaries. 

.. code-block:: python

   from Consensus.ConfigManager import ConfigManager

This class has three methods for saving, updating, and resetting the ``config.json`` file. The ``config.json`` file resides in the folder "Consensus/config" inside the package installation folder.

The default ``config.json`` contents are:

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

For the ``DownloadFromNomis()`` class to function, you must provide at least the "nomis_api_key" API key, which you can get by signing up on www.nomisweb.co.uk and heading to your profile settings. 
Likewise, for ``LGInform()`` class to function, you must provide the "lg_inform_key" and "lg_inform_secret", although your institution must also have signed up to use their platform. 

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
                  "proxies": {'http': "your_proxy", 'https': "your_proxy"}
               }

   conf = ConfigManager()
   conf.update_config(config_dict)


Building a lookup table for Open Geography Portal
"""""""""""""""""""""""""""""""""""""""""""""""""
Building a ``lookup.json`` file is necessary if you want to make full use of the capabilities of this package. The ``lookup.json`` file is used by the class ``Consensus.GeocodeMerger.SmartLinker()`` to search for the quickest path from your starting column to the ending column. However, ``SmartLinker()`` class has a fallback for creating the lookup file if it is not already available. If you instead choose to use ``Consensus.EsriServers.OpenGeography()`` class in combination with ``Consensus.EsriConnector.FeatureServer()`` class to directly access Open Geography Portal you may forgo creating the lookup table, although the package comes with one pre-built and using and updating it is very much recommended. While accessing Open Geography directly gives you more control over what you download, it is also more tedious as you will have to write longer scripts, particularly when accessing several datasets that you want to merge.

You can create ``lookup.json`` (or update it) by running the below snippet:

.. code-block:: python

   from Consensus.EsriServers import OpenGeography
   import asyncio

   def main():
      og = OpenGeography(max_retries=30)
      asyncio.run(og.initialize())
      asyncio.run(og.build_lookup(replace_old=True))

   if __name__ == "__main__":
      main()

or inside Jupyter notebook cells:

.. code-block:: python

   from Consensus.EsriServers import OpenGeography
   import asyncio

   async def main():
      og = OpenGeography(max_retries=30)
      await og.initialize()
      await og.build_lookup(replace_old=True)

   # and then run the code in a new cell:
   await main()

Note that Open Geography Portal uses ESRI web servers and they do not always respond to queries. To circumnvent the non-responsiveness, we set ``max_retries=30``. On rare occasions, this is not enough and you may have to increase the number of retries. 
Another, related idiosyncrasy with this approach is that the connection may drop during the building of the ``lookup.json`` file resulting in some, but not all, datasets being left out of the final lookup file. In these cases, the package will report failures, but will not try to rectify it. We may fix this behaviour later.  


Explore UK geographies
""""""""""""""""""""""

The package contains a ``GeoHelper()`` class that is designed to help you understand UK geographies and select the starting and ending columns when using ``SmartLinker().run_graph()``. 

.. code-block:: python

        from Consensus.GeocodeMerger import GeoHelper

        gh = GeoHelper()
        print(gh.geography_keys())  # outputs a dictionary of explanations for nearly all UK geographic units.
        print(gh.available_geographies())  # outputs all geographies currently available in the lookup file.
        print(gh.geographies_filter('WD'))  # outputs all columns referring to wards.

Please note that the ``geography_keys()`` method does not explain all geographies as explanations were not always available when developing this method.

Example pipeline
----------------
For instance, let's say you've explored the geographies using ``GeoHelper()`` and decided you want to look at 2022 wards. You can do the following:

.. code-block:: python

    async def get_data():
        gss = SmartLinker()
        await gss.initialise()  # order is important - you must run initialise() before anything else.
        gss.allow_geometry('geometry_only')  # use this method to restrict the graph search space to tables with geometry.
        gss.run_graph(starting_column='WD22CD', ending_column='LAD22CD', geographic_areas=['Lewisham', 'Southwark'], geographic_area_columns=['LAD22NM'])  # you can choose the starting and ending columns using ``GeoHelper().geographies_filter()`` method.
        codes = await gss.geodata(selected_path=9, chunk_size=50)  # the selected path is the ninth in the list of potential paths output by ``run_graph()`` method. Increase chunk_size if your download is slow and try decreasing it if you are being throttled (or encounter weird errors).
        print(codes['table_data'][0])  # the output is a dictionary of ``{'path': [[table1_of_path_1, table2_of_path1], [table1_of_path2, table2_of_path2]], 'table_data':[data_for_path1, data_for_path2]}``
        return codes['table_data'][0]
    ward_geos = asyncio.run(get_data())

From here, you can take the WD22CD column from ``output`` and use it as input to the ``Consensus.Nomis.DownloadFromNomis()`` class if you wanted to:

.. code-block:: python

    from Consensus.Nomis import DownloadFromNomis
    from Consensus.ConfigManager import ConfigManager
    from dotenv import load_dotenv
    from pathlib import Path
    from os import environ

    # get your API keys and proxy settings from .env file
    dotenv_path = Path('.env')  # assuming .env file is in your working directory
    load_dotenv(dotenv_path)
    api_key = environ.get("NOMIS_API")  # assuming you've saved the API key to a variable called NOMIS_API
    proxy = environ.get("PROXY") # assuming you've saved the proxy address to a variable called PROXY

    # set up your config.json file - only necessary the first time you use the package
    config = {
              "nomis_api_key": api_key,  # the key for NOMIS must be 'nomis_api_key'
              "proxies.http": proxy,  # you may not need to provide anything for proxy
              "proxies.https": proxy  # the http and https proxies can be different if your setup requires it
              }
    conf = ConfigManager()
    conf.save_config()

    # establish connection
    nomis = DownloadFromNomis()
    nomis.connect()

    # print all tables from NOMIS
    nomis.print_table_info()

    # Get more detailed information about a specific table. Use the string starting with NM_* when selecting a table.
    # In this case, we choose TS054 - Tenure from Census 2021:
    nomis.detailed_info_for_table('NM_2072_1')  #  TS054 - Tenure

    # If you want the data for all geographies:
    df_bulk = nomis.bulk_download('NM_2072_1')
    print(df_bulk)

    # And if you want just an extract for a specific geography, in our case all wards in Lewisham and Southwark:
    geography = {'geography': list(ward_geos['WD22CD'].unique())}  # you can extend this list
    df_lewisham_and_southwark_wards = nomis.download('NM_2072_1', params=geography)  # note that this method falls back to using bulk_download() if it fails for some reason and then applies the geography filter.
    print(df_lewisham_and_southwark_wards)

Now you have both the geopandas GeoDataFrame() of the wards and the TS054 - Tenure data for the wards and you're free to create maps and graphs as you like. 