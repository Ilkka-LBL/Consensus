# Combining NOMIS data and ONS Geoportal GSS codes
---
### TODO:
The next stage in the development is to create a DuckDB database cache backend that is searched before a query to Open Geography Portal is made and extended with every new call of `FeatureServer` class. Likewise, this database could be made use of to build a local storage of Nomis and other APIs.

### Purpose
The main purpose of this Python package is to allow easier navigation of the NOMIS API and easier collection of GSS geocodes from ONS Open Geography Portal. The GSS geocodes are necessary for selecting the right tables in the NOMIS API, which can otherwise be very difficult to navigate.

This package also includes a class to help with selecting data from LG Inform Plus, if your institution is a subscriber.

### The caveats
The current version of the package relies on access to Open Geography Portal, but their ESRI servers are not always available. The official response from ONS and ESRI was that we can only keep trying, which means that occasionally the download times will take somewhat long. The package automatically retries whenever connection is lost.   

The second caveat is that the output from SmartGeocoder class is not guaranteed to contain the correct tables, but there is built-in capability to choose which tables you want to merge. This requires some knowledge of the data in the tables themselves, however. You may also be more interested in population weighted joins, which this package does not perform (only left joins are supported at the moment). However, the AsyncFeatureServer class does support downloading geometries from Open Geography Portal and NOMIS contains Census 2021 data for demographics, so in theory, you should be able to create your own population weighted joins using just this package.

Note that this package does not create any sort of file caches, so you should implement your own. This is in the todo pile for the package, however.

## Installation
To install this package:

`python -m pip install git+https://github.com/Ilkka-LBL/Consensus.git`

Or 

`python -m pip install Consensus==1.0.0`


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



## Building a lookup table for Open Geography Portal

Building a `lookup.json` file is necessary if you want to make use of the capabilities of this package:

```
from Consensus.AsyncOGP import OpenGeographyLookup
import asyncio

def main():
    ogl = OpenGeographyLookup(max_retries=30)
    asyncio.run(ogl.initialize())
    asyncio.run(ogl.build_lookup(replace_old=True))

if __name__ == "__main__":
    main()
```
or inside Jupyter notebook cells:
```
async def main():
    ogl = OpenGeographyLookup(max_retries=30)
    await ogl.initialize()
    await ogl.build_lookup(replace_old=True)

# and then run the code in a new cell:
await main()
```

## Some examples for using the package
















### Getting help selecting geocodes:
To get help with selecting geocodes, you must first import `GeoHelper` class


```
from Consensus.GeocodeMerger import GeoHelper

geo_help = GeoHelper()
```

`GeoHelper` class has a few helpful options to select the correct GSS codes to use with NOMIS.
First of all, we can check what tables are available:

`all_available_tables = geo_help.files_and_folders`

The result is a JSON-like dictionary output that the user can use to navigate the geocode tables. Call it the 'Advanced mode' if you like and you can use this structure as a guide if you really want to do joins manually. This dictionary is organised like: 

`{year: file_name{'columns': list_of_columns, 'useful_columns': columns_that_end_in_CD}}`

where year is the sub-folder in `lookups` folder, file_name is the .csv or .xlsx file in that sub-folder, `list_of_columns` is a list containing all columns for that table, and `columns_that_end_in_CD` is the subset of all columns in the lookup table consisting of columns that end in 'CD'.

A more user-friendly option over the 'Advanced mode' is to explore the available geographical regions. You can do this by first printing the available 'years' sub-folders, from which you can select the sub-folder that interests you and use it as an input to an additional helper method:

```
years = geo_help.year_options  
for year in years:
    print(geo_help.available_geographies(year=year))
```

If you added a custom folder with your own .csv files and deleted the old JSON file, these will also show up with the above command. If you want the available geographies for all tables, simply write:

`print(geo_help.available_geographies())`

If you need an explanation for any of the codes output by the `available_geographies()` method, you can use 

`print(geo_help.geography_keys())`

which will print describe what the first few letters of the columns stand for. These descriptions aren't in-depth descriptions, but do provide some context. To fully understand what each of these areas are supposed to measure, please refer to ONS' Open Geography Portal.  

Please note that you need to select the starting and the ending columns from the list of available geographies that are printed using the `available_geographies()` method.

## Selecting the geocodes
Now that you have decided what transformation you want, you're ready to use the `SmartGeocodeLookup` class. To import this class:

`from Consensus.load_geocodes import SmartGeocodeLookup`

`SmartGeocodeLookup` class first finds common columns between tables, and then uses graph theory to find the shortest path between all columns, regardless of whether they are in the same or different tables. This class is particularly helpful when the path between columns requires more than one join operation. As the original reason for creating this class was to find the geocodes for local authorities, we also need to provide a list of local authorities. As an example, let's say we want to get the 2022 GSS codes for Lewisham at Ward level, we'd use:

```
gss = SmartGeocodeLookup(end_column_max_value_search=True, local_authority_constraint=True, verbose=True)
# changing end_column_max_value_search to True gives different results from setting it False
gss.run_graph(starting_column='LAD22CD', ending_column='WD22CD', local_authorities=['Lewisham'])
# try changing WD22CD to WD21CD and WD23CD to see how this affects the results

geocodes = gss.get_filtered_geocodes(1)  # the integer input here sets the number of possible routes returned.
print(geocodes[0])

```

This returns a Pandas dataframe containing all Wards for Lewisham as at 2022. Note that Pandas dataframe consists of other columns too, so you may need to apply further filters. If you want to know the path (i.e. list of tables that were joined), use:

`print(gss.shortest_paths)`

As another example, to get 2021 census Output area GSS codes, we'd have to choose output area column for 2021:
  
```
gss.run_graph(starting_column='LAD22CD', ending_column='OA21CD', local_authorities=['Lewisham'])

print(gss.get_filtered_geocodes())
```
Note that we haven't created a new SmartGeocodeLookup object, but rather are just building a new graph based on the data we already have.
---
# Using Geocodes with NOMIS

## Configuring NOMIS
The pre-requisite for using the NOMIS class is that you'll need to register for NOMIS and find your API key (www.nomisweb.co.uk) in settings. When you first use the `DownloadFromNomis` class, you should set the `api_key` and `proxies` arguments. If you want, you can additionally set `memorize=True`, which will save these variables in the `config.json` file in the `config` folder. The proxies argument has to be set as a dictionary `proxies = {'http': your_http_proxy, 'https': your_https_proxy}`. For example:

```
from Consensus.access_nomis import DownloadFromNomis

api_key = 'examplestringthatcouldbeanything'
proxies = {'http': your_http_proxy, 'https': your_https_proxy}

conn = DownloadFromNomis(api_key=api_key, proxies=proxies, memorize=True)
conn.connect()
```

If you need to change the API key and proxies that are stored in the `config.json` file, you can use the `update_config()` method:

```
from Consensus.access_nomis import DownloadFromNomis

api_key = 'example_api_string'
proxies = {'http': your_http_proxy, 'https': your_https_proxy}

conn = DownloadFromNomis(api_key=api_key, proxies=proxies, memorize=True)
conn.connect()

api_key = 'new_api_string'
proxies = {'http': your_new_http_proxy, 'https': your_new_https_proxy}

conn.update_config(api_key=api_key, proxies=proxies)
```

Furthermore, if tracking the proxies and the API key becomes a burden, you can also reset these config settings with the `reset_config()` method, which deletes the `config.json` file in the `config` folder as well as removes the `api_key` and `proxies` class attributes:

```
conn.reset_config()
print(conn.api_key)
```
The above will output an error:

```
AttributeError: 'DownloadFromNomis' object has no attribute 'api_key'
```
If you haven't removed the configurations, you can always print the stored api_key and proxies with:

```
print(conn.api_key, conn.proxies)
```

However, note also that even after calling the `conn.reset_config()` method, you can still use the `conn.connect()` as the API key has been stored as part of the URL call. This also means that you can still download data from NOMIS too. If this is not desired, you should delete the `DownloadFromNomis()` object. 

## Get table info from NOMIS
Once you have the geocodes, you can use them to download census data using the NOMIS API. To do so, you need to import the class for downloading data from NOMIS:

`from Consensus.access_nomis import DownloadFromNomis`

To use this class, you need to create an object and call the `connect()` method:

```
conn = DownloadFromNomis()
conn.connect()
```
Note that here we assume that you have set up your `api_key` and `proxies` previously, saving them with the `memorize` argument.

Now that you have created a connection, you can print a list of all available tables from NOMIS:

`conn.print_table_info()`

Sample of output:
```
NM_1_1 : Records the number of people claiming Jobseeker's Allowance (JSA) and National Insurance credits at Jobcentre Plus local offices. This is not an official measure of unemployment, but is the only indicative statistic available for areas smaller than Local Authorities.
NM_2_1 : A quartery count of claimants who were claiming Jobseeker's Allowance on the count date analysed by their age and the duration.
NM_4_1 : A monthly count of Jobseeker's Allowance (JSA) claimants broken down by age and the duration of claim. Totals exclude non-computerised clerical claims (approx. 1%). Available for areas smaller than Local Authorities.
.
.
.
.
NM_2096_1 : TS031 - Religion (detailed)
NM_2097_1 : TS075 - Multi religion households
NM_2098_1 : TS076 - Welsh language skills (speaking) by single year of age
```

Calling the above method prints two important details for every table (more than 1300 currently) available through the NOMIS API, separated by a colon: 1) the code that you'll use when downloading a table or information therein through the API; and 2) the table name, including a brief description of the data contained. To get more detailed information about a table, take the code string before the colon (e.g. NM_2098_1 for the table TS076 - Welsh language skills (speaking) by single year of age) and use it as input to `detailed_info_for_table()` method:

`conn.detailed_info_for_table(table_name='NM_2097_1')`

This will print a more detailed description of the table:

```
Table id: NM_2097_1

Table description: TS075 - Multi religion households

Status: Current (being actively updated)
Keywords: Religion,Household
Units: Households
contenttype/sources: census_2021_ts
contenttype/geoglevel: oa,msoa,la
SubDescription: All households
Mnemonic: c2021ts075
FirstReleased: 2022-11-29 09:30:00
LastUpdated: 2022-11-29 09:30:00
MetadataTitle0: About this dataset
MetadataText0: This dataset provides Census 2021 estimates that classify households in England and Wales by multi religion households. The estimates are as at Census Day, 21 March 2021.
MetadataTitle1: Protecting personal data
MetadataText1: Sometimes we need to make changes to data if it is possible to identify individuals. This is known as statistical disclosure control. In Census 2021, we:

* Swapped records (targeted record swapping), for example, if a household was likely to be identified in datasets because it has unusual characteristics, we swapped the record with a similar one from a nearby small area. Very unusual households could be swapped with one in a nearby local authority.
* Added small changes to some counts (cell key perturbation), for example, we might change a count of four to a three or a five. This might make small differences between tables depending on how the data are broken down when we applied perturbation.
MetadataCount: 2


Column: GEOGRAPHY, column code: CL_2097_1_GEOGRAPHY
Column: C2021_RELMULT_7, column code: CL_2097_1_C2021_RELMULT_7
Column: MEASURES, column code: CL_2097_1_MEASURES
Column: FREQ, column code: CL_2097_1_FREQ
```


## Download data from NOMIS

The `DownloadFromNomis` class gives you three main downloading methods: `table_to_csv()`, `table_to_pandas()`, and `get_bulk()`. The difference between the first two methods is that the first one saves the downloaded data to a csv file, while `table_to_pandas()` returns a pandas dataframe. The `get_bulk()` method takes an argument to specify whether you want to download the data as a csv or output a pandas dataframe. While the `table_to_csv()` and `table_to_pandas()` methods take six and five arguments, respectively, the `get_bulk()` method takes only three. The reason for this is simple: these methods all take the dataset name as an argument, but `table_to_pandas()` and `table_to_csv()` methods also allow you to provide a dictionary of qualifiers to download just a subset of the data from NOMIS. These two methods also share the ability that you can ask for a specific set of columns to be output, instead of all columns. Likewise, you can also define whether you want the data in counts or as percentages. In contrast, `get_bulk()` only takes the name of the dataset, `data_format` argument used for specifying whether you want a pandas dataframe or a downlaoded csv file, and the `save_location` argument. 

To use `get_bulk()`, you type:

```
from Consensus.access_nomis import DownloadFromNomis

conn = DownloadFromNomis()
conn.connect()

dataset = 'NM_2097_1'
save_location = '../nomis_downloads/'

# to get a pandas dataframe:
bulk_data = conn.get_bulk(dataset=dataset, data_format='df')  # you can write either 'df' or 'pandas' for data_format

# or alternatively, if you want to save the data:
conn.get_bulk(dataset=dataset, data_format='csv', save_location=save_location)  # you can use 'csv' or 'download' for data_format

# the above command will create a file 'NM_2097_1_bulk.csv' in the folder '../nomis_downloads/'
```

To use `table_to_pandas()` to download data for Lewisham:

```
from Consensus.access_nomis import DownloadFromNomis

conn = DownloadFromNomis()
conn.connect()

dataset = 'NM_2097_1'
geographies = ['E09000023']  # E09000023 is the GSS code for Lewisham
 
qualifiers = {'geography': geographies}  # other qualifiers are also possible (e.g. age or sex), but need to be provided as a list of values
table_columns = ['geography_name', 'obs_value']  # optional argument, which limits the columns returned

value_or_percent = 'value'  # this argument is used for selecting either raw values or percentages

df = conn.table_to_pandas(dataset=dataset, qualifiers=qualifiers, table_columns=table_columns, value_or_percent=value_or_percent)
```


To save this information, you can use `table_to_csv()`:
```
from LBLDataAccess.access_nomis import DownloadFromNomis

conn = DownloadFromNomis()
conn.connect()

dataset = 'NM_2097_1'

geographies = ['E09000023']  # E09000023 is the GSS code for Lewisham
qualifiers = {'geography': geographies}  # other qualifiers are also possible (e.g. age or sex), but need to be provided as a list of values
file_name = 'lewisham_multi_religion_household.csv'  # optional argument, defaults to f"{dataset}_query.csv" - must provide .csv extension
table_columns = ['geography_name', 'obs_value']  # optional argument, which limits the columns returned
save_location = '../nomis_downloads/'
value_or_percent = 'value'  # this argument is used for selecting either raw values ('value') or percentages ('percent')

conn.table_to_csv(dataset=dataset, qualifiers=qualifiers, file_name=file_name, table_columns=table_columns, value_or_percent=value_or_percent)

# the above command will create a file 'lewisham_multi_religion_household.csv' in the folder '../nomis_downloads/'
# the downloaded data will include all rows for Lewisham and contain the geography_name and obs_value columns - the values will be the raw
# values.
```


# A full example of intended workflow
Let's go through an example where we want to get data about religion at output area level for Lewisham and Waltham Forest from 2021 Census. From nomisweb.co.uk we can say that we want data from the table TS075 - Multi religion households.

First, we import our classes:
```
from LBLDataAccess.load_geocodes import GeoHelper, SmartGeocodeLookup
from LBLDataAccess.access_nomis import DownloadFromNomis
```
Then we want to have a look at what geographies are available
```
geo_help = GeoHelper()
print(geo_help.available_geographies())  # find what available geocodes there are and choose 'LAD22CD' and 'OA21CD' from this list
```
Output:
```
All available geographies:

['BUA11CD', 'BUA22CD', 'BUASD11CD', 'CAUTH22CD', 'CCG20CD', 'CED21CD', 'CMWD11CD', 'CTRY22CD', 'CTY21CD', 'CTY22CD', 'EER11CD', 'LAD11CD', 'LAD21CD', 'LAD22CD', 'LAU110CD', 'LAU210CD', 'LPA22CD', 'LSOA11CD', 'LSOA21CD', 'LTLA22CD', 'MSOA11CD', 'MSOA21CD', 'NAT22CD', 'NHSER20CD', 'NUTS106CD', 'NUTS206CD', 'NUTS306CD', 'OA11CD', 'OA21CD', 'PCO11CD', 'PCON11CD', 'RGN11CD', 'RGN22CD', 'SHA11CD', 'STP20CD', 'TTWA11CD', 'UTLA22CD', 'WD11CD', 'WD21CD', 'WD22CD', 'WZ11CD']
```

We have now explored the geographies and made our choice, and we can define the local authorities too:
```
start_column = 'LAD22CD'
end_column = 'OA21CD'
local_authorities = ['Lewisham', 'Waltham Forest']  # the input has to be a list and it is case sensitive
```
Let's get the GSS codes:
```
gss = SmartGeocodeLookup(end_column_max_value_search=True, local_authority_constraint=True, verbose=True) 
gss.run_graph(starting_column=start_column, ending_column=end_column, local_authorities=local_authorities) 
oa_geocodes = gss.get_filtered_geocodes(1)
```
Our function helpfully tells us that the data is all contained in one table and fetches that:

```
Reading JSON file json_data.json
['OA21_LSOA21_MSOA21_LAD22_EW_LU.csv', 'OA2021_to_LSOA2021_to_MSOA2021_to_LAD2022_DEC_2021.csv']
Same Node
Same Node
Shortest path is in the same table
Shortest path is in the same table

All possible shortest paths:

Path 1

Path 2
Got UnicodeDecodeError 'utf-8' codec can't decode byte 0xf4 in position 49806: invalid continuation byte for file C:\Users\isipila\OneDrive - Lewisham Council\Documents\Github\LBLDataAccess\LBLDataAccess\lookups\2021\OA21_LSOA21_MSOA21_LAD22_EW_LU.csv - changing encoding to latin-1
```

Above output simply shows that the algorithm identified two equally short paths from the column LAD22CD to column OA21CD. In both cases that path occurs in the same table, but as there are two paths, there are two tables that contain this same information. Indeed, under the line `Reading JSON file json_data.json`, we have a list of the tables being joined, which in our case are simply the individual tables from which the data comes from. Lastly, we ignore the UnicodeDecodeError as it simply refers to a method of opening a file in Pandas. We handle this error by changing the encoding to latin-1, as stated in the message. 

When we print `oa_geocodes[0]`, we get the pandas dataframe:

```
           OA21CD   LSOA21CD             LSOA21NM   MSOA21CD  \
15188   E00016112  E01003195        Lewisham 029C  E02000681   
15189   E00016113  E01003196        Lewisham 029D  E02000681   
15190   E00016114  E01003197        Lewisham 029E  E02000681   
15191   E00016115  E01003189        Lewisham 034A  E02000686   
15192   E00016116  E01003190        Lewisham 034B  E02000686   
...           ...        ...                  ...        ...   
173838  E00185827  E01004327  Waltham Forest 028A  E02000922   
173839  E00185828  E01004430  Waltham Forest 026D  E02000920   
173840  E00185829  E01004424  Waltham Forest 022B  E02000916   
173844  E00185833  E01004382  Waltham Forest 008C  E02000902   
173854  E00185843  E01034485  Waltham Forest 014F  E02000908   

                  MSOA21NM    LAD22CD         LAD22NM LAD22NMW  
15188         Lewisham 029  E09000023        Lewisham      NaN  
15189         Lewisham 029  E09000023        Lewisham      NaN  
15190         Lewisham 029  E09000023        Lewisham      NaN  
15191         Lewisham 034  E09000023        Lewisham      NaN  
15192         Lewisham 034  E09000023        Lewisham      NaN  
...                    ...        ...             ...      ...  
173838  Waltham Forest 028  E09000031  Waltham Forest      NaN  
173839  Waltham Forest 026  E09000031  Waltham Forest      NaN  
173840  Waltham Forest 022  E09000031  Waltham Forest      NaN  
173844  Waltham Forest 008  E09000031  Waltham Forest      NaN  
173854  Waltham Forest 014  E09000031  Waltham Forest      NaN  

[1705 rows x 8 columns]
```

Okay, great, we have the necessary geocodes. Now let's get the NOMIS data as a pandas dataframe too. Before, though, we need to set the API
key and possibly also the proxies:

```
api_key = 'change_me'  # needs to be changed!!
proxies = {'http': 'change_me', 'https': 'change_me'}  # optional, but can be beneficial
```
And let's connect:
```
conn = DownloadFromNomis(api_key=api_key, proxies=proxies, memorize=True)  # setting memorize=True stores your API key and proxies for future use
conn.connect()

conn.print_table_info()
```

This prints the long list of information about the tables contained in NOMIS. We go through the printed text and find that the corresponding
table code for TS075 - Multi religion households, which we now know to be `NM_2097_1`. 

```
dataset = 'NM_2097_1'
geographies = list(oa_geocodes[0]['OA21CD'].unique())
qualifiers = {'geography': geographies}

df = conn.table_to_pandas(dataset=dataset, qualifiers=qualifiers, value_or_percent='value')
print(df)
```

The printed dataframe is:

```
       DATE  DATE_NAME  ...  RECORD_OFFSET RECORD_COUNT
0      2021       2021  ...              0        12888
1      2021       2021  ...              1        12888
2      2021       2021  ...              2        12888
3      2021       2021  ...              3        12888
4      2021       2021  ...              4        12888
    ...        ...  ...            ...          ...
12883  2021       2021  ...          12883        12888
12884  2021       2021  ...          12884        12888
12885  2021       2021  ...          12885        12888
12886  2021       2021  ...          12886        12888
12887  2021       2021  ...          12887        12888

[13640 rows x 28 columns]
```
There are 13,640 rows because unlike when using bulk downloading, the data is presented depth-wise rather than breadth-wise. This means that as there are eight categories for religion, we need to divide 13,640 by 8 to make sure that the output matches the expected number of records, which is the `len(geographies)` or 1705. 

13,640/8 = 1705 so we now that we have downloaded the correct number of records, and the only thing left to do is to wrangle the data into another format, but we won't be showing an example of that here.

## The complete example:

```
from LBLDataAccess.load_geocodes import GeoHelper, SmartGeocodeLookup
from LBLDataAccess.access_nomis import DownloadFromNomis
import pandas as pd

pd.set_option('display.max_columns', None)

geo_help = GeoHelper()
print(geo_help.available_geographies())  # find what available geocodes there are and choose 'LAD22CD' and 'OA21CD' from this list

start_column = 'LAD22CD'
end_column = 'OA21CD'
local_authorities = ['Lewisham', 'Waltham Forest']  # the input has to be a list and it is case sensitive

gss = SmartGeocodeLookup(end_column_max_value_search=True, local_authority_constraint=True, verbose=True) 
gss.run_graph(starting_column=start_column, ending_column=end_column, local_authorities=local_authorities) 
oa_geocodes = gss.get_filtered_geocodes(1)

print(oa_geocodes[0])
api_key = 'change_me'  # needs to be changed!!
proxies = {'http': 'change_me', 'https': 'change_me'}  # optional, but can be beneficial
conn = DownloadFromNomis(api_key=api_key, proxies=proxies, memorize=True)  # setting memorize=True stores your API key and proxies for future use
conn.connect()

conn.print_table_info()


dataset = 'NM_2097_1'
geographies = list(oa_geocodes[0]['OA21CD'].unique())
qualifiers = {'geography': geographies}

df = conn.table_to_pandas(dataset=dataset, qualifiers=qualifiers, value_or_percent='value')

print(df.head(20))
```




