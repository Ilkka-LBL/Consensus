# -*- coding: utf-8 -*-
"""
Created on Thu Jan 19 10:44:17 2023.

@author: ISipila

SmartGeocoder class takes a starting and ending column, list of local authorities, and finds the shortest path between the start and end 
points. We do this by using graph theory, specifically the Breadth-first search method between the columns of the various tables. 
The end result is not by any means perfect and you are advised to output at least three different paths and to check that the output makes sense.

"""

from pathlib import Path
import pandas as pd
from typing import Any, Dict, List, Tuple
import json
import importlib.resources as pkg_resources
from LBLDataAccess import OpenGeographyPortal, lookups

def BFS_SP(graph: Dict, start: str, goal: str) -> List[Any]:
    """Breadth-first search."""
    explored = []
     
    # Queue for traversing the graph in the BFS
    queue = [[start]]
     
    # If the desired node is reached
    if start == goal:
        print("Same Node")
        return 
     
    # Loop to traverse the graph with the help of the queue
    while queue:
        path = queue.pop(0)
        node = path[-1]

        # Condition to check if the current node is not visited
        if node not in explored:
            if isinstance(node, tuple):
                neighbours = graph[node[0]]
            else:
                neighbours = graph[node]

            # Loop to iterate over the neighbours of the node
            for neighbour in neighbours:
                new_path = list(path)
                new_path.append(neighbour)
                queue.append(new_path)
                 
                # Condition to check if the neighbour node is the goal
                if neighbour[0] == goal:
                    return new_path
            explored.append(node)
 
    # Condition when the nodes are not connected
    return 'no_connecting_path'


class SmartGeocoder:
    """
    
        Uses graph theory to find shortest path between table columns.

        Methods:
            run_graph   -   This method creates the graph by searching through the lookup.json file for data with shared column names, given the names of the starting and ending columns.
            geocodes    -   This method outputs the geocodes given the 

        Usage:
            This class works as follows. The user provides the names of the starting and ending columns, and an optional list of local authorities when using the run_graph() method. 
            They can then get the appropriate subset of the geocodes using the geocodes() method.
            
            Internally, on initialising the class, a json lookup file is read, if the json file exists. Then, using the information contained in the json file, a graph of connections between table columns is created using the run_graph() method. 
            Following the creation of the graph, all possible starting points are searched for (i.e. which tables contain the user-provided starting_table). After this, we look for the shortest paths. To do this, we look for all possible paths from all starting_columns to ending_columns and count how many steps there are between each table. We choose the shortest link, as we then join these tables together iteratively using outer join. Finally, we filter the table by the local_authorities list.

            The intended workflow is:
            gss = SmartGrapher(end_column_max_value_search=False)  
            gss.run_graph(starting_column='LAD23CD', ending_column='OA21CD', local_authorities=['Lewisham', 'Southwark']) # the starting and ending columns should end in CD
            codes = gss.geocodes()
            
            Above, change the end_column_max_value_search parameter to True if you want to limit the search to only tables with the maximum number of unique values. This can help with issues where lookups already exist, but which omit the full range of values. In other words, the lookups created by Open Geography Portal are intersections, but we may instead be interested in the right join. However, this may result in some tables being omitted. Setting the parameter to True should in theory help with selecting exact-fit rather than best-fit lookups, but this is not guaranteed as we cannot rely on the file name differentiating exact-fit and best-fit lookups and this information needs to be derived by looking for the maximum number of unique values given a column name. For example, OA21CD would have n unique values in a LAD21CD to OA21CD lookup, but it could have only n-m unique values in a OA11CD to OA21CD best-fit lookup, whereas exact-fit of the same columns should have n unique values for OA21CD. This will depend entirely on the geographic area of interest and it may well be that exact-fit and best-fit produce the same result. 

    """
    
    def __init__(self, end_column_max_value_search: bool = False, verbose: bool = False, lookup_location: Path = None, geometry_only: bool = False):
        """Initialise SmartGrapher."""
        self.using_max_values = end_column_max_value_search
        self.verbose = verbose
               
        # hard code the local authorities columns, but keep in init to allow additions later        
        self._la_possibilities = ['LAD', 'UTLA', 'LTLA']                          # local authority column names - these are hidden, but available
        
        self.lookup = self.read_lookup(lookup_folder=lookup_location)  # read a json file as Pandas
        if geometry_only:
            self.lookup = self.lookup[self.lookup['has_geometry']==geometry_only]

    def run_graph(self, starting_column: str = None, ending_column: str = None, local_authorities: List = None):
        """
            Use this method to create the graph given start and end points, as well as the local authority.
            The starting_column and ending_column parameters should end in "CD". For example LAD21CD or WD23CD.

        """

        self.starting_column = starting_column.upper()                      # start point in the path search
        self.ending_column = ending_column.upper()                          # end point in the path search
        self.local_authorities = local_authorities                          # list of local authorities to get the geocodes for

        if self.starting_column and self.ending_column:
            self.graph, self.table_column_pairs = self.create_graph()       # create the graph for connecting columns
            if self.local_authorities:
                self.starting_points = self.get_starting_point()            # find all possible starting points given criteria
            else:
                self.starting_points = self.get_starting_point_without_local_authority_constraint()
            self.shortest_paths = self.find_shortest_paths()                # get the shortest path
        
        else:
            raise Exception("You haven't provided all parameters. Make sure the local_authorities list is not empty.")
        
    def _get_ogp_table(self, pathway:str) -> Tuple[pd.DataFrame, str]:
        """
            Download relevant data from Open Geography Portal
        """

        fs = OpenGeographyPortal.FeatureServer(pathway)
        if 'geometry' in fs.feature_service.data['fields'][0]:
            return fs.download(return_geometry=True)
        else:
            return fs.download()
        


    def geocodes(self, n_first_routes:int = 3) -> Dict[str, List]:
        """
            Get pandas dataframe filtered by the local_authorities list. 
            Setting n_first_routes to >1 gives the flexibility of choosing the best route for your use case, as the joins may not produce the exact table you're after.

            n_first_routes: give the number of possible join tables that you want to choose from. The default is set to maximum three possible join routes.
        """

        final_tables_to_return = {'paths':[], 'table_data':[]}
        for shortest_path in self.shortest_paths[:n_first_routes]:
            start_table = self._get_ogp_table(shortest_path[0])                
            start_table.columns = [col.upper() for col in list(start_table.columns)]
            print(shortest_path)
            final_tables_to_return['paths'].append(shortest_path)
            if len(shortest_path) == 1:                
                if self.local_authorities:
                    try:
                        for la_col in self._la_possibilities:
                            for final_table_col in start_table.columns:
                        
                                if final_table_col[:len(la_col)].upper() in self._la_possibilities and final_table_col[-2:].upper() == 'NM':              
                                    final_tables_to_return['table_data'].append(start_table[start_table[final_table_col].isin(self.local_authorities)])
                                    
                    except Exception as e:
                        print(f"Error: {e}, returning full table")
                        final_tables_to_return['table_data'].append(start_table)
                        
                else:
                    final_tables_to_return['table_data'].append(start_table)
                    
            else:
                for pathway in shortest_path[1:]:
                    next_table = self._get_ogp_table(pathway[0])
                    next_table.columns = [col.upper() for col in list(next_table.columns)]
                    start_table = start_table.merge(next_table, on=pathway[1], how='left', suffixes=('', '_DROP')).filter(regex='^(?!.*_DROP)')
                start_table = start_table.drop_duplicates()
                start_table.dropna(axis='columns', how='all', inplace=True)

                if self.local_authorities:
                    try:
                        la_cd_col_subset = []
                        for la_col in self._la_possibilities:
                            for final_table_col in start_table.columns:
                                if final_table_col[:len(la_col)].upper() in self._la_possibilities and final_table_col[-2:].upper() == 'NM':
                                    la_cd_col_subset.append(final_table_col)
                        if len(start_table[start_table[la_cd_col_subset[0]].isin(self.local_authorities)]) > 0:
                            final_tables_to_return['table_data'].append(start_table[start_table[la_cd_col_subset[0]].isin(self.local_authorities)])
                        else:
                            print("Couldn't limit the data to listed local authorities, returning full table")
                            final_tables_to_return['table_data'].append(start_table)
                    except Exception as e:
                        print(f"Error: {e}, returning full table")
                        final_tables_to_return['table_data'].append(start_table)
                        
                else:
                    final_tables_to_return['table_data'].append(start_table)
        return final_tables_to_return
    
               
    def read_lookup(self, lookup_folder:Path = None) -> pd.DataFrame:
        """
            Read lookup table.

            Arguments:
                lookup_folder {Path}    -   pathlib Path to the folder where lookup.json file is stored.
            
            Returns:
                pd.DataFrame    -   Lookup table as a Pandas dataframe.
        """
        try:
            if lookup_folder:
                json_path = Path(lookup_folder) / 'lookups' / 'lookup.json'
                return pd.read_json(json_path)
            else:
                with pkg_resources.open_text(lookups, 'lookup.json') as f:
                    lookup_data = json.load(f)
                return pd.DataFrame(lookup_data)
        except FileNotFoundError:
            print('No lookup.json file found, building from scratch')
            return OpenGeographyPortal.OpenGeographyLookup().build_lookup()
            
    
    def create_graph(self) -> Tuple[Dict, List]:
        """Create a graph of connections between tables using common column names."""
        graph = {}
        
        table_column_pairs = list(zip(self.lookup['name'], self.lookup['matchable_fields']))
        
        
        for enum, (table, columns) in enumerate(zip(self.lookup['name'], self.lookup['matchable_fields'])):
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
        
        for row in self.lookup.iterrows():
            row = row[1]
            if self.starting_column in row['matchable_fields']:
                starting_points[row['name']] = {'columns': row['fields'], 'useful_columns': row['matchable_fields']}
        if starting_points:
            return starting_points
        else:
            print(f"Sorry, no tables containing column {self.starting_column} - make sure the chosen column ends in 'CD' and try removing local_authorities argument")

    def get_starting_point(self):
        """Starting point is hard coded as being from any table with 'LAD', 'UTLA', or 'LTLA' columns."""
        starting_points = {}
        
        for row in self.lookup.iterrows():
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
            print(f"Sorry, no tables containing column {self.starting_column} - make sure the chosen column ends in 'CD'  and try removing local_authorities argument")


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
            raise Exception("A connecting path doesn't exist, try a different starting point (e.g. LTLA21CD, UTLA21CD, LAD23CD instead of LAD21CD), set geometry_only=False, or set end_column_max_value_search=False")
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
      


#TODOOOOO
class GeoHelper(SmartGeocoder):
    """GeoHelper class helps with finding the starting and ending columns.
    
    This class provides three tools: 
        1) geography_keys(), which outputs a dictionary of short-hand descriptions of geographic areas
        2) available_geographies(), which outputs all available geographies.
    """
    
    def __init__(self):
        """Initialise GeoHelper by inherting from SmartGrapher."""
        super().__init__()
    
    
    @staticmethod
    def geography_keys():
        """Get the short-hand descriptions of most common geographic areas."""

        geography_keys = {'AONB': 'Areas of Outstanding Natural Beauty',
                          'BUA': 'Built-up areas',
                          'BUASD': 'Built-up area sub-divisions',
                          'CAL': 'Cancer Alliances',
                          'CALNCV': 'Cancer Alliances / National Cancer Vanguards',
                          'CAUTH': 'Combined authorities',
                          'CCG': 'Clinical commissioning groups', 
                          'CED': 'County electoral divisions',
                          'CIS': 'Covid Infection Survey',
                          'CMCTY': '?',
                          'CMLAD': 'Census-merged local authority districts',
                          'CMWD': 'Census-merged wards',
                          'CSP': 'Community safety partnerships',
                          'CTRY': 'Countries',
                          'CTY': 'Counties',
                          'CTYUA': 'Counties and unitary authorities',
                          'DCELLS': 'Department for Children, Education, Lifelong Learning and Skills',
                          'DZ': 'Data zones (Scotland)',
                          'EER': 'European electoral regions', 
                          'FRA': 'Fire and rescue authorities',
                          'GB': '?',
                          'GLTLA': 'Grouped lower-tier local authorities',
                          'GOR': 'Regions?',
                          'HB': 'Health boards',
                          'HLTH': 'Strategic Health Authority Name (England), Health Board Name (Scotland), Local Health Board Name (Wales)',
                          'HSCB': 'Health and social care boards',
                          'ICB': 'Integrated care boards',
                          'IOL': 'Inner and outer London',
                          'ITL1': 'International territorial level 1',
                          'ITL2': 'International territorial level 2',
                          'ITL3': 'International territorial level 3',
                          'IZ': 'Intermediate zones',
                          'LA': 'Local authority districts (historic: 1961)',
                          'LAC': 'London assembly constituencies',
                          'LAD': 'Local authority districts',
                          'LAU1': 'Local administrative unit 1 (Eurostat)',
                          'LAU2': 'Local administrative unit 2 (Eurostat)',
                          'LEP': 'Local enterprise partnerships',
                          'LEPNOP': 'Local enterprise partnerships (non overlapping parts)',
                          'LEPOP': 'Local enterprise partnerships (overlapping parts)',
                          'LGD': 'Local government districts',
                          'LHB': 'Local health boards',
                          'LMCTY': '?',
                          'LOC': 'Locations',
                          'LPA': 'Local planning authorities',
                          'LRF': 'Local resilience forums',
                          'LSIP': 'Local skills improvement plan areas',
                          'LSOA': 'Lower layer super output areas',
                          'LSOAN': 'Lower layer super output areas Northern Ireland',
                          'LTLA': 'Lower-tier local authorities',
                          'MCTY': 'Metropolitan counties',
                          'MSOA': 'Middle layer super output areas',
                          'NAER': 'National Assembly Economic Regions in Wales',
                          'NAT': 'England and Wales',
                          'NAWC': 'National Assembly for Wales constituencies',
                          'NAWER': 'National Assembly for Wales electoral regions',
                          'NCP': 'Non-civil parished areas',
                          'NCV': 'National Cancer Vanguards',
                          'NHSAT': '?',
                          'NHSCR': 'NHS commissioning regions',
                          'NHSER': 'NHS England regions',
                          'NHSRG': 'NHS regions',
                          'NHSRL': 'NHS England (Region, Local office)',
                          'NPARK': 'National parks',
                          'NSGC': 'Non-Standard Geography Categories',
                          'NUTS0': 'Nomenclature of territorial units for statistics (Eurostat)',
                          'NUTS1': 'Nomenclature of territorial units for statistics (Eurostat)',
                          'NUTS2': 'Nomenclature of territorial units for statistics (Eurostat)',
                          'NUTS3': 'Nomenclature of territorial units for statistics (Eurostat)',
                          'OA': 'Output areas',
                          'PAR': 'Parishes',
                          'PARNCP': 'Parishes and non civil parished areas',
                          'PCDS': 'Postcode sectors',
                          'PCO': 'Primary care organisations',
                          'PCON': 'Westminster parliamentary constituencies',
                          'PFA': 'Police force areas',
                          'PHEC': 'Public Health England Centres',
                          'PHEREG': 'Public Health England Regions',
                          'PLACE': 'Place names (index of)',
                          'PSHA': 'Pan strategic health authorities',
                          'REGD': 'Registration districts',
                          'RGN': 'Regions',
                          'RGNT': 'Regions (historic: 1921)',
                          'RUC': 'Rural urban classifications',
                          'RUCOA': '?',
                          'SA': 'Small areas (Northern Ireland)',
                          'SCN': 'Strategic clinical networks',
                          'SENC': 'Senedd Cymru Constituencies in Wales',
                          'SENER': 'Senedd Cymru Electoral Regions in Wales',
                          'SHA': 'Strategic health authorities',
                          'SICBL': 'Sub Integrated Care Board Locations',
                          'SOAC': 'Super output area classifications (Northern Ireland)',
                          'SPC': 'Scottish Parliamentary Constituencies',
                          'SPR': 'Scottish Parliamentary Regions',
                          'STP': 'Sustainability and transformation partnerships',
                          'TCITY': 'Major Towns and Cities in England and Wales',
                          'TTWA': 'Travel to work areas',
                          'UA': 'Unitary authorities',
                          'UACC': 'Urban audit core cities',
                          'UAFUA': 'Urban audit functional urban areas',
                          'UAGC': 'Urban audit greater cities',
                          'UK': '?',
                          'UTLA': 'Upper-tier local authorities',
                          'WD': 'Wards',
                          'WDCAS': 'Census area statistics wards',
                          'WDSTB': 'Standard Table Wards',
                          'WDSTL': 'Statistical wards',
                          'WPC': 'Westminster Parliamentary Constituencies',
                          'WZ': 'Workplace zones'}
        return geography_keys
    

    def available_geographies(self) -> List[str]:
        """ Prints the available geocode columns."""
        available_geocodes = sorted(list(self.lookup[self.lookup['matchable_fields'].map(len)>0]['matchable_fields'].explode().unique()))
        return available_geocodes
        
    def geographies_filter(self, geo_key:str=None) -> List[str]:
        assert geo_key is not None, 'Please provide geo_key argument - select a key using geography_keys() method.'
        geo_key = geo_key.upper()
        available_geocodes = self.available_geographies()
        filtered_geocodes = [i for i in available_geocodes if i[:len(geo_key)] == geo_key and i[len(geo_key):-2].isnumeric()]
        return filtered_geocodes

    

