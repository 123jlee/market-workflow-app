import streamlit as st
import pandas as pd
from services.bigquery_service import BigQueryService
from services.market_data import BinanceService
from logic import calculate_context_primitives, classify_relevance

st.set_page_config(page_title="Market Workflow", layout="wide")

st.title("Market Workflow: Trade Ready (Stage 1)")

# Initialize Services
@st.cache_resource
def get_services():
    return BigQueryService(), BinanceService()

bq_service, binance_service = get_services()

# Sidebar Controls
st.sidebar.header("Configuration")
if st.sidebar.button("Refresh Structure (BigQuery)"):
    bq_service.get_structural_levels.clear()
    st.experimental_rerun()

if st.sidebar.button("Refresh Prices (Binance)"):
    binance_service.get_current_prices.clear()
    st.experimental_rerun()

# 1. Fetch & Process Data
with st.spinner("Loading Context..."):
    # Parallel fetch simulation (Streamlit handles cache)
    structure_df = bq_service.get_structural_levels()
    prices_series = binance_service.get_current_prices()
    
    # Calculate Logic
    context_df = calculate_context_primitives(structure_df, prices_series)
    classified_df = classify_relevance(context_df)

if classified_df.empty:
    st.warning("No data available. Check connections.")
else:
    # Display Bands
    bands = ["Structurally Relevant", "Contextually Watchable", "Structurally Uninteresting"]
    
    for band in bands:
        st.subheader(f"{band}")
        subset = classified_df[classified_df['relevance_band'] == band]
        
        if subset.empty:
            st.info("No markets in this band.")
        else:
            # Display Key Columns
            display_cols = ['current_price', 'weekly_auction_state', 'dw_alignment', 'price_loc_w', 'flags']
            st.dataframe(subset[display_cols].style.format({'current_price': '{:.2f}'}))
