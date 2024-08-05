# -*- coding: utf-8 -*-
"""
Created on Thu Jan 19 10:44:17 2023.

@author: ISipila

SmartGeocode class takes a starting and ending column, list of local authorities, and finds the shortest path between the start and end 
points. We do this by using graph theory, specifically the Breadth-first search method. 

"""
#%%

from pathlib import Path
import pandas as pd
from typing import Any, Dict, List, Tuple
import json
from operator import itemgetter
from pkg_resources import resource_stream
import importlib.resources as pkg_resources
from LBLDataAccess import lookups, open_geography_api

def BFS_SP(graph: Dict, start: str, goal: str) -> List[Any]:
    """Breadth-first search."""
    explored = []
     
    # Queue for traversing the
    # graph in the BFS
    queue = [[start]]
     
    # If the desired node is
    # reached
    if start == goal:
        print("Same Node")
        return 
     
    # Loop to traverse the graph
    # with the help of the queue
    while queue:
        path = queue.pop(0)
        node = path[-1]

        # Condition to check if the
        # current node is not visited
        if node not in explored:
            if isinstance(node, tuple):
                neighbours = graph[node[0]]
            else:
                neighbours = graph[node]

            # Loop to iterate over the
            # neighbours of the node
            for neighbour in neighbours:
                new_path = list(path)
                new_path.append(neighbour)
                queue.append(new_path)
                 
                # Condition to check if the
                # neighbour node is the goal
                if neighbour[0] == goal:
                    #print("Shortest path = ", *new_path)
                    return new_path
            explored.append(node)
 
    # Condition when the nodes are not connected
    return 'no_connecting_path'


class SmartGeocodeLookup:
    """Use graph theory to find shortest path between table columns.
    
    This class works as follows. The user provides the names of the starting and ending columns, and a list of local authorities when initialising the class. They can then get the appropriate subset of the geocodes using the get_filtered_geocodes() method.
    
    Internally, on initialising the class, a json file is either created based on the location of the lookup tables or read, if the json file exists. Then, using the information contained in the json file, a graph of connections between table columns is created using the run_graph() method. 
    Following the creation of the graph, all possible starting points are searched for (i.e. which tables contain the user-provided starting_table). After this, we look for the shortest paths. To do this, we look for all possible paths from all starting_columns to ending_columns and count how many steps there are between each table. We choose the shortest link, as we then join these tables together iteratively using outer join. Finally, we filter the table by the local_authorities list.

    The intended workflow is:
    gss = SmartGeocodeLookup(end_column_max_value_search=False)  
    gss.run_graph(starting_column='LAD23CD', ending_column='OA21CD', local_authorities=['Lewisham', 'Southwark']) # the starting and ending columns should end in CD
    codes = gss.get_filtered_geocodes()
    
    Above, change the end_column_max_value_search parameter to True if you want to limit the search to only tables with the maximum number of unique values. This can help with issues where lookups already exist, but which omit the full range of values. In other words, the lookups created by Open Geography Portal are intersections, but we may instead be interested in the right join. However, this may result in some tables being omitted. Setting the parameter to True should in theory help with selecting exact-fit rather than best-fit lookups, but this is not guaranteed as we cannot rely on the file name differentiating exact-fit and best-fit lookups and this information needs to be derived by looking for the maximum number of unique values given a column name. For example, OA21CD would have n unique values in a LAD21CD to OA21CD lookup, but it could have only n-m unique values in a OA11CD to OA21CD best-fit lookup, whereas exact-fit of the same columns should have n unique values for OA21CD. This will depend entirely on the geographic area of interest and it may well be that exact-fit and best-fit produce the same result. 
    
    """
    
    def __init__(self, end_column_max_value_search: bool = False, local_authority_constraint: bool = True, verbose: bool = False, lookup_location: Path = None):
        """Initialise SmartGeocodeLookup."""
        self.using_max_values = end_column_max_value_search
        self.local_authority_constraint = local_authority_constraint
        self.verbose = verbose
               
        # hard code the local authorities columns, but keep in init to allow additions later        
        self._la_possibilities = ['LAD', 'UTLA', 'LTLA']                          # local authority column names - these are hidden, but available
        
        self.files_and_folders = self.read_lookup(lookup_folder=lookup_location)  # read a json file as Pandas

    def run_graph(self, starting_column: str = None, ending_column: str = None, local_authorities: List = None):
        """
            Use this method to create the graph given start and end points, as well as the local authority.
            The starting_column and ending_column parameters should end in "CD". For example LAD21CD or WD23CD.

        """

        self.starting_column = starting_column.upper()                      # start point in the path search
        self.ending_column = ending_column.upper()                          # end point in the path search
        self.local_authorities = local_authorities                          # list of local authorities to get the geocodes for

        if self.starting_column and self.ending_column and self.local_authorities:
            self.graph, self.table_column_pairs = self.create_graph()       # create the graph for connecting columns
            if self.local_authority_constraint:
                self.starting_points = self.get_starting_point()            # find all possible starting points given criteria
            else:
                self.starting_points = self.get_starting_point_without_local_authority_constraint()
            self.shortest_paths = self.find_shortest_paths()                # get the shortest path
        
        else:
            raise Exception("You haven't provided all parameters. Make sure the local_authorities list is not empty.")
        
    
    def get_filtered_geocodes(self, n_first_routes:int = 3) -> List[pd.DataFrame]:
        """
            Get pandas dataframe filtered by the local_authorities list. 
            Setting n_first_routes to >1 gives the flexibility of choosing the best route for your use case, as the joins may not produce the exact table you're after.

            n_first_routes: give the number of possible join tables that you want to choose from. The default is set to maximum three possible join routes.
        """

        final_tables_to_return = []
        for shortest_path in self.shortest_paths[:n_first_routes]:
            if len(shortest_path) == 1:
                print(shortest_path[0])
                fs = open_geography_api.OpenGeography()
                output_table = fs.connect_to_feature_service(shortest_path[0])
                metadata = output_table.lookup_format()
                print(output_table)
                if 'geometry' in metadata['fields'][0]:
                    output = output_table.download(return_geometry=True)
                else:
                    output = output_table.download()
                
                if self.local_authority_constraint:
                    for field in metadata['fields'][0]:
                        if field[:-4].upper() in self._la_possibilities:
                            la_field = field
                            print(la_field, output_table.fields)
                            geocodes_subset = output[output[la_field].isin(self.local_authorities)]
                            return geocodes_subset
                
                        else:
                            return output
                        
                    

            else:
                joined_table = self.join_tables(shortest_path)
                joined_table = joined_table.drop_duplicates()
                joined_table.dropna(axis='columns', how='all', inplace=True)
                if self.local_authorities:
                    try:
                        la_cd_col_subset = []
                        for la_col in self._la_possibilities:
                            for final_table_col in joined_table.columns:
                                if final_table_col[:len(la_col)].upper() in self._la_possibilities and final_table_col[-2:].upper() == 'NM':
                                    la_cd_col_subset.append(final_table_col)
                        print(la_cd_col_subset)
                        if len(joined_table[joined_table[la_cd_col_subset[0]].isin(self.local_authorities)]) > 0:
                            final_tables_to_return.append(joined_table[joined_table[la_cd_col_subset[0]].isin(self.local_authorities)])
                        else:
                            print("Couldn't limit the data to listed local authorities, returning full table")
                            final_tables_to_return.append(joined_table)
                    except KeyError:
                        print("Couldn't find suitable local authority column, returning full table")
                else:
                    final_tables_to_return.append(joined_table)
        return final_tables_to_return
    
    def open_table_as_pandas(self, file_path_object: Any) -> pd.DataFrame:
        """Read table as pandas dataframe."""
        extension = file_path_object.suffix
        if extension == '.csv':
            try:
                df = pd.read_csv(file_path_object, low_memory=False)

            except UnicodeDecodeError as e:
                print(f'Got UnicodeDecodeError {e} for file {file_path_object} - changing encoding to latin-1')
                df = pd.read_csv(file_path_object, encoding='latin-1', low_memory=False)
            finally:
                if 'OBJECTID' in list(df.columns):
                    df.drop(columns=['OBJECTID'], inplace=True)
                df.columns = [col.upper().strip() for col in df.columns]
                return df
                
        elif extension == '.xlsx':
            df = pd.read_excel(file_path_object, sheet_name=0)
            if 'OBJECTID' in list(df.columns):
                df.drop(columns=['OBJECTID'], inplace=True)
            df.columns = [col.upper().strip() for col in df.columns]
            return df
    
               
    def read_lookup(self, lookup_folder) -> pd.DataFrame:
        """
            Read lookup table.

            Arguments:
                lookup_folder {Path}    -   pathlib Path to the folder where lookup.json file is stored.
            
            Returns:
                pd.DataFrame    -   Lookup table as a Pandas dataframe.
        """

        if lookup_folder:
            json_path = Path(lookup_folder) / 'lookups' / 'lookup.json'
            return pd.read_json(json_path)
        else:
            with pkg_resources.open_text(lookups, 'lookup.json') as f:
                lookup_data = json.load(f)
            return pd.DataFrame(lookup_data)

            
    
    def create_graph(self) -> Tuple[Dict, List]:
        """Create a graph of connections between tables using common column names."""
        graph = {}
        
        table_column_pairs = list(zip(self.files_and_folders['name'], self.files_and_folders['matchable_fields']))
        
        
        for enum, (table, columns) in enumerate(zip(self.files_and_folders['name'], self.files_and_folders['matchable_fields'])):
            if columns:
                graph[table] = []
                table_columns_comparison = list(table_column_pairs).copy()
                table_columns_comparison.pop(enum)
                for comparison_table, comparison_columns in table_columns_comparison:
                    if comparison_columns:
                        shared_columns = list(set(columns).intersection(set(comparison_columns)))
                        
                        for shared_column in shared_columns:
                            graph[table].append((comparison_table, shared_column))
                    
        return graph, table_column_pairs
    
    
    def get_starting_point_without_local_authority_constraint(self) -> Dict: 
        """Starting point is any table with a suitable column."""
        starting_points = {}
        
        for row in self.files_and_folders.iterrows():
            row = row[1]
            if self.starting_column in row['matchable_fields']:
                starting_points[row['name']] = {'columns': row['fields'], 'useful_columns': row['matchable_fields']}
        if starting_points:
            return starting_points
        else:
            print(f"Sorry, no tables containing column {self.starting_column} - make sure the chosen column ends in 'CD'")

    def get_starting_point(self):
        """Starting point is hard coded as being from any table with 'LAD', 'UTLA', or 'LTLA' columns."""
        starting_points = {}
        


        for row in self.files_and_folders.iterrows():
            row = row[1]
            for la_col in self._la_possibilities:
                
                la_nm_col_subset = [col for col in row['fields'] if col[:len(la_col)].upper() in self._la_possibilities and col[-2:].upper() == 'NM']
                la_cd_col_subset = [col for col in row['fields'] if col[:len(la_col)].upper() in self._la_possibilities and col[-2:].upper() == 'CD']
                if la_col in [col[:len(la_col)].upper() for col in row['matchable_fields']]:
                    if self.starting_column in row['matchable_fields']:
                        starting_points[row['name']] = {'columns': row['fields'], 'la_nm_columns': la_nm_col_subset, 'la_cd_columns': la_cd_col_subset, 'useful_columns': row['matchable_fields']}
        if starting_points:
            return starting_points
        else:
            print(f"Sorry, no tables containing column {self.starting_column} - make sure the chosen column ends in 'CD'")


    def find_paths(self) -> Dict[str, List]:
        """Find all paths given all start and end options using BFS_SP function."""
       
        """
        if self.using_max_values:
            get_nunique = itemgetter(2) 
            nunique_vals_in_columns = list(map(get_nunique, self.table_column_pairs))  # make a list of nunique values 
            end_table_indices = [i for i, x in enumerate(nunique_vals_in_columns) if x == max(nunique_vals_in_columns)]  # reduce the list to only those tables with the maximum number
            end_options = [table for i, (table, columns, columns_nunique) in enumerate(self.table_column_pairs) if i in end_table_indices]
            print(end_options)
        else:
        """
        end_options = []
        for table, columns in self.table_column_pairs:
            if self.ending_column in columns:
                end_options.append(table)

        path_options = {}
        for start_table in self.starting_points.keys():
            path_options[start_table] = {}
            for end_table in end_options:
                #print(start_table, end_table)
                
                shortest_path = BFS_SP(self.graph, start_table, end_table)
                #print('\n Shortest path: ', shortest_path, '\n')
                if shortest_path != 'no_connecting_path':
                    path_options[start_table][end_table] = shortest_path
            if len(path_options[start_table]) < 1:
                path_options.pop(start_table)
        if len(path_options) < 1:
            raise Exception("A connecting path doesn't exist, try a different starting point (e.g. LTLA21CD, UTLA21CD, LAD23CD instead of LAD21CD) or set end_column_max_value_search=False")
        else:
            return path_options
    
    
    def find_shortest_paths(self) -> List[str]:
        """From all path options, choose shortest."""
        all_paths = self.find_paths()
        shortest_path_length = 99
        shortest_paths = []
        for path_start, path_end_options in all_paths.items():
            for path_end_option, path_route in path_end_options.items():
                if isinstance(path_route, type(None)):
                    print('Shortest path is in the same table')
                    shortest_path = [path_start]
                    shortest_paths.append(shortest_path)
                    shortest_path_length = 1
                else:
                    if len(path_route) <= shortest_path_length:
                        shortest_path_length = len(path_route)
                        shortest_paths.append(path_route)
        path_indices = [i for i, x in enumerate(shortest_paths) if len(x) == shortest_path_length]
        paths_to_explore = [shortest_paths[path_index] for path_index in path_indices]

        if self.verbose:
            print('\nAll possible shortest paths:')    
            for enum, path_explore in enumerate(paths_to_explore):
                print(f'\nPath {enum+1}')
                if len(path_explore) > 1:
                    print('Starting table:', path_explore[0])
                    for join_path in path_explore[1:]:
                        print('Above joined to', join_path[0], 'via', join_path[1])
                    

        return paths_to_explore
      
    
    def join_tables(self, shortest_path) -> pd.DataFrame:
        """If multiple tables in path, apply left merge."""
        starting_csv = shortest_path[0]
        
        directory_locations = {}
        for folder, files_and_components in self.files_and_folders.items():
            file_names = files_and_components.keys()
            if starting_csv in file_names:
                directory_locations[starting_csv] = self.lookups.joinpath(Path(folder)).joinpath(Path(starting_csv))
            for connecting_table in shortest_path[1:]:
                if connecting_table[0] in file_names:
                    directory_locations[connecting_table[0]] = self.lookups.joinpath(Path(folder)).joinpath(Path(connecting_table[0]))
    
        first_table = self.open_table_as_pandas(directory_locations[starting_csv])
        if self.local_authority_constraint:
            first_table = self.filter_by_local_authority(first_table)
        first_table_columns = [col.upper() for col in list(first_table.columns)]
        first_table.columns = first_table_columns

        for table_to_join in shortest_path[1:]:
            second_table = self.open_table_as_pandas(directory_locations[table_to_join[0]])
            second_table_columns = [col.upper() for col in list(second_table.columns)]
            second_table.columns = second_table_columns

            first_table = first_table.merge(second_table, on=table_to_join[1], how='left', suffixes=('', '_DROP')).filter(regex='^(?!.*_DROP)')

        if 'OBJECTID' in first_table.columns:
            first_table.drop(columns=['OBJECTID'], inplace=True)
        return first_table
    
    
    def filter_by_local_authority(self, table_to_filter: pd.DataFrame) -> pd.DataFrame:
        """Filter the table_to_filter by local authority list."""
        joined_table_columns = table_to_filter.columns
        
        all_local_auth_columns = []
        for key in self.starting_points.keys():
            all_local_auth_columns.extend(self.starting_points[key]['la_nm_columns'])
        all_local_auth_columns = list(set(all_local_auth_columns))
        
        local_auth_columns_present_in_joined_table = []
        for possibility in all_local_auth_columns:
            for joined_column in joined_table_columns:
                if possibility == joined_column[:len(possibility)]:
                    local_auth_columns_present_in_joined_table.append(joined_column)
        
        chosen_local_auth_column = local_auth_columns_present_in_joined_table[0]

        local_authority_subset = table_to_filter[table_to_filter[chosen_local_auth_column].isin(self.local_authorities)]
        local_authority_subset = local_authority_subset.drop_duplicates()
        return local_authority_subset


class GeoHelper(SmartGeocodeLookup):
    """GeoHelper class helps with finding the starting and ending columns.
    
    This class provides three tools: 
        1) geography_keys(), which outputs a dictionary of short-hand descriptions of geographic areas
        2) available_geographies(), which takes the optional 'year' argument and outputs all available geographies.
        3) year_options attribute, which simply outputs the 'year' options that can then be used with available_geographies() method.
    """
    
    def __init__(self):
        """Initialise GeoHelper by inherting from SmartGeocodeLookup."""
        super().__init__()
        self.year_options = self._get_geocodes_for_years()
    
    
    @staticmethod
    def geography_keys():
        """Get the short-hand descriptions of geographic areas."""
        print('\nAdd a year code (e.g. 11 for 2011) and CD to the below geography codes when choosing the right geography start and end points.') 
        print('For example, choose WD22CD as a starting point and WD11CD as an end point to get the lookup table from 2022 wards to 2011 wards.')
        geography_keys = {'BUA': 'Built-up area',
                          'BUASD': 'Built-up area sub-divisions',
                          'CAUTH': 'Combined authority',
                          'CCG': 'Clinical commissioning group', 
                          'CED': 'County electoral division',
                          'CMWD': 'Census-merged wards',
                          'CTRY': 'Country',
                          'CTY': 'County',
                          'EER': 'European electoral region', 
                          'LAD': 'Local authority district',
                          'LAU1': 'Local administrative unit 1 (Eurostat)',
                          'LAU2': 'Local administrative unit 2 (Eurostat)',
                          'LPA': 'Local planning authority',
                          'LSOA': 'Lower layer super output area',
                          'LTLA': 'Lower-tier local authority',
                          'MSOA': 'Middle layer super output area',
                          'NAT': 'Nations (?)',
                          'NHSER': 'NHS England region',
                          'NUTS1': 'Nomenclature of territorial units for statistics (Eurostat)',
                          'NUTS2': 'Nomenclature of territorial units for statistics (Eurostat)',
                          'NUTS3': 'Nomenclature of territorial units for statistics (Eurostat)',
                          'OA': 'Output area',
                          'PCO': 'Primary care organisation',
                          'PCON': 'Westminster parliamentary constituency',
                          'RGN': 'Region',
                          'SHA': 'Strategic health authority',
                          'STP': 'Sustainability and transformation partnerships',
                          'TTWA': 'Travel to work area',
                          'UA': 'Unitary authority',
                          'UTLA': 'Upper-tier local authority',
                          'WD': 'Ward',
                          'WZ': 'Workplace zone'}
        return geography_keys
    
    def _get_geocodes_for_years(self) -> List[str]:
        """Output the year options."""
        year_options = [item.parts[-1] for item in list(self.lookups.iterdir()) if item.is_dir()]
        return year_options


    def get_available_geocodes(self, selected_year: Dict[str, Dict]):
        """Get a set of geocode columns for all selected lookup tables."""
        all_columns = []
        for table in selected_year.keys():
            all_columns.extend(selected_year[table]['useful_columns'])        
        all_columns = list(set([col.upper() for col in all_columns]))
        return sorted(all_columns)
    
    
    def available_geographies(self, year: str = None) -> Dict[str, str]:
        """Get the available geographies for your chosen lookup year."""
        print("\nAll available geographies:\n")
        if year:
            year = self._valid_year_choice(year)
            selected_year_tables = self._tables_by_year(year)
            geocode_columns = self.get_available_geocodes(selected_year_tables)
            return geocode_columns

        else:
            all_geocode_columns = []
            for year in self.year_options:
                selected_year_tables = self._tables_by_year(year)
                geocode_columns = self.get_available_geocodes(selected_year_tables)
                all_geocode_columns.extend(geocode_columns)
            all_geocode_columns = list(set(all_geocode_columns))
            return sorted(all_geocode_columns)

    
    def _valid_year_choice(self, selected_year: str) -> str:
        """Make sure chosen lookup year is valid."""
        selected_year = str(selected_year)
        assert (selected_year in self.year_options), f"{selected_year} not in {self.year_options} - please pick one of the options"
        return selected_year
    
    
    def _tables_by_year(self, selected_year: str) -> Dict[str, Dict]:
        """Return tables by selected lookup year."""
        for year, tables in self.files_and_folders.items():
            if selected_year == year:
                return tables
    
def _test_smart_lookup():
    print('Testing SmartGeocodeLookup')

    # get all tables and their columns
    gss = SmartGeocodeLookup(end_column_max_value_search=False, local_authority_constraint=True, verbose=True)  # changing end_column_max_value_search to True gives different results from setting it True
    gss.run_graph(starting_column='OA11CD', ending_column='MSOA21CD', local_authorities=['Lewisham'])
    
    filtered = gss.get_filtered_geocodes(3)
    return filtered

def _test_geohelper():
    print('\nTesting GeoHelper')
    geo_help = GeoHelper()
    print('\n year options:')
    print(geo_help.year_options)
    print(geo_help.geography_keys())
    print(geo_help.available_geographies())


def _test_og_API():
    gss = SmartGeocodeLookup()
    gss.run_graph(starting_column='OA11CD', ending_column='OA21CD', local_authorities=['Lewisham'])
    
    filtered = gss.get_filtered_geocodes(3)
    return filtered

#%%
if __name__ == '__main__':
    

    gss = SmartGeocodeLookup()
    try:
        gss.run_graph(starting_column='OA11CD', ending_column='MSOA21CD', local_authorities=['Lewisham'])
    
        filtered = gss.get_filtered_geocodes(1)

    except Exception as e:
        print(e)
        print("Graph:")
        #print(gss.graph)
        #print(gss.files_and_folders)
    

# %%
fs = open_geography_api.OpenGeography()
output_table = fs.connect_to_feature_service('OA11_LAD15_LSOA11_MSOA11_LEP14_EN_LUv2_55efc515fae94c8dabd9c6e3baeb9cb8')
out = output_table.lookup_format()
dl = output_table.download()
dl
#%%
out['fields'][0]

#%%
gss = SmartGeocodeLookup()

gss.files_and_folders[gss.files_and_folders['name'] == 'OA11_LAD15_LSOA11_MSOA11_LEP14_EN_LUv2_55efc515fae94c8dabd9c6e3baeb9cb8']