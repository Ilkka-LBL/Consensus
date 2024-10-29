Changelog
---------


Version 1.0.5
=============

Bugs: Fixed an issue where chunk_size argument in GeocodeMerger.SmartLinker was not passed to EsriConnector.FeatureServer object.

Changed: Changed the name of AsyncOGP module to OGP. 
Removed: Removed Open Geography Lookup class and merged its methods with EsriConnector, except for build_lookup() which is now part of the OGP.OpenGeography class.

Improved: Improved documentation throughout. 
Improved: Improved unit tests.