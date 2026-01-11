"""
Market Workflow App - Main Entry Point
Stage 1: Trade Ready | Stage 2: Signals
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from services.bigquery_service import BigQueryService
from services.market_data import BinanceService
from logic import calculate_trade_ready_context, classify_relevance, detect_signals, format_ticket
import config

st.set_page_config(page_title="Market Workflow", layout="wide")

# ============== Initialize Services ==============
@st.cache_resource
def get_services():
    return BigQueryService(), BinanceService()

bq_service, binance_service = get_services()

# ============== Session State Initialization ==============
if 'trade_ready_df' not in st.session_state:
    st.session_state.trade_ready_df = None
if 'refresh_timestamp' not in st.session_state:
    st.session_state.refresh_timestamp = None
if 'signals' not in st.session_state:
    st.session_state.signals = []

# ============== Sidebar ==============
st.sidebar.header("Configuration")

# Time anchor display
now_utc = config.get_current_utc()
st.sidebar.caption(f"📅 Session time: {now_utc.strftime('%Y-%m-%d %H:%M')} UTC")

# Last refreshed
if st.session_state.refresh_timestamp:
    st.sidebar.caption(f"🔄 Last refreshed: {st.session_state.refresh_timestamp.strftime('%Y-%m-%d %H:%M')} UTC")
else:
    st.sidebar.caption("🔄 No data loaded yet")

# Developing Week Toggle
include_dev = st.sidebar.checkbox("Include Developing Week (W-0)", value=False)

# Refresh button
if st.sidebar.button("🔄 Refresh Snapshot", type="primary"):
    with st.spinner("Loading data..."):
        try:
            weekly_df = bq_service.get_weekly_levels()
            prices_series = binance_service.get_current_prices()
            context_df = calculate_trade_ready_context(weekly_df, prices_series, include_developing=include_dev)
            classified_df = classify_relevance(context_df)
            st.session_state.trade_ready_df = classified_df
            st.session_state.refresh_timestamp = config.get_current_utc()
            st.rerun()
        except Exception as e:
            st.error(f"Error refreshing data: {e}")

st.sidebar.divider()

# ============== Tabs ==============
tab1, tab2 = st.tabs(["Stage 1: Trade Ready", "Stage 2: Signals"])

# ============== STAGE 1: Trade Ready ==============
with tab1:
    st.header("Trade Ready")
    
    df = st.session_state.trade_ready_df
    
    if df is None or df.empty:
        st.info("No data loaded. Click **Refresh Snapshot** in the sidebar to load.")
    else:
        # ============== Filters ==============
        with st.expander("🔍 Filters", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                regime_filter = st.multiselect(
                    "Regime (W-1)",
                    options=['BALANCED', 'TRENDING', 'TRANSITIONAL'],
                    default=['BALANCED', 'TRENDING', 'TRANSITIONAL']
                )
            with col2:
                htf_filter = st.multiselect(
                    "HTF Direction",
                    options=['UP', 'DOWN', 'NEUTRAL'],
                    default=['UP', 'DOWN', 'NEUTRAL']
                )
            with col3:
                interaction_filter = st.multiselect(
                    "Interaction",
                    options=['TEST_POC', 'TEST_VAL', 'TEST_VAH', 'INSIDE_VALUE', 'BELOW_VALUE', 'ABOVE_VALUE'],
                    default=['TEST_POC', 'TEST_VAL', 'TEST_VAH', 'INSIDE_VALUE', 'BELOW_VALUE', 'ABOVE_VALUE']
                )
            with col4:
                bias_filter = st.multiselect(
                    "Bias",
                    options=['FAVORS_LONG', 'FAVORS_SHORT', 'NEUTRAL_WAIT'],
                    default=['FAVORS_LONG', 'FAVORS_SHORT', 'NEUTRAL_WAIT']
                )
            
            col5, col6 = st.columns(2)
            with col5:
                symbol_search = st.text_input("Symbol Search", placeholder="e.g., BTC")
            with col6:
                warning_filter = st.multiselect(
                    "Warnings (include any)",
                    options=['LOW_CONFIDENCE', 'COMPRESSED', 'PINNED', 'EXTENDED', 'DEVELOPING'],
                    default=[]
                )
        
        # Apply filters
        filtered_df = df.copy()
        filtered_df = filtered_df[filtered_df['regime_w1'].isin(regime_filter)]
        filtered_df = filtered_df[filtered_df['htf_dir_w1'].isin(htf_filter)]
        filtered_df = filtered_df[filtered_df['now_interaction_w1'].isin(interaction_filter)]
        filtered_df = filtered_df[filtered_df['bias_compatibility'].isin(bias_filter)]
        
        if symbol_search:
            filtered_df = filtered_df[filtered_df.index.str.contains(symbol_search.upper())]
        
        if warning_filter:
            filtered_df = filtered_df[filtered_df['warnings'].apply(
                lambda w: any(tag in w for tag in warning_filter)
            )]
        
        # ============== Display Columns ==============
        display_cols = [
            'price', 'regime_w1', 'htf_dir_w1', 'now_interaction_w1',
            'bias_compatibility', 'pct_to_w_val', 'pct_to_w_poc', 'pct_to_w_vah', 'warnings'
        ]
        
        # ============== Bands ==============
        bands = ["Trade Ready", "Watch", "Ignore for Now"]
        
        for band in bands:
            st.subheader(f"{band}")
            subset = filtered_df[filtered_df['relevance_band'] == band]
            
            if subset.empty:
                st.caption("No markets in this band.")
            else:
                # Sort: bias (FAVORS_* first), then nearest level, then alpha
                subset = subset.copy()
                subset['_bias_sort'] = subset['bias_compatibility'].map({
                    'FAVORS_LONG': 0, 'FAVORS_SHORT': 0, 'NEUTRAL_WAIT': 1
                })
                subset['_nearest_level'] = subset[['pct_to_w_val', 'pct_to_w_poc', 'pct_to_w_vah']].abs().min(axis=1)
                subset = subset.sort_values(['_bias_sort', '_nearest_level', subset.index.name or 'symbol_clean'])
                
                # Format warnings for display
                subset_display = subset[display_cols].copy()
                subset_display['warnings'] = subset_display['warnings'].apply(
                    lambda w: ', '.join(w) if w else ''
                )
                
                st.dataframe(
                    subset_display.style.format({
                        'price': '{:.2f}',
                        'pct_to_w_val': '{:.2f}%',
                        'pct_to_w_poc': '{:.2f}%',
                        'pct_to_w_vah': '{:.2f}%'
                    }),
                    use_container_width=True
                )
        
        # ============== CSV Export ==============
        st.divider()
        export_df = filtered_df[display_cols].copy()
        export_df['warnings'] = export_df['warnings'].apply(lambda w: ', '.join(w) if w else '')
        export_df['refreshed_at'] = st.session_state.refresh_timestamp.strftime('%Y-%m-%d %H:%M UTC') if st.session_state.refresh_timestamp else ''
        export_df = export_df.reset_index()
        
        timestamp_str = st.session_state.refresh_timestamp.strftime('%Y-%m-%d_%H%M') if st.session_state.refresh_timestamp else 'export'
        
        st.download_button(
            label="📥 Download CSV",
            data=export_df.to_csv(index=False),
            file_name=f"trade_ready_{timestamp_str}.csv",
            mime="text/csv"
        )

# ============== STAGE 2: Signals ==============
with tab2:
    st.header("Signal Engine")
    
    df = st.session_state.trade_ready_df
    
    if df is None or df.empty:
        st.warning("Load Stage 1 data first (click Refresh Snapshot in sidebar).")
    else:
        relevant_symbols = df[df['relevance_band'] == 'Trade Ready'].index.tolist()
        
        st.write(f"**{len(relevant_symbols)}** markets eligible for signal scan.")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🔍 Run Signals", type="primary"):
                st.session_state.signals = []
                progress_bar = st.progress(0)
                
                for i, symbol in enumerate(relevant_symbols):
                    klines = binance_service.get_klines(symbol, '30m', limit=50)
                    context_row = df.loc[symbol].to_dict()
                    new_signals = detect_signals(symbol, klines, context_row, zscore_threshold=2.5)
                    st.session_state.signals.extend(new_signals)
                    progress_bar.progress((i + 1) / len(relevant_symbols))
                
                progress_bar.empty()
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear Signals"):
                st.session_state.signals = []
                st.rerun()
        
        st.subheader("Active Signals")
        if st.session_state.signals:
            signals_df = pd.DataFrame(st.session_state.signals)
            st.dataframe(signals_df)
            
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
