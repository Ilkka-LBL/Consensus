"""


"""

import pandas as pd
import networkx as nx
from pathlib import Path
from typing import List, Dict, Any, Union
import duckdb
import pandas as pd

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = duckdb.connect(database=self.db_path, read_only=False)
       
    def create_database(self, table_paths):
        for node, path in table_paths.items():
            file_path = str(path)  # Convert Path object to string
            
            if Path(file_path).exists():
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                elif file_path.endswith('.xlsx'):
                    df = pd.read_excel(file_path)
                else:
                    print(f"Unsupported file type: {file_path}")
                    continue
                
                print(f"Loading data from {file_path}")
                print(f"Preview of {node}:\n", df.head())
                
                df.to_sql(node, self.conn, if_exists='replace', index=False)
                print(f"Table {node} created.")
            else:
                print(f"Node {node} does not have a corresponding file path.")

    def query_tables_from_path(self, path, table_paths, join_type='outer'):
        tables = [node for node in path if node in table_paths]
        if not tables:
            raise ValueError("No valid tables found in the provided path.")
        
        # Load data from each table into a dictionary of DataFrames
        dfs = {}
        for table in tables:
            file_path = str(table_paths[table])
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            else:
                print(f"Unsupported file type for table {table}: {file_path}")
                continue
            
            dfs[table] = df
        
        # Perform joins on the DataFrames
        try:
            result_df = self._join_tables(dfs, join_type)
            return result_df
        except Exception as e:
            print(f"Failed to join tables: {e}")
            raise

    def _join_tables(self, dfs, join_type):
        # Initialize result_df with the first DataFrame
        tables = list(dfs.keys())
        if not tables:
            raise ValueError("No tables to join.")
        
        result_df = dfs[tables[0]]
        for table in tables[1:]:
            df_to_join = dfs[table]
            print(f"Joining with table {table} using {join_type} join")
            # Use the first common column of the result_df and df_to_join to perform the join
            common_columns = list(set(result_df.columns) & set(df_to_join.columns))
            if not common_columns:
                raise ValueError(f"No common columns to join on between {result_df.columns} and {df_to_join.columns}")
            
            join_column = common_columns[0]
            result_df = result_df.merge(df_to_join, how=join_type, on=join_column, suffixes=('', f'_{table}'))
            print(f"Result after join with {table}:\n", result_df.head())
        
        return result_df

    def list_all_tables(self):
        return [table[0] for table in self.conn.execute("SHOW TABLES").fetchall()]

    def close(self):
        self.conn.close()





class GraphBuilder:
    def __init__(self, directory_path: str):
        self.directory_path = Path(directory_path)
        self.graph = nx.Graph()
        self.table_paths = {}  # Dictionary to store table paths
        self._build_graph()
    
    def _build_graph(self):
        for file_path in self.directory_path.rglob('*.csv'):
            self._process_csv(file_path)
        for file_path in self.directory_path.rglob('*.xls*'):
            self._process_excel(file_path)
    
    def _process_csv(self, file_path: Path):
        df = pd.read_csv(file_path)
        self._process_dataframe(df, file_path.stem, file_path)
    
    def _process_excel(self, file_path: Path):
        df = pd.read_excel(file_path)
        self._process_dataframe(df, file_path.stem, file_path)
    
    def _process_dataframe(self, df: pd.DataFrame, table_name: str, file_path: Path):
        df.columns = [col.upper() for col in df.columns]
        self.graph.add_node(table_name, columns=df.columns.tolist())
        self.table_paths[table_name] = file_path  # Store path
        for col in df.columns:
            self.graph.add_node(col)
            self.graph.add_edge(table_name, col)
    
    def get_table_paths(self) -> Dict[str, Path]:
        """Returns a dictionary of table names and their corresponding file paths."""
        return self.table_paths
    
    def find_paths(self, start: str, end: str, by: str = 'table') -> List[List[str]]:
        """Find all paths from start to end using BFS. Can be by table name or column name."""
        if start not in self.graph or end not in self.graph:
            return []
        
        def bfs_paths(start, end):
            queue = [[start]]
            paths = []
            while queue:
                path = queue.pop(0)
                node = path[-1]
                if node == end:
                    paths.append(path)
                for neighbor in self.graph.neighbors(node):
                    if neighbor not in path:
                        queue.append(path + [neighbor])
            return paths
        
        if by == 'column':
            columns = {node for node, data in self.graph.nodes(data=True) if 'columns' in data}
            if start not in columns or end not in columns:
                return []
            return bfs_paths(start, end)
        else:
            if start not in self.graph.nodes or end not in self.graph.nodes:
                return []
            return bfs_paths(start, end)
    
    def get_full_graph(self) -> nx.Graph:
        """Returns the full graph with all connections."""
        return self.graph
    
    def get_all_possible_paths(self, start: str, end: str, by: str = 'table') -> List[List[str]]:
        """Outputs all possible paths based on start and end, by table or column."""
        return self.find_paths(start, end, by)
    
    def choose_path(self, paths: List[List[str]], index: int) -> List[str]:
        """Allows the user to choose a path from a list of paths."""
        if 0 <= index < len(paths):
            return paths[index]
        else:
            raise IndexError("Path index out of range.")