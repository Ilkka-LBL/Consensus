# %%
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Consensus.EsriConnector import FeatureServer
from Consensus.EsriServers import OpenGeography
from Consensus.utils import where_clause_maker


og = OpenGeography(max_retries=100)

# %%
full_name = 'Wards_December_2023_Boundaries_UK_BSC - WD_DEC_2023_UK_BSC'
column_name = 'WD23NM'
geographic_areas = ['Brockley']


fs = FeatureServer()
await fs.setup(full_name=full_name, esri_server=og._name, max_retries=100, retry_delay=2, chunk_size=50)
where_clause = where_clause_maker(values=geographic_areas, column=column_name)
output = await fs.download(where_clause=where_clause, return_geometry=True)
assert output['WD23NM'].nunique() == 1
print(output)
