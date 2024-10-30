from typing import List


def where_clause_maker(string_list: List, column_name: str, service_name: str) -> str:
    """
    Create a SQL where clause based on a list of strings and a column name.

    Args:
        string_list (List): A list of strings to include in the where clause.
        column_name (str): The column name to use in the where clause.
        service_name (str): The table name to use in the where clause.

    Returns:
        str: A SQL where clause.
    """
    assert column_name, "No column name provided"
    where_clause = f"{column_name} IN {str(tuple(string_list))}" if len(string_list) > 1 else f"{column_name} IN ('{str(string_list[0])}')"
    print(f"Selecting items based on SQL: {where_clause} in table {service_name}")
    return where_clause
