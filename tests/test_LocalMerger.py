import unittest
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Consensus.LocalMerger import GraphBuilder, DatabaseManager
from pathlib import Path
import pandas as pd
import duckdb


class TestGraphBuilder(unittest.TestCase):

    @patch("builtins.open", new_callable=MagicMock)  # Mock the open function to simulate reading files
    @patch("pathlib.Path.rglob", return_value=[Path("/mock/path/to/directory/table1.csv"), Path("/mock/path/to/directory/table2.xlsx")])  # Mock the rglob method for both CSV and Excel
    @patch("pandas.read_csv", return_value=pd.DataFrame({"column1": [1, 2], "column2": [3, 4]}))  # Mock pd.read_csv to return a dummy DataFrame
    @patch("pandas.read_excel", return_value=pd.DataFrame({"column1": [1, 2], "column2": [3, 4]}))  # Mock pd.read_excel to return a dummy DataFrame
    def test_build_graph(self, mock_read_excel, mock_read_csv, mock_rglob, mock_open):
        # Mock file contents, assuming the file should return some CSV-like content
        mock_open.return_value.__enter__.return_value = ["column1,column2", "value1,value2", "value3,value4"]

        # Initialize the GraphBuilder with a mock directory path
        builder = GraphBuilder("/mock/path/to/directory")

        # Ensure build_graph or equivalent is called to trigger rglob
        builder._build_graph()  # Call the method that uses rglob to find files

        # Check that rglob was called
        mock_rglob.assert_called()  # Verify rglob was called during graph building

        # Debugging: Print the actual calls to read_csv
        print("Calls to read_csv:", mock_read_csv.call_args_list)

        # Check if pandas read_csv was called with a Path object
        mock_read_csv.assert_any_call(Path("/mock/path/to/directory/table1.csv"))  # Check the correct Path object

        # Check if pandas read_excel was called with a Path object
        mock_read_excel.assert_any_call(Path("/mock/path/to/directory/table2.xlsx"))  # Check the correct Path object

        # Debugging: Print the graph's nodes
        print("Graph nodes:", builder.graph.nodes)  # Inspect the graph structure
    
        # Test: There should be 4 nodes in the graph: two tables and two columns
        self.assertEqual(len(builder.graph.nodes), 4)  # Expected 4 nodes: two tables and two columns

    def test_bfs_paths(self):
        # Arrange
        builder = GraphBuilder(Path("/mock/path/to/directory"))
        builder.graph.add_node("A")
        builder.graph.add_node("B")
        builder.graph.add_edge("A", "B")

        # Act
        paths = builder.bfs_paths("A", "B")

        # Assert
        self.assertEqual(paths, [["A", "B"]])

    def test_find_paths(self):
        # Arrange
        builder = GraphBuilder(Path("/mock/path/to/directory"))
        builder.graph.add_node("A")
        builder.graph.add_node("B")
        builder.graph.add_edge("A", "B")

        # Act
        paths = builder.find_paths("A", "B", by='table')

        # Assert
        self.assertEqual(paths, [["A", "B"]])


class TestDatabaseManager(unittest.TestCase):

    @patch('pandas.DataFrame.to_sql')
    @patch('pandas.read_csv')
    @patch('duckdb.connect')  # Mocking duckdb.connect (not sqlite3.connect)
    def test_create_database(self, mock_connect, mock_read_csv, mock_to_sql):
        # Create mock return values for read_csv and connect
        mock_df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})  # Mocked DataFrame
        mock_conn = MagicMock()  # Mocked database connection
        
        mock_read_csv.return_value = mock_df  # When read_csv is called, return mock_df
        mock_connect.return_value = mock_conn  # When duckdb.connect is called, return mock_conn

        # Create an instance of DatabaseManager
        db_manager = DatabaseManager('path_to_db.db')  # Adjust the database path as needed
        
        # Mock input for create_database method (using the dictionary format expected)
        table_paths = {'table1': Path('path_to_csv.csv'), 'table2': Path('path_to_csv.csv')}
        
        # Call the method you're testing
        db_manager.create_database(table_paths)

        # Print out all calls to to_sql to inspect what arguments were passed
        print("Calls to to_sql:", mock_to_sql.call_args_list)

        # Now assert that to_sql was called with the correct arguments for 'table1'
        mock_to_sql.assert_any_call(mock_df, mock_conn, 'table1', if_exists='replace', index=False)
        mock_to_sql.assert_any_call(mock_df, mock_conn, 'table2', if_exists='replace', index=False)

        # Additional checks: Ensure the mock methods were called correctly
        mock_connect.assert_called_once_with('path_to_db.db')  # Check the connection string
        mock_read_csv.assert_any_call('path_to_csv.csv')  # Check the CSV file path

        # Optionally, check the number of times to_sql was called (one per table)
        self.assertEqual(mock_to_sql.call_count, 2)  # Two tables (table1, table2) should be processed




    @patch("duckdb.connect")
    @patch("pandas.read_csv")
    @patch("pandas.read_excel")
    def test_query_tables_from_path(self, mock_read_excel, mock_read_csv, mock_connect):
        # Mock the connection and methods
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        # Mock DataFrames for the CSV and Excel files
        mock_read_csv.return_value = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        mock_read_excel.return_value = pd.DataFrame({'col1': [1, 2], 'col2': [7, 8]})

        db_manager = DatabaseManager("test_db.duckdb")
        
        # Mock table_paths dictionary
        table_paths = {"table1": Path("test.csv"), "table2": Path("test.xlsx")}
        
        # Act
        path = ["table1", "table2"]  # Example path for testing
        result_df = db_manager.query_tables_from_path(path, table_paths)

        # Debugging prints to check the data loaded
        print("Loaded DataFrame for table1 (CSV):")
        print(mock_read_csv.return_value)
        print("Loaded DataFrame for table2 (Excel):")
        print(mock_read_excel.return_value)

        # Assert the result is as expected
        print("Resulting DataFrame after inner join:")
        print(result_df)
        
        # Assert that the shape is (2, 2), as the join should result in 2 rows and 2 columns.
        # The join is inner by default, and 'col1' should match between both DataFrames.
        self.assertEqual(result_df.shape, (2, 3))

    @patch("duckdb.connect")
    def test_list_all_tables(self, mock_connect):
        # Arrange
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [("table1",), ("table2",)]

        db_manager = DatabaseManager("test_db.duckdb")

        # Act
        tables = db_manager.list_all_tables()

        # Assert
        self.assertEqual(tables, ["table1", "table2"])

    @patch("duckdb.connect")
    def test_close(self, mock_connect):
        # Arrange
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        db_manager = DatabaseManager("test_db.duckdb")

        # Act
        db_manager.close()

        # Assert
        mock_conn.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
