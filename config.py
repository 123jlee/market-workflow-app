import os
from datetime import datetime, timezone

# ============== Project ==============
PROJECT_ID = "dynamic-sanctum-469401-n3"
DATASET_ID = "core"
TABLE_ID = "levels_final"

# ============== Tolerances & Thresholds ==============
TOLERANCE_PCT = 0.20          # 0.2% tolerance for level tests
COMPRESSION_THRESHOLD = 0.015  # 1.5% VA width = compressed
EXTENDED_THRESHOLD = 2.0       # 2% outside value = extended
OVERLAP_BALANCED = 0.70        # >70% overlap = balanced
OVERLAP_TRENDING = 0.30        # <30% overlap = trending

# ============== BigQuery ==============
# Query fetches Weekly rows only with all needed columns
# W-1 and W-2 are derived from prior_final_* columns
BQ_QUERY_WEEKLY_LEVELS = f"""
    SELECT 
        symbol, 
        timeframe, 
        period_start_date, 
        final_poc, 
        final_vah, 
        final_val, 
        prior_final_poc,
        prior_final_vah,
        prior_final_val,
        va_width_pct, 
        poc_change_pct, 
        value_overlap_pct, 
        coverage_flag
    FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    WHERE timeframe = 'W'
      AND period_start_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 21 DAY)
    ORDER BY period_start_date DESC
"""

# ============== Binance ==============
BINANCE_BASE_URL = "https://fapi.binance.com"
BINANCE_PROXY_URL = os.getenv("BINANCE_PROXY_URL", None)
TIMEFRAMES = ["5m", "15m", "30m", "4h"]

# ============== Data Mode ==============
# Default to True for local dev, False in Docker
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "true").lower() == "true"

# ============== Utility ==============
def get_current_utc():
    """Returns current UTC datetime."""
    return datetime.now(timezone.utc)
