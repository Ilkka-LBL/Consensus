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
from Consensus import AsyncOGP, lookups
import aiohttp
import asyncio
from numpy import random

random.seed(42)

def BFS_SP(graph: Dict, start: str, goal: str) -> List[Any]:
    """
    Breadth-first search.

    Args:
        graph (Dict): Dictionary of connected tables based on shared columns.
        start (str): Starting table and column.
        goal (str): Final table and column. 

    Returns:
        List[Any]: A path as a list 
    """
    explored = []
     
    # Queue for traversing the graph in the BFS
    queue = [[start]]
     
    # If the desired node is reached
    if start == goal:
        print("Start and end point are the same")
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


class InvalidColumnError(Exception):
    """Raise if invalid column"""

class MissingDataError(Exception):
    """Raise if no data found"""

class InvalidPathError(Exception):
    """Raise if graph path length less than one"""

class SmartGeocoder:
    """
    
        Uses graph theory (breadth-first search) to find shortest path between table columns.

        Methods:
            run_graph: This method creates the graph by searching through the lookup.json file for data with shared column names, given the names of the starting and ending columns.
            geocodes: This method outputs the geocodes given the start and end columns 

        Usage:
            This class works as follows. The user provides the names of the starting and ending columns, and an optional list of local authorities when using the run_graph() method. 
            They can then get the appropriate subset of the geocodes using the geocodes() method.
            
            Internally, on initialising the class, a json lookup file is read, if the json file exists. Then, using the information contained in the json file, a graph of connections between table columns is created using the run_graph() method. 
            Following the creation of the graph, all possible starting points are searched for (i.e. which tables contain the user-provided starting_table). After this, we look for the shortest paths. 
            To do this, we look for all possible paths from all starting_columns to ending_columns and count how many steps there are between each table. We choose the shortest link, as we then join these tables together iteratively using outer join. 
            Finally, we filter the table by the local_authorities list.

            The intended workflow is:
            gss = SmartGeocoder()  
            gss.allow_geometry('geometry_only')  # use this method to restrict the graph search space to tables with geometry
            gss.run_graph(starting_column='LAD21CD', ending_column='OA21CD', local_authorities=['Lewisham', 'Southwark']) # the starting and ending columns should end in CD

            codes = gss.geocodes()
            

    """
    
    def __init__(self, lookup_location: Path = None, **kwargs):
        """Initialise SmartGeocoder."""
        self.lookup_location = lookup_location
        self.ogp = None
        self.fs_service_table = None
        self.initial_lookup = None
        self.lookup = None

        # Initialise attributes that don't require async operations
        self.initial_lookup = self.read_lookup(lookup_folder=lookup_location)  # read a json file as Pandas
        self.lookup = self.initial_lookup

    async def initialise(self, **kwargs) -> None:
        """
        Initialise the async.

        Returns:
            None
        """
        self.ogp = AsyncOGP.OpenGeography(**kwargs)
        await self.ogp.initialise()
        self.fs_service_table = self.ogp.service_table
        self.fs = AsyncOGP.AsyncFeatureServer()

    def allow_geometry(self, setting: str = None) -> None:
        """
        Use this method to limit the graph search space, which slightly speeds up the process, but also limits the possible connections that can be made. If you're only interested in geographic areas with geometries (say, you need ward boundaries), 
        then set the 'setting' argument to 'geometry_only'. 

        If a setting has been chosen, you may find that you need to reset it so that you can search a wider space. To do so, simply run the method without any arguments and it will reset the lookup space to default.

        Args:
            setting (str): Either 'geometry_only' or 'non_geometry'. Anything else will use the default, which is that both geometry and non-geometry tables are used.
        
        Returns:
            None
        """
        self.lookup = self.initial_lookup
        
        if setting == 'non_geometry':
            print('The graph search space has been set to use only the tables without geometries.')
            self.lookup = self.lookup[self.lookup['has_geometry']==False]
        
        elif setting == 'geometry_only':
            print('The graph search space has been set to use only the tables with geometries.')
            self.lookup = self.lookup[self.lookup['has_geometry']==True]

        else:
            print('The graph search space has been reset. Using all available tables.')
            

    def run_graph(self, starting_column: str = None, ending_column: str = None, geographic_areas: List[str] = None, geographic_area_columns: List[str] = ['LAD22NM', 'UTLA22NM', 'LTLA22NM']):
        """
            Use this method to create the graph given start and end points, as well as the local authority.
            The starting_column and ending_column parameters should end in "CD". For example LAD21CD or WD23CD.

            Arguments:
                starting_column {str}   -   This should be the full column name (case insensitive) of the data that you want as your starting point. The one constraint is that it should end in "CD". 
                                            For instance, WD21CD for 2021 wards.
                ending_column {str} -   As above, but this should be final endpoint. 
                geographic_areas {List[str]}    -   An optional argument. Provide a list of local authorities (e.g. ['Lewisham', 'Greenwich']) if you want the starting table to be restricted 
                                                    to the set of tables that have one of following columns: "LAD##CD", "LTLA##CD", "UTLA##CD", where ## refers to a year. 
                geographic_areas_columns {List[str]}    -   An optional argument. A list of columns to check for the geographic areas.
                

        """
        assert starting_column, "No start point provided"
        assert ending_column, "No end point provided"
        self.starting_column = starting_column.upper()                                          # start point in the path search
        self.ending_column = ending_column.upper()                                              # end point in the path search
        self.geographic_areas = geographic_areas                                                # list of geographic areas to get the geocodes for
        self.geographic_area_columns = [i.upper() for i in geographic_area_columns]             # column names to restrict the starting table to. Must only contain the alphabets before the "##CD" part of the column name, ## referring to a year. Defaults to using local authority columns.

        if self.starting_column and self.ending_column:
            self.graph, self.table_column_pairs = self.create_graph()       # create the graph for connecting columns
            if self.geographic_areas:
                self.starting_points = self.get_starting_point()            # find all possible starting points given criteria
            else:
                self.starting_points = self.get_starting_point_without_local_authority_constraint()
            self.shortest_paths = self.find_shortest_paths()                # get the shortest path
        
        else:
            raise Exception("You haven't provided all parameters. Make sure the local_authorities list is not empty.")
        

    def _where_clause_maker(self, string_list: List, column_name: str, table_name: str) -> str:
        where_clause = f"{column_name} IN {str(tuple(string_list))}" if len(string_list) > 1 else f"{column_name} IN ('{str(self.geographic_areas[0])}')"
        print(f"Selecting items based on SQL: {where_clause} in table {table_name}")
        return where_clause
    

    async def _get_ogp_table(self, pathway: str, where_clause: str = "1=1", **kwargs) -> Tuple[pd.DataFrame, str]:
        max_retries = kwargs.get('max_retries', 20)
        retry_delay = kwargs.get('retry_delay', 5)
        chunk_size = kwargs.get('chunk_size', 50)

        await self.fs.setup(service_name=pathway, service_table=self.fs_service_table, max_retries=max_retries, retry_delay=retry_delay, chunk_size=chunk_size)
        print("Table fields:")
        print(self.fs.feature_service.data['fields'][0])
        if 'geometry' in self.fs.feature_service.data['fields'][0]:
            return await self.fs.download(where_clause=where_clause, return_geometry=True)
        else:
            return await self.fs.download(where_clause=where_clause)


    async def geocodes(self, selected_path: int = None, retun_all: bool = False, **kwargs) -> Dict[str, List[Any]]:
        """
            Get pandas dataframe filtered by the local_authorities list. 
            Setting n_first_routes to >1 gives the flexibility of choosing the best route for your use case, as the joins may not produce the exact table you're after.

            Arguments:
                selected_path {int} -   Choose the path based on the position of your path.
                retun_all {bool}    -   Set this to True if you want to get individual tables that would otherwise get merged instead of the merged data.
                **kwargs    -   These keyword arguments get passed to AsyncOGP's AsyncFeatureServer() object. Main keywords to use are max_retries, timeout, and chunk_size. Change these if you're experiencing connectivity issues. 
                                For instance, add more retries and increase time between tries, and reduce chunk_size for each call so you're not being overwhelming the server.

            Returns:
                Dict[str, List[Any]] -   A dictionary of merged tables, where the first key ('paths') refers to a list of lists that of the merged tables and the second key-value pair ('table_data') contains a list of Pandas dataframe objects that are the left joined data tables.
        """
        print(selected_path)

        final_tables_to_return = {'path':[], 'table_data':[]}

        assert 0 <= selected_path < len(self.shortest_paths), f"selected_path not in the range (0, {len(self.shortest_paths)})"
        chosen_path = self.shortest_paths[selected_path]
        
        print(chosen_path)
        print("Chosen shortest path: ", chosen_path)
        final_tables_to_return['path'].append(chosen_path)
                
        print("Currently downloading:", chosen_path[0])

        table_downloads = {'table_name': [], 'download_order': [], 'connected_to_previous_table_by_column':[], 'data': []}

        if self.geographic_areas: 
            # if limiting the data to specific local authorities, we need to modify the where_clause from "1=1" to the correct name of the column (e.g. LAD21NM) so that e.g. a list of ['Lewisham', 'Greenwich'] becomes an SQL call "LAD21NM IN ('Lewisham', 'Greenwich')". 
            # This has an upper limit, however, so if the list is too long, we need to handle those cases too. 
            column_names = [i for i in self.lookup[self.lookup['name']==chosen_path[0]]['fields'][0] if i.upper() in self.geographic_area_columns]# and i.upper().endswith('NM')]
            for final_table_col in column_names:
                if final_table_col.upper() in self.geographic_area_columns: #and final_table_col.upper().endswith('NM'):
                    string_list = [f'{i}' for i in self.geographic_areas]
                    if len(string_list) < 200:
                        where_clause = self._where_clause_maker(string_list, final_table_col, chosen_path[0])
                        start_table = await self._get_ogp_table(chosen_path[0], where_clause=where_clause, kwargs=kwargs)
                        start_table.drop_duplicates(inplace=True)

                    else:
                        print(f"More than 200 items listed for 'geographic_areas' argument, returning full table and filtering after")
                        start_table = await self._get_ogp_table(chosen_path[0], kwargs=kwargs)
                        start_table.drop_duplicates(inplace=True)
                        start_table = start_table[start_table[final_table_col].isin(self.geographic_areas)]

        else:
            start_table = await self._get_ogp_table(chosen_path[0], kwargs=kwargs)
            start_table.drop_duplicates(inplace=True)
        table_downloads['table_name'].append(chosen_path[0])
        table_downloads['download_order'].append(0)
        table_downloads['connected_to_previous_table_by_column'].append('NA')
        table_downloads['data'].append(start_table)

        if len(chosen_path) == 1:  # if the path length is 1 (i.e. only one table is needed), just append to the dictionary to be returned
            final_tables_to_return['table_data'].append(start_table)
            return final_tables_to_return
        
        else:
            for enum, pathway in enumerate(chosen_path[1:]):
                connecting_column = pathway[1]
                string_list = [f'{i}' for i in start_table[connecting_column].unique()]
                if len(string_list) < 100:
                    where_clause = self._where_clause_maker(string_list, final_table_col, chosen_path[0])
                    next_table = await self._get_ogp_table(pathway[0], where_clause=where_clause, kwargs=kwargs)
                    next_table.columns = [col.upper() for col in list(next_table.columns)]
                else:
                    print("More than 100 unique values to join, downloading full table and applying left join")
                    next_table = await self._get_ogp_table(pathway[0], kwargs=kwargs)
                    next_table.columns = [col.upper() for col in list(next_table.columns)]
                
                table_downloads['table_name'].append(pathway[0])
                table_downloads['download_order'].append(enum+1)
                table_downloads['connected_to_previous_table_by_column'].append(pathway[1])
                table_downloads['data'].append(next_table)
                start_table = start_table.merge(next_table, on=connecting_column, how='left', suffixes=('', '_DROP')).filter(regex='^(?!.*_DROP)')  # always perform left join on the common column (based on its name), add "_DROP" to column names that are duplicated and then filter them out.
            start_table = start_table.drop_duplicates()
            start_table.dropna(axis='columns', how='all', inplace=True)
            final_tables_to_return['table_data'].append(start_table)

            if retun_all:
                return table_downloads
            else:   
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
            return AsyncOGP.OpenGeographyLookup().build_lookup(replace_old=True)
            
    
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
            raise MissingDataError(f"Sorry, no tables containing column {self.starting_column} - try without geographic_areas argument")


    def get_starting_point(self):
        """Starting point is hard coded as being from any table with 'LAD', 'UTLA', or 'LTLA' columns."""
        
        starting_points = {}
        
        for row in self.lookup.iterrows():
            row = row[1]
            for la_col in self.geographic_area_columns:
                
                la_nm_col_subset = [col for col in row['fields'] if col[:len(la_col)].upper() in self.geographic_area_columns and col.endswith('NM')]
                la_cd_col_subset = [col for col in row['fields'] if col[:len(la_col)].upper() in self.geographic_area_columns and col.endswith('CD')]
                if la_col in [col[:len(la_col)].upper() for col in row['matchable_fields']]:
                    if self.starting_column in row['matchable_fields']:
                        starting_points[row['name']] = {'columns': row['fields'], 'la_nm_columns': la_nm_col_subset, 'la_cd_columns': la_cd_col_subset, 'useful_columns': row['matchable_fields']}
        if starting_points:
            return starting_points
        else:
            raise MissingDataError(f"Sorry, no tables containing column {self.starting_column} - try without geographic_areas argument")


    def find_paths(self) -> Dict[str, List]:
        """Find all paths given all start and end options using BFS_SP function."""
       
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
            raise InvalidPathError("A connecting path doesn't exist, try a different starting point (e.g. WD22CD instead of WD21CD) or set allow_geometry() to default if you have limited the search to 'geometry_only'")
        else:
            return dict(sorted(path_options.items()))


    def find_shortest_paths(self) -> List[str]:
        """From all path options, choose shortest."""
        all_paths = self.find_paths()
        shortest_path_length = 99
        shortest_paths = []
        for path_start, path_end_options in all_paths.items():
            for path_end_option, path_route in path_end_options.items():
                if isinstance(path_route, type(None)):
                    #print(f'Start and end in the same table: {path_start}')
                    shortest_path = [path_start]
                    shortest_paths.append(shortest_path)
                    shortest_path_length = 1
                else:
                    #path_tables = [i[0] for i in path_route[1:]]
                    #path_tables.insert(0, path_route[0])
                    #path_tables = " - ".join(path_tables)
                    #print(f"Exploring path route: {path_tables}")
                    if len(path_route) <= shortest_path_length:
                        shortest_path_length = len(path_route)
                        shortest_paths.append(path_route)
        path_indices = [i for i, x in enumerate(shortest_paths) if len(x) == shortest_path_length]
        paths_to_explore = [shortest_paths[path_index] for path_index in path_indices]
        self.path_tables = self._path_to_tables(paths_to_explore)
        print(f"These are the best paths. Choose one from the following using integers (starting from 0) and input to geocodes(selected_path=): {chr(10)}{f'{chr(10)}'.join([f'{enum}) {i}' for enum, i in enumerate(self.path_tables)])}")
        return paths_to_explore
    

    def _path_to_tables(self, paths: List[List] = [[]]) -> List:
        """ Make a list of tables in the path """

        path_tables = []
        for pth in paths:
            tables = [pth[0]]
            for table in pth[1:]:
                tables.append(table[0])
            path_tables.append(tables)
        return path_tables
    

    def paths_to_explore(self) -> Dict:
        """ Returns all possible paths (only table names) as a dictionary. The keys can be used to select your desired path by inputting it like: geocodes(selected_path=key) """
        explore_dict = {}
        for enum, i in enumerate(self.path_tables):
            explore_dict[enum] = i
        return explore_dict

#TODOOOOO
class GeoHelper(SmartGeocoder):
    """GeoHelper class helps with finding the starting and ending columns.
    
    This class provides three tools: 
        1) geography_keys(), which outputs a dictionary of short-hand descriptions of geographic areas
        2) available_geographies(), which outputs all available geographies.
    """
    
    def __init__(self):
        """
        Initialise GeoHelper by inherting from SmartGeocoder.
        
        :meta private:
        """
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
                          'CMCTY': 'Census-merged county (?)',
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
                          'GB': 'Great Britain (?)',
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
                          'PCD': 'Postcode',
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
                          'UK': 'United Kingdom (?)',
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

    
