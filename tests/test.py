# %%
import sys
import os
sys_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, sys_path)

from Consensus import SmartLinker, GeoHelper, OpenGeography
import platform
import asyncio

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# %%
og = OpenGeography()
await og.initialise()
await og.build_lookup()

# %%
gss = SmartLinker('OGP')
await gss.initialise()
# %%
gss.allow_geometry('connected_tables')
gss.run_graph(starting_column='LAD21CD', ending_column='OA21CD', geographic_areas=['Lewisham'], geographic_area_columns=['LAD21NM'])

# %%
data = await gss.geodata(44, chunk_size=200)
print(data['table_data'][0])

# %%

# %%
print(data['table_data'][0])


# %%
geo = data['table_data'][0]
geo = geo.set_crs("epsg:4326")
geo = geo.to_crs("epsg:27700")
geo.plot()
# %%

# %%
gss.allow_geometry('connected_tables')  # set this to ``True`` if you must have geometries in the *connected* table
gss.run_graph(starting_column='WD22CD', ending_column='LAD22CD', geographic_areas=['Lewisham', 'Southwark'], geographic_area_columns=['LAD22NM'])  # you can choose the starting and ending columns using ``GeoHelper().geographies_filter()`` method.
codes = await gss.geodata(selected_path=0, chunk_size=50)  # the selected path is the ninth in the list of potential paths output by ``run_graph()`` method. Increase chunk_size if your download is slow and try decreasing it if you are being throttled (or encounter weird errors).
print(codes['table_data'][0])  # the output is a dictionary of ``{'path': [[table1_of_path_1, table2_of_path1], [table1_of_path2, table2_of_path2]], 'table_data':[data_for_path1, data_for_path2]}``
# %%
geo = codes['table_data'][0]
geo = geo.set_crs("epsg:4326")
geo = geo.to_crs("epsg:27700")
geo.plot()

# %%
