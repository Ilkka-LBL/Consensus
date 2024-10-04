#%%
from LBLDataAccess.GeocodeMerger import SmartGeocoder
from LBLDataAccess.Nomis import DownloadFromNomis
from LBLDataAccess.OpenGeographyPortal import OpenGeography
import os
import asyncio

sg = SmartGeocoder(max_retries=100, retry_delay=5)

with open(".env", 'r') as e:
    line = e.readline().split("NOMIS_API=")[1]

    os.environ['NOMIS'] = line
"""
for key in sg.fs_service_table.keys():
    try:
        print(key, sg.fs_service_table.get(key).featureservers().lookup_format()['fields'])
    except AttributeError:
        continue


london = ['City of London','Tower Hamlets', 'Hackney', 'Kensington and Chelsea', 'Southwark', 'Bexley', 'Redbridge', 'Croydon', 'Ealing', 
          'Harrow', 'Hillingdon', 'Haringey', 'Hounslow', 'Barnet', 'Camden', 'Enfield', 'Richmond upon Thames', 'Hammersmith and Fulham', 
          'Islington', 'Lewisham', 'Westminster', 'Waltham Forest', 'Brent', 'Merton', 'Sutton', 'Bromley', 'Barking and Dagenham', 
          'Greenwich', 'Kingston upon Thames', 'Lambeth', 'Havering', 'Newham', 'Wandsworth']

proxies = {'http': 'http://LBLSquidProxy.lblmain.lewisham.gov.uk:8080', 'https': 'http://LBLSquidProxy.lblmain.lewisham.gov.uk:8080'}

#%%
nomis = DownloadFromNomis(api_key = os.environ['NOMIS'], proxies=proxies)
nomis.connect()
nomis.print_table_info()

#%%
sg.run_graph(starting_column='OA11CD', ending_column='OA21CD', local_authorities=london)
codes = sg.geocodes(1)
print(codes)

#%%
oa = codes['table_data'][0]['OA21CD'].unique()

oa
#%%
dl = nomis.get_bulk('NM_2401_1')

#%%
dl

#%%
local_authorities = ['Lewisham', 'Greenwich', 'Southwark']
final_table_col = 'LAD22NM'
string_list = [f'{i}' for i in local_authorities]
where_clause = f"{final_table_col} IN {str(tuple(string_list))}"
print(where_clause)


#%%






# %%
sg.run_graph(starting_column='OA11CD', ending_column='MSOA21CD', local_authorities=london)
codes = sg.geocodes(1)
print(codes)

#%%
msoa = codes['table_data'][0]['MSOA21CD'].unique()

#%%
DownloadFromNomis()

#%%
print(codes['table_data'][0]['LAD22NM'].unique())

# %%
sg.run_graph(starting_column='LAD23CD', ending_column='MSOA21CD', local_authorities=['Lewisham', 'Greenwich'])
codes = sg.geocodes(1)
print(codes)

# %%
codes['table_data'][0]['LAD23NM'].unique()"""

#%%

#sg.allow_geometry(setting='geometry_only')  # set to 'non_geometry' to exclude tables with geometries, and if you don't care about it either way, simply ignore this method. If you want to reset the setting, run the method without any arguments.
#sg.run_graph(starting_column='LAD21CD', ending_column='LAD21CD')
#codes = sg.geocodes(1)
#print(codes)

# %%
#sg.allow_geometry('geometry_only')

async def main():
    sg = SmartGeocoder()
    await sg.initialize(max_retries=100, retry_delay=5)
    #sg.run_graph(starting_column='OA21CD', ending_column='PCDS', geographic_areas=["SE4 1", "SE4 2"], geographic_area_columns=['PCDS'])
    sg.run_graph(starting_column='WD22CD', ending_column='LAD22NM', geographic_areas=["Lewisham"], geographic_area_columns=['LAD22NM'])
    #sg.run_graph(starting_column='OA11CD', ending_column='MSOA21CD', geographic_areas=["Lewisham"], geographic_area_columns=['LAD22NM'])
    paths = sg.paths_to_explore()
    print(paths)
    #codes = await sg.geocodes(selected_path=0, chunk_size=2500)
    codes = await sg.geocodes(selected_path=4, chunk_size=500, retun_all=True)
    print(codes)
    

if __name__ == "__main__":
    asyncio.run(main())

# %%
#codes['table_data'][0]