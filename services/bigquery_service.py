import pandas as pd
from google.cloud import bigquery
import streamlit as st
import config

class BigQueryService:
    def __init__(self):
        # Streamlit caching for BQ client if needed, or standard init
        self.project_id = config.PROJECT_ID
        
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def get_structural_levels(_self):
        """
        Fetches the authoritative levels_final table.
        Returns a DataFrame indexed by symbol.
        """
        try:
            client = bigquery.Client(project=_self.project_id)
            query = config.BQ_QUERY_LEVELS
            df = client.query(query).to_dataframe()
            return df
        except Exception as e:
            st.error(f"BigQuery Error: {e}")
            return pd.DataFrame()

    def get_active_universe(self):
        """
        Returns a list of symbols that have structural coverage.
        """
        df = self.get_structural_levels()
        if not df.empty:
            return df['symbol'].unique().tolist()
        return []
