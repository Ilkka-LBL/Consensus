Changelog
---------

TODO
====
1. Improved documentation
2. Example use cases
3. Better tests


Version 1.0.6
=============

Bugs: Fixed an issue where the url "https://services1.arcgis.com/YswvgzOodUvqkoCN/ArcGIS/rest/services/Bus_Shelters/FeatureServer/3/query" would not be accessible by the TFL module because Service dataclass' service_metadata() method did not account for the change in the number in this bit of the URL: 'FeatureServer/3/query'. While this was affecting a 'layer' type, it is now fixed so that similar issues should not affect 'table' type objects either.
Bugs: Removed the 'self' argument in the where_clause_maker() function in the utils module

Improved: Added the ability to choose the layer number in FeatureServer() class' setup() method. This is in reference to the bug above and helps with cases where there are multiple layers (e.g. https://services1.arcgis.com/ESMARspQHYMw9BZ9/ArcGIS/rest/services/Pollution_Removal_2007_2011_2015_2030_GeoPackage/FeatureServer). 


Version 1.0.5
=============

Bugs: Fixed an issue where chunk_size argument in GeocodeMerger.SmartLinker was not passed to EsriConnector.FeatureServer object.

Changed: Changed the name of AsyncOGP module to OGP. 
Removed: Removed Open Geography Lookup class and merged its methods with EsriConnector, except for build_lookup() which is now part of the OGP.OpenGeography class.

Improved: Improved documentation throughout. 
Improved: Improved unit tests.