Changelog
=========

TODO and future improvements
----------------------------
1. Create a DuckDB database cache backend that is searched before a query to Open Geography Portal is made and extended with every new call of ``FeatureServer()`` class. Likewise, this database could be made use of to build a local storage of Nomis and other APIs.
2. Implement geometry search for Open Geography Portal. This is possible to an extent already, but needs refining and proper tests.
3. Add more APIs, for instance ONS, EPC, MetOffice. Easy wins would be to add more ESRI servers as they can be easily plugged in with the ``EsriConnector()`` class (see how it is done with TFL or Open Geography modules, for instance).
4. Improve GeocodeMerger.py by adding the ability to choose additional nodes in the graph so that the graph is guided through these columns.
:strike:5. Clean up code - currently most files fail flake8. I have relaxed the conditions to ignore PEP8:E501 and PEP8:E402
6. Improve documentation.
7. Add more test cases and examples.
8. Switch to using networkx graph as the basis for ``SmartLinker()`` so that it's in line with ``Consensus.LocalMerger.GraphBuilder()``
9. Rework LocalMerger module. It currently isn't fully implemented.

Version 1.1.1
-------------

Added: ``print_object_data()`` to ``EsriConnector()`` class. This method takes the layer as input and prints the full name, service name, layer name, fields within the layer, and the service type.
Improved: Documentation for usage.


Version 1.1.0
-------------

Added: ``select_layers_by_service()`` and ``select_layers_by_layers()`` methods for ``EsriConnector()`` class. These methods should help with selecting the right Esri layer from the maze of services.
Added: ``Layer()`` dataclass. As each ``Service()`` can have multiple layers, ``EsriConnector()`` previously only found the services and ``FeatureServer()`` only downloaded the first layer.
Added: ``field_matching_condition()`` was added to the ``EsriConnector()`` base class, which is then injected into the ``Service()`` dataclass and applied to all fields found in any of the service's ``Layer()`` objects
Added: Ability to define proxies for ``EsriConnector()`` and ``FeatureServer()``.

Improved: More comprehensive testing for ``EsriConnector()``
Improved: Documentation for using ``GeoHelper()``
Improved: Fixed LGInform module's documentation to use Google style.
Improved: ``DownloadFromNomis()`` automatically falls back to using ``bulk_download()`` method if ``download()`` method fails and applies the geography filter.

Changed: Made ``build_lookup()`` method part of the ``EsriConnector()`` class instead of restricting it to Open Geography Portal. Can now create a lookup file for any Esri ArcGIS server. 
Changed: Enabled extending the matchable_fields column when building a lookup table of an Esri server. The old default was that a lookup could be built only for Open Geography Portal. By adding the ability to extend the matchable_fields, the ``SmartLinker()`` class can create custom connections and is therefore usable for Esri ArcGIS servers other than just Open Geography Portal. For Open Geography Portal, it was hard coded that matchable_fields should follow the pattern ``i['name'].upper() for i in self.fields if (i['name'].upper().endswith(tuple(self.matchable_fields_endswith)) and i['name'].upper()[-4:-2].isnumeric())`` (i.e. find all instances where the indices -4-> -2 are numeric and the field name ends with 'CD', 'NM', 'CDH', or 'NMW'). This is now more flexible and the criteria should be defined as part of the module definition.
Changed: Changed how Open Geography Portal decides which field name can be added to the list of matchable_fields for use by ``SmartLinker()`` to a much more complex and comprehensive strategy. The main change is that instead of relying on the name of the field, the ``field_matching_condition()`` method now looks at the field's type and only accepts ``esriFieldTypeStrings``.
Changed: Created ``Consensus.EsriServers`` module that is intended to contain all classes for connecting to Esri ArcGIS REST API servers. This should streamline testing and maintenance of new ``EsriConnector()`` sub-classes.
Changed: ``Consensus.utils.where_clause_maker()`` function now takes just two arguments: values and columns.

Removed: `print_services_by_server_type()` method from `EsriConnector()`. `print_all_services()` should suffice. 
Removed: ``Consensus.OGP`` and ``Consensus.TFL`` modules. These are now found under ``Consensus.EsriServers``
Removed: The ability to choose the layer number in ``FeatureServer().setup()`` method. This was replaced by the argument ``full_name`` (or alternatively you can provide ``service_name`` and ``layer_name`` that are combined into the ``full_name`` argument).

Version 1.0.6
-------------

Bugs: Fixed an issue where the url "https://services1.arcgis.com/YswvgzOodUvqkoCN/ArcGIS/rest/services/Bus_Shelters/FeatureServer/3/query" would not be accessible by the TFL module because ``Service().service_metadata()`` method did not account for the change in the number in this bit of the URL: 'FeatureServer/3/query'. While this was affecting a 'layer' type, it is now fixed so that similar issues should not affect 'table' type objects either.
Bugs: Removed the 'self' argument in the ``where_clause_maker()`` function in the utils module

Improved: Added the ability to choose the layer number in ``FeatureServer().setup()`` method. This is in reference to the bug above and helps with cases where there are multiple layers (e.g. https://services1.arcgis.com/ESMARspQHYMw9BZ9/ArcGIS/rest/services/Pollution_Removal_2007_2011_2015_2030_GeoPackage/FeatureServer). 


Version 1.0.5
-------------

Bugs: Fixed an issue where chunk_size argument in ``GeocodeMerger.SmartLinker()`` was not passed to EsriConnector.FeatureServer object.

Changed: Changed the name of AsyncOGP module to OGP. 
Removed: Removed Open Geography Lookup class and merged its methods with EsriConnector, except for ``build_lookup()`` which is now part of the ``OGP.OpenGeography()`` class.

Improved: Improved documentation throughout. 
Improved: Improved unit tests.