#%%
from LBLDataAccess.GeocodeMerger import SmartGeocoder
from LBLDataAccess.Nomis import DownloadFromNomis
import os

sg = SmartGeocoder()

with open(".env", 'r') as e:
    line = e.readline().split("NOMIS_API=")[1]

    os.environ['NOMIS'] = line

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
codes['table_data'][0]['LAD22NM'].unique()

#%%
sg = SmartGeocoder(geometry_only=True)
sg.run_graph(starting_column='WD21CD', ending_column='WD21CD')
codes = sg.geocodes(1)
print(codes)

# %%
sg.run_graph(starting_column='WD22CD', ending_column='WD22CD', local_authorities=['Lewisham', 'Greenwich'])
codes = sg.geocodes(1)
print(codes)

# %%
codes['table_data'][0]