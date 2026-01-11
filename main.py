import streamlit as st
import pandas as pd
from services.bigquery_service import BigQueryService
from services.market_data import BinanceService
from logic import calculate_context_primitives, classify_relevance, detect_signals, format_ticket

st.set_page_config(page_title="Market Workflow", layout="wide")

# Initialize Services
@st.cache_resource
def get_services():
    return BigQueryService(), BinanceService()

bq_service, binance_service = get_services()

# Sidebar Controls
st.sidebar.header("Configuration")
if st.sidebar.button("Refresh Structure (BigQuery)"):
    bq_service.get_structural_levels.clear()
    st.rerun()

if st.sidebar.button("Refresh Prices (Binance)"):
    binance_service.get_current_prices.clear()
    st.rerun()

# Tabs for Stages
tab1, tab2 = st.tabs(["Stage 1: Trade Ready", "Stage 2: Signals"])

# ========== STAGE 1 ==========
with tab1:
    st.header("Trade Ready")
    
    with st.spinner("Loading Context..."):
        structure_df = bq_service.get_structural_levels()
        prices_series = binance_service.get_current_prices()
        context_df = calculate_context_primitives(structure_df, prices_series)
        classified_df = classify_relevance(context_df)

    if classified_df.empty:
        st.warning("No data available. Check connections.")
    else:
        bands = ["Structurally Relevant", "Contextually Watchable", "Structurally Uninteresting"]
        
        for band in bands:
            st.subheader(f"{band}")
            subset = classified_df[classified_df['relevance_band'] == band]
            
            if subset.empty:
                st.info("No markets in this band.")
            else:
                display_cols = ['current_price', 'weekly_auction_state', 'dw_alignment', 'price_loc_w', 'flags']
                st.dataframe(subset[display_cols].style.format({'current_price': '{:.2f}'}))

# ========== STAGE 2 ==========
with tab2:
    st.header("Signal Engine")
    
    # Only run signals on Relevant markets
    if 'classified_df' in dir() and not classified_df.empty:
        relevant_symbols = classified_df[classified_df['relevance_band'] == 'Structurally Relevant'].index.tolist()
        
        st.write(f"**{len(relevant_symbols)}** markets eligible for signal scan.")
        
        # Store signals in session state
        if 'signals' not in st.session_state:
            st.session_state.signals = []
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🔍 Run Signals", type="primary"):
                st.session_state.signals = []
                progress_bar = st.progress(0)
                
                for i, symbol in enumerate(relevant_symbols):
                    # Fetch klines for this symbol (30m timeframe)
                    klines = binance_service.get_klines(symbol, '30m', limit=50)
                    
                    # Get context row
                    context_row = classified_df.loc[symbol].to_dict()
                    
                    # Detect signals
                    new_signals = detect_signals(symbol, klines, context_row, zscore_threshold=2.5)
                    st.session_state.signals.extend(new_signals)
                    
                    progress_bar.progress((i + 1) / len(relevant_symbols))
                
                progress_bar.empty()
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear Signals"):
                st.session_state.signals = []
                st.rerun()
        
        # Display Signals
        st.subheader("Active Signals")
        if st.session_state.signals:
            signals_df = pd.DataFrame(st.session_state.signals)
            st.dataframe(signals_df)
            
            # Export
            st.subheader("Export")
            export_text = "\n".join([format_ticket(s) for s in st.session_state.signals])
            st.code(export_text, language=None)
            st.download_button(
                label="Download CSV",
                data=signals_df.to_csv(index=False),
                file_name="signals.csv",
                mime="text/csv"
            )
        else:
            st.info("No signals detected. Click 'Run Signals' to scan.")
    else:
        st.warning("Load Stage 1 data first.")
