import pandas as pd
from google.cloud import bigquery
import config

class BigQueryService:
    def __init__(self):
        self.project_id = config.PROJECT_ID
        self._client = None
        
    @property
    def client(self):
        """Lazy-load BQ client."""
        if self._client is None:
            self._client = bigquery.Client(project=self.project_id)
        return self._client
        
    def get_weekly_levels(self):
        """
        Fetches Weekly levels (W-1 with prior columns for W-2).
        No caching here - controlled by session_state in main.py.
        Returns a DataFrame.
        """
        try:
            query = config.BQ_QUERY_WEEKLY_LEVELS
            df = self.client.query(query).to_dataframe()
            return df
        except Exception as e:
            raise Exception(f"BigQuery Error: {e}")

    def get_active_universe(self):
        """
        Returns a list of symbols that have weekly structural coverage.
        """
        df = self.get_weekly_levels()
        if not df.empty:
            return df['symbol'].unique().tolist()
        return []
