from pathlib import Path
from LBLDataAccess.LocalMerger import DatabaseManager, GraphBuilder

# Initialize GraphBuilder and build the graph
graph_builder = GraphBuilder(r'C:\Users\isipila\OneDrive - Lewisham Council\Documents\Github\LBLDataAccess\Tests')
full_graph = graph_builder.get_full_graph()
table_paths = graph_builder.get_table_paths()
print("Table Paths:", table_paths)

# Initialize DatabaseManager with the database path
db_manager = DatabaseManager(db_path=r'C:\Users\isipila\OneDrive - Lewisham Council\Documents\Github\LBLDataAccess\Tests\data.duckdb')

# Create the database using the graph
db_manager.create_database(table_paths)

print("Tables in the Database:")
print(db_manager.list_all_tables())

# Find paths using GraphBuilder
paths = graph_builder.get_all_possible_paths('Boo2', 'Book1', by='table')

print("Paths:", paths)

# Choose a path
chosen_path = graph_builder.choose_path(paths, index=0)
print("Chosen Path:", chosen_path)

# Query the database based on the chosen path with outer join
try:
    result_df = db_manager.query_tables_from_path(chosen_path, table_paths, join_type='outer')
    print(result_df)
except ValueError as e:
    print(f"Error: {e}")

# Close the database connection
db_manager.close()

