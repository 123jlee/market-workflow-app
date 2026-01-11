import os

# Config
PROJECT_ID = "dynamic-sanctum-469401-n3"
DATASET_ID = "core"
TABLE_ID = "levels_final"

# BigQuery
BQ_QUERY_LEVELS = f"""
    SELECT 
        symbol, 
        timeframe, 
        period_start_date, 
        final_poc, 
        final_vah, 
        final_val, 
        va_width_pct, 
        poc_change_pct, 
        value_overlap_pct, 
        coverage_flag
    FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    WHERE period_start_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 21 DAY)
"""

# Binance
BINANCE_BASE_URL = "https://fapi.binance.com"
# PLACEHOLDER: User will update this after running infra/deploy.sh
# Example: "https://europe-west1-dynamic-sanctum-469401-n3.cloudfunctions.net/binance_proxy"
BINANCE_PROXY_URL = os.getenv("BINANCE_PROXY_URL", None)
TIMEFRAMES = ["5m", "15m", "30m", "4h"]

# Data Mode
# Default to True for safety, set to 'false' in Docker for Live
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
