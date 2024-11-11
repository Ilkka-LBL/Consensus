from pathlib import Path
import pandas as pd
import hmac
import hashlib
import base64
import requests
from typing import Dict, Any, List
import multiprocessing as mp
import more_itertools
from Consensus.config_utils import load_config

JSONDict = Dict[str, Any]


class LGInform:

    """
    The class takes a dictionary of LG Inform datasets (such as {'IMD_2010': 841, 'IMD_2009': 842, 'Death_of_enterprises': 102}), finds all metrics, downloads the data, and merges them into one. The dictionary keys can be any string of your choosing, but the integer values must be one of https://webservices.esd.org.uk/datasets?ApplicationKey=ExamplePPK&Signature=YChwR9HU0Vbg8KZ5ezdGZt+EyL4=
    The main method to download data for multiple datasets is the ``mp_download()`` method, which uses multiprocessing to download data from multiple datasets simultaneously. However, this requires that the class is called within ``if __name__ == '__main__'``.
    If multiprocessing is not necessary, it's better to use ``download()`` method, which is what the multiprocessing wrapper method also calls.

    Attributes:
        api_key (str): Application Key to LG Inform Plus.
        api_secret (str): Application Secret to LG Inform Plus.
        proxies (Dict[str, str]): Proxy address if known.
        area (str): A comma separated string of areas, excluding whitespace. You can either use GSS codes or use LG Inform's off-the-shelf groups for areas. For instance, Lewisham GSS code is E09000023 and it's CIPFA nearest neighbours is called Lewisham_CIPFA_Near_Neighbours. Together these would be input as 'E09000023,Lewisham_CIPFA_Near_Neighbours'.

    Methods:
        json_to_pandas(json_data: JSONDict): Transform downloaded json data to Pandas dataframe.
        sign_url(url: str): Sign all url calls with your unique secret and key.
        download_variable_data(identifier: int, latest_n: int): Download data for a given metricType, area, and period.
        download_data_for_many_variables(variables: JSONDict, latest_n: int = 20, arraytype: str = 'metricType-array'): Download the variables for an array of metricTypes.
        get_dataset_table_variables(dataset: int): Given a dataset, output all the metricType numbers (dataset columns).
        format_tables(outputs: List[JSONDict], drop_discontinued: bool = True): Format the data for each variable and create a metadata table.
        merge_tables(dataset_name: str): Merge the variables to form a table for a given dataset.
        download(datasets: Dict[str, int], output_folder: Path, latest_n: int = 5, drop_discontinued: bool = True): Download data for one or more datasets.
        mp_download(datasets: Dict[str, int], output_folder: Path, latest_n: int = 20, drop_discontinued: bool = True, max_workers: int = 8): Multiprocessing wrapper to download data for multiple datasets simultaneously.

    Usage:

        .. code-block:: python

            from Consensus.LGInform import LGInform
            from Consensus.ConfigManager import ConfigManager
            from dotenv import load_dotenv
            from os import environ
            from pathlib import Path
            dotenv_path = Path('.env')
            load_dotenv(dotenv_path)


            lg_key = environ.get("LG_KEY")  # public key to LG Inform Plus
            lg_secret = environ.get("LG_SECRET")  # secret to LG Inform Plus
            conf = ConfigManager()  # Use ConfigManager to save environment variables and proxy address if you want the information to be stored with this package
            conf.update_config("lg_inform_key", lg_key)
            conf.update_config("lg_inform_secret", lg_secret)
            out_folder = Path('./data/mp_test/')  # folder to store final data
            datasets = {'IMD_2010': 841, 'IMD_2009': 842, 'Death_of_enterprises': 102}  # a dictionary of datasets. The key can be any string, but the integer value must be an identifier from https://webservices.esd.org.uk/datasets?ApplicationKey=ExamplePPK&Signature=YChwR9HU0Vbg8KZ5ezdGZt+EyL4=

            if __name__ '__main__':  # when using the multiprocessing wrapper method, you have to run it under if __name__ '__main__' statement.
                api_call = LGInform(area='E09000023,Lewisham_CIPFA_Near_Neighbours')
                #api_call.download(datasets=datasets, output_folder=out_folder, latest_n=20, drop_discontinued=False)  # normal, single threaded download
                api_call.mp_download(datasets, output_folder=out_folder, latest_n=20, drop_discontinued=False, max_workers=8)
    """

    def __init__(self, api_key: str = None, api_secret: str = None, proxies: Dict[str, str] = {}, area: str = 'E09000023,Lewisham_CIPFA_Near_Neighbours') -> None:
        """
        Initialise the class with API key, secret, and proxy address.

        Args:
            api_key (str): Application Key to LG Inform Plus.
            api_secret (str): Application Secret to LG Inform Plus.
            proxies (Dict[str, str]): Proxy address if known.
            area (str): A comma separated string of areas, excluding whitespace. You can either use GSS codes or use LG Inform's off-the-shelf groups for areas. For instance, Lewisham GSS code is E09000023 and it's CIPFA nearest neighbours is called Lewisham_CIPFA_Near_Neighbours. Together these would be input as 'E09000023,Lewisham_CIPFA_Near_Neighbours'.

        Returns:
            None
        """
        mp.set_start_method('spawn')

        self.config = load_config()
        self.api_key = api_key or self.config.get('lg_inform_key', None).strip()
        self.api_secret = api_secret or self.config.get('lg_inform_secret', None).strip()
        self.proxies = proxies or self.config.get('proxies', {})

        assert self.api_key, 'Please provide Application Key to LG Inform Plus - if using ContextManager, name variable as "lg_inform_key"'
        assert self.api_secret, 'Please provide Application Secret to LG Inform Plus - if using ContextManager, name variable as "lg_inform_secret"'

        self.area = area

        self.base_url = "https://webservices.esd.org.uk"

    def json_to_pandas(self, json_data: JSONDict) -> pd.DataFrame:
        """
        Transform downloaded json data to Pandas.

        Args:
            json_data (JSONDict): JSON data to transform.

        Returns:
            pd.DataFrame: Downloaded data as Pandas dataframe.
        """

        column_names = [col['period']['label'] for col in json_data['columns']]
        data = {i['area']['label']: [val['formatted'] for val in i['values']] for i in json_data['rows']}
        return pd.DataFrame.from_dict(data, orient='index', columns=column_names)

    def sign_url(self, url: str) -> str:
        """
        Each url needs to be signed.

        Args:
            url (str): URL to be signed.

        Returns:
            str: Signed URL.
        """
        url = url + 'ApplicationKey=' + self.api_key
        byteSecret = bytes(self.api_secret, 'utf-8')
        digest = hmac.digest(byteSecret, bytes(url, 'utf-8'), hashlib.sha1)
        signature = base64.b64encode(digest).decode('UTF-8')
        signature = '&Signature=' + signature
        url = url + signature
        return url

    def download_variable_data(self, identifier: int, latest_n: int) -> JSONDict:
        """
        Download data for a given metricType, area, and period (latest n periods).

        Args:
            identifier (int): metricType integer.
            latest_n (int): Latest n periods. Period could be year, quarter, month, week, or some other period such as the latest n publications.

        Returns:
            JSONDict: Downloaded data as JSON.
        """

        url = f"{self.base_url}/data?value.valueType=raw&metricType={str(identifier)}&area={str(self.area)}&period=latest{str(latest_n)}&rowGrouping=area&"
        data_url = self.sign_url(url)
        output = requests.get(data_url).json()
        return output

    def download_data_for_many_variables(self, variables: JSONDict, latest_n: int = 20, arraytype: str = 'metricType-array') -> List[JSONDict]:
        """
        Download the variables for an array of metricTypes using download_variable_data method.

        Args:
            variables (JSONDict): variables JSON from get_dataset_table_variables method.
            latest_n (int): Latest n periods. Period could be year, quarter, month, week, or some other period such as the latest n publications.
            arraytype (str): Type of variables to download. Default is metricType-array.

        Returns:
            List[JSONDict]: A list of JSON variables.
        """

        outputs = []
        for variable in variables[arraytype]:
            identifier = variable['identifier']
            output = self.download_variable_data(identifier, latest_n)
            outputs.append(output)
        return outputs

    def get_dataset_table_variables(self, dataset: int) -> JSONDict:
        """
        Given a dataset, output all the metricType numbers (dataset columns). The output dictionary is a JSON.

        Args:
            dataset (int): The number of the dataset from https://webservices.esd.org.uk/datasets?ApplicationKey=ExamplePPK&Signature=YChwR9HU0Vbg8KZ5ezdGZt+EyL4=

        Returns:
            JSONDict:  A JSON dictionary object
        """

        url = f'{self.base_url}/metricTypes?dataset={str(dataset)}&'
        data_url = self.sign_url(url)
        variables = requests.get(data_url, proxies=self.proxies).json()
        return variables

    def format_tables(self, outputs: List[JSONDict], drop_discontinued: bool = True) -> None:
        """
        Format the data for each variable and create a metadata table.

        Args:
            outputs (List[JSONDict]): A list of JSONDict objects.
            drop_discontinued (bool): Boolean to select whether to include discontinued metrics.

        Returns:
            None
        """

        table_headers = {'MetricType': [], 'Column name': [], 'Original table name': [], 'Alternative table name(s)': [], 'Short label': [], 'Discontinued': [], 'Metric help text': [], 'Notes': []}
        tables_excluded = 0
        for download in outputs:
            if download['columns']:
                metrictype_identifier = download['columns'][0]['metricType']['identifier']
                table_name = download['columns'][0]['metricType']['label']

                try:
                    dl_df = self.json_to_pandas(download)
                    dl_df.reset_index(inplace=True, names=['Area'])

                    df_melt = pd.melt(dl_df, id_vars=['Area'], value_vars=dl_df.columns, var_name='Time period', value_name=table_name)

                    # check if data is discontinued:
                    metric_data = f"{self.base_url}/metricTypes/{metrictype_identifier}?"
                    metadata_url = self.sign_url(metric_data)
                    meta_data = requests.get(metadata_url).json()
                    is_discontinued = meta_data['metricType']['discontinued']

                    if is_discontinued and drop_discontinued:
                        continue
                    else:
                        table_headers['Discontinued'].append(is_discontinued)
                        help_text = meta_data['metricType']['helpText']
                        table_headers['Metric help text'].append(help_text)
                        try:
                            table_name_original = meta_data['metricType']['originalLabel']
                            table_headers['Original table name'].append(table_name_original)
                        except KeyError:
                            table_headers['Original table name'].append('')

                        try:
                            table_name_alt_names = meta_data['metricType']['alternativeLabels']
                            table_headers['Alternative table name(s)'].append(table_name_alt_names)
                        except KeyError:
                            table_headers['Alternative table name(s)'].append('')
                        try:
                            table_label = meta_data['metricType']['label']
                            table_headers['Short label'].append(table_label)
                        except KeyError:
                            table_headers['Short label'].append('')

                        table_headers['Column name'].append(table_name)
                        table_headers['MetricType'].append(metrictype_identifier)
                        table_headers['Notes'].append('')
                        df_melt.to_csv(self.raw_data_folder.joinpath(f"table for metricType {metrictype_identifier}.csv"), index=False)

                except TypeError:
                    table_headers['MetricType'].append(metrictype_identifier)
                    table_headers['Column name'].append(table_name)
                    table_headers['Original table name'].append('')
                    table_headers['Alternative table name(s)'].append('')
                    table_headers['Short label'].append('')
                    table_headers['Discontinued'].append('')
                    table_headers['Metric help text'].append('help_text')
                    table_headers['Notes'].append('TypeError, data omitted from final dataset')
                    print('Error with table', table_name)
                    tables_excluded += 1

        table_name_lookup = pd.DataFrame.from_dict(table_headers)
        table_name_lookup.to_csv(self.dataset_specific_output_folder.joinpath('metadata.csv'))
        print(f'Finished formatting table for dataset {self.dataset_key}, number of columns dropped due to errors: {tables_excluded}')

    def merge_tables(self, dataset_name: str) -> pd.DataFrame:
        """
        Merge the variables to form a table for a given dataset.

        Args:
            dataset_name (str): Dataset name string.

        Returns:
            pd.DataFrame: All variables of the dataset merged as one Pandas dataframe.
        """
        all_tables = [i for i in self.raw_data_folder.glob("*.csv")]
        try:
            df = pd.read_csv(all_tables[0])

            for i in all_tables[1:]:
                df_to_merge = pd.read_csv(i)
                df = df.merge(df_to_merge, how='left', on=['Area', 'Time period'])

            df.to_csv(self.dataset_specific_output_folder.joinpath(f'data for dataset {dataset_name}.csv'), index=False)
            return df
        except IndexError:
            print(f"No data found in {self.raw_data_folder}. Maybe the variables are discontinued? Try changing drop_discontinued parameter to False.")
            return None

    def download(self, datasets: Dict[str, int], output_folder: Path, latest_n: int = 5, drop_discontinued: bool = True) -> None:
        """
        Download all variables for many datasets, merging the variables to one table by area and time period.

        Args:

            datasets (Dict[str,int]): Dictionary of format {"some_name": some_integer}', where the integer value is an identifier from https://webservices.esd.org.uk/datasets?ApplicationKey=ExamplePPK&Signature=YChwR9HU0Vbg8KZ5ezdGZt+EyL4=
            latest_n (int): The period is currently restricted to using the latest n periods. This means that the period can be years, quarters, months, weeks or some other period (e.g. for Indices of Multiple Deprivation, the period refers to publications so that latest_n=2 would get data for 2019 and 2015).
            drop_discontinued (bool): If you set this to False, the downloaded data will include discontinued metrics. Default is True.

        Returns:
            None
        """
        assert output_folder, 'Please provide a storage location for merged data'

        if not output_folder.exists():
            output_folder.mkdir(parents=True)

        assert isinstance(datasets, dict), 'Please make sure "datasets" variable is a dictionary of format {"some_name": some_int}'

        for dataset_key, d in datasets.items():
            print(f"Starting download for {dataset_key}")
            self.dataset_key = dataset_key
            dataset_specific_output_folder = output_folder.joinpath(f"{self.dataset_key}")
            self.dataset_specific_output_folder = dataset_specific_output_folder
            self.raw_data_folder = self.dataset_specific_output_folder.joinpath('raw_data')
            if not self.raw_data_folder.exists():
                self.raw_data_folder.mkdir(parents=True)
            variables = self.get_dataset_table_variables(d)
            output = self.download_data_for_many_variables(variables, latest_n=latest_n)
            self.format_tables(output, drop_discontinued=drop_discontinued)
            merged_df = self.merge_tables(self.dataset_key)
            if merged_df is not None:
                print(f"Dataset {dataset_key} downloaded, merged, and stored in {self.dataset_specific_output_folder}")

    def _multiprocessing_wrapper(self, input_queue: mp.Queue) -> None:
        """
        This is just the same as download() method, but wrapped to be used with multiprocessing library.

        Args:
            input_queue (mp.Queue): A multiprocessing queue.

        Returns:
            None
        """
        args = input_queue.get()
        (datasets, latest_n, drop_discontinued) = args
        self.download(datasets, latest_n, drop_discontinued)

    def mp_download(self, datasets: Dict[str, int], output_folder: Path, latest_n: int = 20, drop_discontinued: bool = True, max_workers: int = 8) -> None:
        """
        Multiprocessing method for downloading data for multiple datasets. Use max_workers to split the dataset dictionary to chunks of size max_workers.

        Args:
            datasets (Dict[str,int]): Dictionary of format {"some_name": some_integer}', where the integer value is an identifier from https://webservices.esd.org.uk/datasets?ApplicationKey=ExamplePPK&Signature=YChwR9HU0Vbg8KZ5ezdGZt+EyL4=
            latest_n (int): The period is currently restricted to using the latest n periods. This means that the period can be years, quarters, months, weeks or some other period (e.g. for Indices of Multiple Deprivation, the period refers to publications so that latest_n=2 would get data for 2019 and 2015).
            drop_discontinued (bool): If you set this to False, the downloaded data will include discontinued metrics. Default is True.
            max_workers (int): Set the number of workers for multiprocessing. Typically this would be the number of logical CPUs in your system. This will also process the datasets in chunks, so that if you list 16 datasets in your datasets dictionary and have 8 workers, the script will work through the datasets in two steps (16/8 = 2).

        Returns:
            None
        """
        sliding_dataset = more_itertools.windowed([{i: k} for i, k in datasets.items()], n=max_workers, step=max_workers)

        for enum, subset in enumerate(sliding_dataset):
            print(f"Step {enum + 1} of {round(len(datasets) / max_workers) + 1}")
            new_subset = [item for item in subset if item is not None]

            print(f"Employing workers {1 + max_workers * enum} to {max_workers + max_workers * enum}")
            q = mp.Queue()
            workers = []

            for data_set in new_subset:
                q.put((data_set, output_folder, latest_n, drop_discontinued))

            for i in range(len(new_subset)):
                p = mp.Process(target=self._multiprocessing_wrapper, args=(q,))
                workers.append(p)
                p.start()

            for w in workers:
                q.put(None)

            # Wait for workers to quit.
            for w in workers:
                w.join()

            print(f"Completed step {enum + 1}")

        print('Done')
