Note that the below documentation was created using ChatGPT 4.o and may therefore not be entirely accurate. Please report any mistakes. 

---


# LGInform Documentation

## Overview

The `LGInform` class is designed to interact with the LG Inform Plus API, allowing users to download and merge data from multiple datasets. This class is capable of handling both single-threaded and multi-threaded data downloads, making it flexible for different use cases. It is particularly useful for downloading data related to specific areas, such as those defined by GSS codes or pre-defined area groups.

## Class: LGInform

### Purpose

The `LGInform` class facilitates the process of downloading data from LG Inform Plus datasets. It enables users to sign API requests, download multiple datasets, and merge the resulting data into a unified format.

### Arguments

- **`key`**: `str`
  - The public API key for LG Inform Plus.
  
- **`secret`**: `str`
  - The secret key associated with the public API key.

- **`output_folder`**: `Path`
  - The directory where the downloaded and merged data will be stored.

- **`area`**: `str`
  - A comma-separated string of area codes or groups, excluding whitespace. For example, `E09000023,Lewisham_CIPFA_Near_Neighbours`.

### Methods

#### `json_to_pandas(json_data: JSONDict) -> pd.DataFrame`

Transforms downloaded JSON data into a Pandas DataFrame.

- **Arguments**:
  - `json_data`: JSON data to transform.

- **Returns**:
  - `pd.DataFrame`: The transformed data as a Pandas DataFrame.

#### `sign_url(url: str) -> str`

Signs the URL with the user's API key and secret to authorize the request.

- **Arguments**:
  - `url`: The URL to be signed.

- **Returns**:
  - `str`: The signed URL.

#### `download_variable_data(identifier: int, latest_n: int) -> JSONDict`

Downloads data for a specific metric type, area, and period (latest `n` periods).

- **Arguments**:
  - `identifier`: The metric type identifier (an integer).
  - `latest_n`: The number of latest periods to retrieve data for.

- **Returns**:
  - `JSONDict`: The downloaded data as a JSON object.

#### `download_data_for_many_variables(variables: JSONDict, latest_n: int = 20, arraytype: str = 'metricType-array') -> List[JSONDict]`

Downloads data for an array of metric types.

- **Arguments**:
  - `variables`: A JSON dictionary containing the variables to download.
  - `latest_n`: The number of latest periods to retrieve data for.
  - `arraytype`: The type of variables to download (default is 'metricType-array').

- **Returns**:
  - `List[JSONDict]`: A list of JSON objects containing the downloaded variables.

#### `get_dataset_table_variables(dataset: int) -> JSONDict`

Retrieves all metric type numbers (dataset columns) for a given dataset.

- **Arguments**:
  - `dataset`: The dataset identifier.

- **Returns**:
  - `JSONDict`: A JSON dictionary containing the dataset variables.

#### `format_tables(outputs: List[JSONDict], drop_discontinued: bool = True) -> None`

Formats the downloaded data for each variable and creates a metadata table.

- **Arguments**:
  - `outputs`: A list of JSON objects containing the downloaded variables.
  - `drop_discontinued`: If set to `True`, discontinued metrics are excluded from the final dataset (default is `True`).

#### `merge_tables(dataset_name: str) -> pd.DataFrame`

Merges the variables into a single table for a given dataset.

- **Arguments**:
  - `dataset_name`: The name of the dataset.

- **Returns**:
  - `pd.DataFrame`: The merged dataset as a Pandas DataFrame.

#### `data_from_datasets(datasets: Dict[str, int], latest_n: int = 5, drop_discontinued: bool = True) -> None`

Downloads and merges data for multiple datasets.

- **Arguments**:
  - `datasets`: A dictionary where keys are dataset names and values are dataset identifiers.
  - `latest_n`: The number of latest periods to retrieve data for.
  - `drop_discontinued`: If set to `True`, discontinued metrics are excluded from the final dataset (default is `True`).

#### `mp_data_from_datasets(datasets: Dict[str, int], latest_n: int = 20, drop_discontinued: bool = True, max_workers: int = 8) -> None`

A multiprocessing method for downloading data from multiple datasets simultaneously.

- **Arguments**:
  - `datasets`: A dictionary where keys are dataset names and values are dataset identifiers.
  - `latest_n`: The number of latest periods to retrieve data for.
  - `drop_discontinued`: If set to `True`, discontinued metrics are excluded from the final dataset (default is `True`).
  - `max_workers`: The number of worker processes to use for multiprocessing.

### Usage Example

```python
from LBLDataAccess.LGInform import LGInform
from dotenv import load_dotenv
from os import environ
from pathlib import Path

# Load environment variables
dotenv_path = Path('.env')
load_dotenv(dotenv_path)

# Initialize API keys and output folder
lg_key = environ.get("LG_KEY")  # Public key to LG Inform Plus
lg_secret = environ.get("LG_SECRET")  # Secret key to LG Inform Plus
out_folder = Path('./data/mp_test/')  # Folder to store final data

# Define datasets to download
datasets = {'IMD_2010': 841, 'IMD_2009': 842, 'Death_of_enterprises': 102}

if __name__ == '__main__':
    # Initialize the LGInform object
    api_call = LGInform(key=lg_key, secret=lg_secret, output_folder=out_folder, area='E09000023,Lewisham_CIPFA_Near_Neighbours')

    # Download data using multiprocessing
    api_call.mp_data_from_datasets(datasets, latest_n=20, drop_discontinued=False, max_workers=8)
```

### Notes

- When using the `mp_data_from_datasets` method, ensure the code runs within an `if __name__ == '__main__':` block to avoid issues with multiprocessing on some platforms.
- You can adjust the `max_workers` parameter to match the number of logical CPUs in your system for optimal performance.
- Use the `drop_discontinued` parameter to control whether discontinued metrics should be included in the final dataset.

### References

- [LG Inform Plus API Documentation](https://webservices.esd.org.uk/datasets?ApplicationKey=ExamplePPK&Signature=YChwR9HU0Vbg8KZ5ezdGZt+EyL4=)