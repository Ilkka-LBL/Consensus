# -*- coding: utf-8 -*-
"""
Created on Tue Feb  7 09:07:41 2023

@author: ISipila

Problem setting: we want to map the change in the percentage of population with very good health in the census from 2011 to 2022 at ward 
level for Lewisham and surrounding councils

Why this is difficult? 
    - Ward boundaries have changed 
    - Many different councils involved
    - Not all census tables are available at all geographic levels. For instance health data is only available at OA level for 2011 Census

To install LBLDataAccess:
    python -m pip install git+https://github.com/lb-lewisham/LBLDataAccess.git

"""
#%%
from Consensus.GeocodeMerger import GeoHelper, SmartGeocodeLookup
from Consensus.Nomis import DownloadFromNomis
from pathlib import Path
import json 
import pandas as pd
from dotenv import load_dotenv
from os import environ

pd.set_option('display.max_columns', None)

# load NOMIS api key and proxies from settings.txt
dotenv_path = Path('../.env')
load_dotenv(dotenv_path)

proxies = environ.get("PROXY")   # ignore this when using on Google Colab or outside organisational proxy
nomis_api = environ.get("NOMIS_API")

print(proxies)
#%%
# we initialize the SmartGeocodeLookup (but you can of course also create a new object with different parameters)
from Consensus.GeocodeMerger import SmartGeocodeLookup

gss = SmartGeocodeLookup(end_column_max_value_search=True, local_authority_constraint=True, verbose=True)  # changing end_column_max_value_search to True gives different results from setting it False
gss.run_graph(starting_column='WD22CD', ending_column='LSOA21CD', local_authorities=['Lewisham']) # try changing WD22CD to WD21CD and WD23CD to see how this affects the results

geocodes = gss.get_filtered_geocodes(1)  # the integer input here sets the number of possible routes returned.
print(geocodes[0])


#%% We want to have a look at what data we want from NOMIS. We do that by making an api call to nomis and open a connection:
    
conn = DownloadFromNomis(api_key=nomis_api, proxies=proxies, memorize=True)  
# we set the memorize to True so we don't have to always read the settings file when using this class
conn.connect()

#%% Now that we have a connection, let's see what's available to us:
conn.print_table_info()

#%% We can see literally hundreds of tables. In addition to Census data, there's also JSA and other employment data. Some data
# are constantly updated and new tables are added. 

# Okay, but we still need to know what tables we can use. So let's choose a variable, in this case General Health, which is table NM_2055_1
# for 2021 census and NM_1546_1 for 2011 census. We can get more information about them:
    
conn.detailed_info_for_table('NM_2055_1')
conn.detailed_info_for_table('NM_1546_1') 

# So, looking at the Metadata for the two tables, we can already see that neither table has ward level information available, so we have to 
# manually create our ward level data.

#%% We now have the option of downloading the tables as bulk or we can just download the rows for our desired geographic areas. 
# Let's do bulk download first:
    
health_2021_bulk = conn.get_bulk('NM_2055_1')
health_2011_bulk = conn.get_bulk('NM_1546_1')

#%% The problem with the above is that not all tables are available as bulk and these are large files with 100,000+ rows, 
# which means that the download takes a long time:
print(len(health_2021_bulk), len(health_2011_bulk))

# We can now start filtering this bulk data using the geocodes, which we will be doing next.

#%% So, let's be smarter and only download the relevant NOMIS data at OA level for 2011 and 2021 censuses. 
# To do that, we need the appropriate GSS codes. We have two main helper functions that can help us decipher the geocode hell:
    
GeoHelper().geography_keys()  # short hand descriptions of the letters before the years. 

GeoHelper().available_geographies()  # all codes that we can use in our selection

#%% To get the list of folder names that we can use:
print(GeoHelper().year_options) 

#%% And then we pick 2011 to have a look at available geographies:
GeoHelper().available_geographies('2011')

# Using these tools can help you choose your right geocodes, but are not necessary if you know what geographic areas there are.

#%% Once you know the codes you want, and we want OA21CD and OA11CD for downloading data from NOMIS, we can use SmartGeocodeLookup:
las = ['Lewisham', 'Greenwich', 'Bromley', 'Southwark', 'Tower Hamlets']

gss.run_graph(starting_column='OA11CD', ending_column='OA21CD', local_authorities=las) 
oa_geocodes = gss.get_filtered_geocodes(1)  # the integer input here sets the number of possible routes returned.

unique_oas_2021 = oa_geocodes[0][['OA11CD','OA21CD']].drop_duplicates()
print(unique_oas_2021)


#%% However, we also need to get ward level information, so let's instead do
gss = SmartGeocodeLookup(end_column_max_value_search=False, local_authority_constraint=True, verbose=True)
# we have to set the end_column_max_value_search to False (in above examples we've used True) to get our intended result. The path finding algorithm breaks down in this specific case for an unknown reason (please message me if you have an answer so I can fix it).
gss.run_graph(starting_column='WD22CD', ending_column='WD11CD', local_authorities=las)  
ward_geocodes = gss.get_filtered_geocodes(3)




#%% Printing the geocodes, we can see that some columns have a lot of NaN values and that we didn't drop any columns when doing the joins.
print(ward_geocodes[0])

#%%  Let's use these geocodes to download only the appropriate rows from NOMIS:
    
# GOTCHA #1: The following will result in a ParserError because the URL becomes too long, although it works fine on Google Colab 
oa21cd = list(unique_oas_2021['OA21CD'].unique())
print(len(oa21cd))
health_2021_by_oa = conn.table_to_pandas(dataset='NM_2055_1', qualifiers={'geography': oa21cd}, value_or_percent='value') 


#%% Instead of downloading all at once we can break the download by local authority:

tables_to_join_2021 = []    

for la in las:
    la_subset1 = oa_geocodes[0][oa_geocodes[0]['LAD22NM']==la]
        
    oa21cd = list(la_subset1['OA21CD'].unique())          
    lapd = conn.table_to_pandas(dataset='NM_2055_1', qualifiers={'geography': oa21cd}, value_or_percent='value')
    tables_to_join_2021.append(lapd)

#%%
health_2021_by_oa = pd.concat(tables_to_join_2021)

#%% Let's do the same for 2011:

tables_to_join_2011 = []    

for la in las:
    la_subset = oa_geocodes[0][oa_geocodes[0]['LAD22NM']==la]
    oa11cd = list(la_subset['OA11CD'].unique()) 
    
    print(oa11cd)  
    # GOTCHA #4: there may be NAN values mixed in and we need to remove those:
    #oa11cd = [x for x in oa11cd if x == x]
    lapd = conn.table_to_pandas(dataset='NM_1546_1', qualifiers={'geography': oa11cd}, value_or_percent='value')
    tables_to_join_2011.append(lapd)

health_2011_by_oa = pd.concat(tables_to_join_2011)

print(len(health_2011_by_oa))  
#%% Q: why so many rows?  A: each level is given its own row:
print(health_2021_by_oa.head(10)) # C2021_HEALTH_6_NAME column has six levels for each Output Area
print(health_2011_by_oa.head(10)) # C_HEALTH_NAME column has six levels for each Output Area


#%% Now that we have Output Area level for both 2021 and 2011 censuses for our five local authorities, we can start massaging the data 
# into our desired format by pivoting them:
health_2021_pivot = health_2021_by_oa.pivot_table('OBS_VALUE', ['GEOGRAPHY'], 'C2021_HEALTH_6_NAME')
health_2011_pivot = health_2011_by_oa.pivot_table('OBS_VALUE', ['GEOGRAPHY'], 'C_HEALTH_NAME')

print(health_2021_pivot.head(10))
print(health_2011_pivot.head(10))
#%% To map ward level information, we'll first sum the appropriate rows in the pivot tables:

wards_2022 = list(ward_geocodes[0]['WD22NM'].unique())

oa_11_by_ward_22_dict = {'Ward': [], 'WD22CD':[], 'OA11CD': []}
oa_21_by_ward_22_dict = {'Ward': [], 'WD22CD':[],'OA21CD': []}
for ward in wards_2022:
    ward_subset = ward_geocodes[0][ward_geocodes[0]['WD22NM'] == ward]
    ward_subset_2011 = ward_subset.dropna(subset=['OA11CD'])  # Again, need to drop NaN values
    ward_subset_2021 = ward_subset.dropna(subset=['OA21CD'])  # Again, need to drop NaN values
    ward_2022_by_oa11 = list(ward_subset_2011['OA11CD'].unique())
    ward_2022_by_oa21 = list(ward_subset_2021['OA21CD'].unique())
    print(len(ward_2022_by_oa11), len(ward_2022_by_oa21))  # There are different numbers of Output Areas in 2021 and 2011
    oa_11_by_ward_22_dict['Ward'].extend([ward for i in range(len(ward_2022_by_oa11))])
    oa_21_by_ward_22_dict['Ward'].extend([ward for i in range(len(ward_2022_by_oa21))])
    oa_11_by_ward_22_dict['WD22CD'].extend([list(ward_subset['WD22CD'].unique())[0] for i in range(len(ward_2022_by_oa11))])
    oa_21_by_ward_22_dict['WD22CD'].extend([list(ward_subset['WD22CD'].unique())[0] for i in range(len(ward_2022_by_oa21))])
    oa_11_by_ward_22_dict['OA11CD'].extend(ward_2022_by_oa11)
    oa_21_by_ward_22_dict['OA21CD'].extend(ward_2022_by_oa21)

oa_11_by_ward_22_df = pd.DataFrame(data=oa_11_by_ward_22_dict)
oa_21_by_ward_22_df = pd.DataFrame(data=oa_21_by_ward_22_dict)


health_2011_pivot_to_sum = health_2011_pivot.merge(right=oa_11_by_ward_22_df, how='left', right_on='OA11CD', left_on='GEOGRAPHY')
health_2011_summed = health_2011_pivot_to_sum.groupby("WD22CD").sum()

health_2021_pivot_to_sum = health_2021_pivot.merge(right=oa_21_by_ward_22_df, how='left', right_on='OA21CD', left_on='GEOGRAPHY')
health_2021_summed = health_2021_pivot_to_sum.groupby("WD22CD").sum()

print(health_2011_summed.head())
print(health_2021_summed.head())

#%% Get percentages

columns = list(health_2011_summed.columns)
print(columns)
for col in columns:
    true_values = [True for i in range(len(health_2011_summed[f"{col}"]))]
    percentages = (health_2011_summed[f"{col}"]/health_2011_summed['All categories: General health'])*100
    health_2011_summed[f'{col}_percent'] = health_2011_summed[f"{col}"].mask(true_values, percentages)

#%%
columns = list(health_2021_summed.columns)
for col in columns:
    true_values = [True for i in range(len(health_2021_summed[f"{col}"]))]
    percentages = (health_2021_summed[f"{col}"]/health_2021_summed['Total: All usual residents'])*100
    health_2021_summed[f'{col}_percent'] = health_2021_summed[f"{col}"].mask(true_values, percentages)

print(health_2011_summed.head())
print(health_2021_summed.head())

#%% To actually map these values, we'll have to import geopandas and import the ward boundaries, which we then restrict to our 2022 wards

import geopandas as gpd


#%%
all_bounds = gpd.read_file('./Wards_(December_2022)_Boundaries_GB_BFC.geojson')
#%%

wards_codes = list(geocodes['WD22CD'].unique())
ward_bounds = all_bounds[all_bounds['WD22CD'].isin(wards_codes)]
#ward_bounds['geometry'] = [reproject(x) for x in ward_bounds['geometry'].geometry]

#%%
ward_bound_by_2021_health = ward_bounds.merge(health_2021_summed, how='outer', left_on='WD22CD', right_on='WD22CD')
ward_bound_by_2021_health.plot('Very good health_percent', legend=True)

#%%
ward_bound_by_2011_health= ward_bounds.merge(health_2011_summed, how='outer', left_on='WD22CD', right_on='WD22CD')
ward_bound_by_2011_health.plot('Very good health_percent', legend=True)