"""
This module is not yet fully implemented and is a work in progress. Please let me know if you would like to contribute.

"""

import pandas as pd
from pathlib import Path
from typing import List, Dict
import duckdb
import networkx as nx


class DatabaseManager:
    """
    A class to manage a DuckDB database, including creating tables from file data
    and querying tables using various join types.

    Attributes:
        db_path (str): Path to the DuckDB database file.
        conn (duckdb.DuckDBPyConnection): Connection to the DuckDB database.

    Methods:
        __init__(db_path: str): Initializes the DatabaseManager with the provided database path.
        create_database(table_paths: Dict[str, Path]): Creates tables in the DuckDB database from CSV or Excel files.
        query_tables_from_path(path: List[str], table_paths: Dict[str, Path], join_type: str = 'left'): Queries multiple tables specified in the path and joins them using the specified join type.
        query_tables_from_graph(graph: nx.DiGraph, join_type: str = 'left'): Queries tables based on a directed graph and joins them using the specified join type.
        query_tables_from_dict(graph: Dict[str, List[str]], join_type: str = 'left'): Queries tables based on a dictionary representation of a graph and joins them using the specified join type.

    Usage:

        .. code-block:: python

            from Consensus.LocalMerger import DatabaseManager
            db_manager = DatabaseManager('path/to/database.db')
            db_manager.create_database({'table1': Path('path/to/table1.csv'), 'table2': Path('path/to/table2.csv')})
            result = db_manager.query_tables_from_path(['table1', 'table2'], {'table1': Path('path/to/table1.csv'), 'table2': Path('path/to/table2.csv')}, 'left')
    """

    def __init__(self, db_path: str):
        """
        Initializes the DatabaseManager with the provided database path.

        Args:
            db_path (str): The path to the DuckDB database.
        """
        self.db_path = db_path
        self.conn = duckdb.connect(database=self.db_path, read_only=False)

    def create_database(self, table_paths: Dict[str, Path]):
        """
        Creates tables in the DuckDB database from CSV or Excel files.

        Args:
            table_paths (Dict[str, Path]): A dictionary mapping table names to file paths.

        This method loads data from the specified file paths and creates tables
        in the database. The file paths must point to CSV or Excel files.
        """
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

    def query_tables_from_path(self, path: List[str], table_paths: Dict[str, Path], join_type: str = 'left') -> pd.DataFrame:
        """
        Queries multiple tables specified in the path and joins them using the specified join type.

        Args:
            path (List[str]): A list of table names to include in the query.
            table_paths (Dict[str, Path]): A dictionary mapping table names to file paths.
            join_type (str): The type of join to perform. Default is 'outer'.

        Returns:
            pd.DataFrame: A DataFrame containing the result of the join operation.

        Raises:
            ValueError: If no valid tables are found in the provided path.
        """
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

    def _join_tables(self, dfs: Dict[str, pd.DataFrame], join_type: str = 'left') -> pd.DataFrame:
        """
        Joins multiple DataFrames using the specified join type.

        Args:
            dfs (Dict[str, pd.DataFrame]): A dictionary of table names to DataFrames to be joined.
            join_type (str): The type of join to perform (e.g., 'inner', 'outer').

        Returns:
            pd.DataFrame: The resulting DataFrame after performing all joins.

        Raises:
            ValueError: If no common columns are found between DataFrames for joining.
        """
        # Initialize result_df with the first DataFrame
        tables = list(dfs.keys())
        if not tables:
            raise ValueError("No tables to join.")

        result_df = dfs[tables[0]]
        for table in tables[1:]:
            df_to_join = dfs[table]
            print(f"Joining with table {table} using {join_type} join")

            # Identify common columns for the join
            common_columns = list(set(result_df.columns) & set(df_to_join.columns))
            if not common_columns:
                raise ValueError(f"No common columns to join on between {result_df.columns} and {df_to_join.columns}")

            join_column = common_columns[0]
            # Perform the left join, adding suffixes to handle duplicate column names
            result_df = result_df.merge(df_to_join, how=join_type, on=join_column, suffixes=('', f'_{table}'))

            print(f"Result after join with {table}:\n", result_df.head())

        return result_df

    def list_all_tables(self) -> List[str]:
        """
        Lists all tables in the database.

        Returns:
            List[str]: A list of table names in the database.
        """
        return [table[0] for table in
                self.conn.execute("SHOW TABLES").fetchall()]

    def close(self) -> None:
        """
        Closes the connection to the DuckDB database.

        Returns:
            None
        """
        self.conn.close()


class GraphBuilder:
    """
    A class to build and manage a graph from CSV and Excel files in a directory.

    This class constructs a graph where nodes are tables and columns, and edges represent
    relationships between them. It provides methods to find paths between tables or columns.

    Attributes:
        directory_path (Path): The path to the directory containing the data files.
        graph (nx.DiGraph): The graph representing the relationships between tables and columns.

    Methods:
        __init__(directory_path: str): Initializes the GraphBuilder with a directory containing CSV and Excel files.
        _build_graph(): Scans the directory for CSV and Excel files and builds the graph.
        _process_csv(file_path: Path): Processes a CSV file and updates the graph with table and column information.
        _process_excel(file_path: Path): Processes an Excel file and updates the graph with table and column information.
        _process_dataframe(df: pd.DataFrame, table_name: str, file_path: Path): Processes a DataFrame and updates the graph with table and column relationships.
        get_table_paths(): Returns a dictionary of table names and their corresponding file paths.
        bfs_paths(start: str, end: str): Finds all paths between the start and end nodes using breadth-first search (BFS).
        find_paths(start: str, end: str, by: str = 'table'): Finds all paths between the start and end nodes, either by table name or column name.
        get_full_graph(): Returns the full graph with all nodes and edges.
        get_all_possible_paths(start: str, end: str, by: str = 'table'): Outputs all possible paths based on start and end, by table or column.
        choose_path(paths: List[List[str]], index: int): Allows the user to choose a path from a list of paths by specifying the index.

    Usage:

        .. code-block:: python

            from Consensus.LocalMerger import GraphBuilder
            graph_builder = GraphBuilder('path/to/directory')
            graph_builder.find_paths('table1', 'table2')
            graph_builder.get_all_possible_paths('table1', 'table2')
    """

    def __init__(self, directory_path: str):
        """
        Initializes the GraphBuilder with a directory containing CSV and Excel files.

        Args:
            directory_path (str): The path to the directory containing the data files.
        """
        self.directory_path = Path(directory_path)
        self.graph = nx.Graph()
        self.table_paths = {}  # Dictionary to store table paths
        self._build_graph()

    def _build_graph(self) -> None:
        """
        Scans the directory for CSV and Excel files and builds the graph.

        This method iterates through all CSV and Excel files in the specified directory,
        processes them, and adds the tables and columns to the graph.

        Returns:
            None
        """
        for file_path in self.directory_path.rglob('*.csv'):
            self._process_csv(file_path)
        for file_path in self.directory_path.rglob('*.xls*'):
            self._process_excel(file_path)

    def _process_csv(self, file_path: Path) -> None:
        """
        Processes a CSV file and updates the graph with table and column information.

        Args:
            file_path (Path): The path to the CSV file to process.

        Returns:
            None
        """
        df = pd.read_csv(file_path)
        self._process_dataframe(df, file_path.stem, file_path)

    def _process_excel(self, file_path: Path) -> None:
        """Processes an Excel file and updates the graph with table and column information.

        Args:
            file_path (Path): The path to the Excel file to process.

        Returns:
            None
        """
        df = pd.read_excel(file_path)
        self._process_dataframe(df, file_path.stem, file_path)

    def _process_dataframe(self, df: pd.DataFrame, table_name: str, file_path: Path) -> None:
        """
        Processes a DataFrame and updates the graph with table and column relationships.

        Args:
            df (pd.DataFrame): The DataFrame containing the table's data.
            table_name (str): The name of the table.
            file_path (Path): The path to the data file.

        Returns:
            None
        """
        df.columns = [col.upper() for col in df.columns]
        self.graph.add_node(table_name, columns=df.columns.tolist())
        self.table_paths[table_name] = file_path  # Store path
        for col in df.columns:
            self.graph.add_node(col)
            self.graph.add_edge(table_name, col)

    def get_table_paths(self) -> Dict[str, Path]:
        """
        Returns a dictionary of table names and their corresponding file paths.

        Returns:
            Dict[str, Path]: A dictionary where the keys are table names and the values are file paths.
        """
        return self.table_paths

    def bfs_paths(self, start: str, end: str) -> List[List[str]]:
        """
        Finds all paths between the start and end nodes using breadth-first search (BFS).

        Args:
            start (str): The starting node.
            end (str): The ending node.

        Returns:
            List[List[str]]: A list of paths from start to end nodes.

        Notes:
            This method finds all simple paths between nodes, not necessarily the shortest.
        """
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

    def find_paths(self, start: str, end: str, by: str = 'table') -> List[List[str]]:
        """
        Finds all paths between the start and end nodes, either by table name or column name.

        Args:
            start (str): The starting node.
            end (str): The ending node.
            by (str): Specifies whether to search by 'table' or 'column'. Defaults to 'table'.

        Returns:
            List[List[str]]: A list of paths between start and end nodes.

        Raises:
            ValueError: If the search type is not supported (e.g., 'column' is used but no columns exist).
        """
        if start not in self.graph or end not in self.graph:
            return []

        if by == 'column':
            columns = {node for node, data in self.graph.nodes(data=True) if 'columns' in data}
            if start not in columns or end not in columns:
                return []
            return self.bfs_paths(start, end)
        else:
            if start not in self.graph.nodes or end not in self.graph.nodes:
                return []
            return self.bfs_paths(start, end)

    def get_full_graph(self) -> nx.Graph:
        """
        Returns the full graph with all nodes and edges.

        Returns:
            nx.Graph: The full graph object containing all nodes and edges.
        """
        return self.graph

    def get_all_possible_paths(self, start: str, end: str, by: str = 'table') -> List[List[str]]:
        """
        Outputs all possible paths based on start and end, by table or column.

        Args:
            start (str): The starting node.
            end (str): The ending node.
            by (str): Specifies whether to search by 'table' or 'column'. Defaults to 'table'.

        Returns:
            List[List[str]]: A list of all possible paths from start to end.
        """
        return self.find_paths(start, end, by)

    def choose_path(self, paths: List[List[str]], index: int) -> List[str]:
        """
        Allows the user to choose a path from a list of paths by specifying the index.

        Args:
            paths (List[List[str]]): A list of possible paths.
            index (int): The index of the chosen path.

        Returns:
            List[str]: The chosen path.

        Raises:
            IndexError: If the provided index is out of range for the list of paths.
        """
        if 0 <= index < len(paths):
            return paths[index]
        else:
            raise IndexError("Path index out of range.")
