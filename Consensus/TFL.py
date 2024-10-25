from Consensus.EsriConnector import EsriConnector


class TFL(EsriConnector):
    """
    Uses EsriConnector class to connect to TfL Open Data Hub.
    """
    def __init__(self, max_retries: int = 10, retry_delay: int = 2) -> None:
        """
        Initialise class.

        Returns:
            None

        :meta private:
        """
        super().__init__(max_retries, retry_delay)
        self.base_url = "https://services1.arcgis.com/YswvgzOodUvqkoCN/ArcGIS/rest/services?f=json"
        print("Connecting to TfL Open Data Hub")
