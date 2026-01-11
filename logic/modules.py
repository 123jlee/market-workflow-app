"""
Stage 1 Logic: Trade Ready Context Calculation

Pure functions for computing:
- Weekly regime (W-1)
- HTF direction (W-1 vs W-2)
- Price interaction tags
- Bias compatibility
- Warnings
- % distances to levels
"""
import pandas as pd
import numpy as np
import config


def calculate_trade_ready_context(weekly_df, current_prices):
    """
    Master function: Transforms raw weekly BQ data + Binance prices into
    a trader-readable context DataFrame.
    
    Inputs:
    - weekly_df: DataFrame from BQ with W-1 weekly rows (includes prior_final_* for W-2)
    - current_prices: Series {symbol: price} from Binance
    
    Output:
    - DataFrame with one row per symbol, all new columns
    """
    if weekly_df.empty:
        return pd.DataFrame()
    
    # 1. Normalize symbols (strip .P suffix)
    df = weekly_df.copy()
    df['symbol_clean'] = df['symbol'].str.replace('.P', '', regex=False)
    
    # 2. Get latest row per symbol (W-1)
    df = df.sort_values('period_start_date', ascending=False)
    df = df.drop_duplicates('symbol_clean').set_index('symbol_clean')
    
    # 3. Join current prices
    df['price'] = current_prices
    df = df.dropna(subset=['price'])
    
    if df.empty:
        return pd.DataFrame()
    
    # 4. Convert numeric columns (Decimal -> float)
    numeric_cols = ['final_poc', 'final_vah', 'final_val', 
                    'prior_final_poc', 'prior_final_vah', 'prior_final_val',
                    'va_width_pct', 'poc_change_pct', 'value_overlap_pct']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df['price'] = df['price'].astype(float)
    
    # 5. Compute all derived columns
    df['regime_w1'] = df.apply(compute_regime, axis=1)
    df['htf_dir_w1'] = df.apply(compute_htf_direction, axis=1)
    df['now_interaction_w1'] = df.apply(compute_interaction_tag, axis=1)
    df['pct_to_w_val'] = df.apply(lambda r: pct_distance(r['price'], r['final_val']), axis=1)
    df['pct_to_w_poc'] = df.apply(lambda r: pct_distance(r['price'], r['final_poc']), axis=1)
    df['pct_to_w_vah'] = df.apply(lambda r: pct_distance(r['price'], r['final_vah']), axis=1)
    df['warnings'] = df.apply(compute_warnings, axis=1)
    df['bias_compatibility'] = df.apply(compute_bias_compatibility, axis=1)
    
    return df


# ============== Pure Functions ==============

def compute_regime(row):
    """
    Compute weekly regime from overlap and POC migration.
    Returns: BALANCED | TRENDING | TRANSITIONAL
    """
    overlap = row.get('value_overlap_pct')
    
    if pd.isna(overlap):
        return 'TRANSITIONAL'
    
    overlap = float(overlap)
    
    if overlap >= config.OVERLAP_BALANCED:
        return 'BALANCED'
    elif overlap <= config.OVERLAP_TRENDING:
        return 'TRENDING'
    else:
        return 'TRANSITIONAL'


def compute_htf_direction(row):
    """
    Compute HTF direction from W-1 vs W-2 (prior) POC and midpoint.
    Returns: UP | DOWN | NEUTRAL
    """
    w1_poc = row.get('final_poc')
    w2_poc = row.get('prior_final_poc')
    w1_vah = row.get('final_vah')
    w1_val = row.get('final_val')
    w2_vah = row.get('prior_final_vah')
    w2_val = row.get('prior_final_val')
    
    # Handle missing prior data
    if pd.isna(w2_poc) or pd.isna(w1_poc):
        return 'NEUTRAL'
    
    w1_poc, w2_poc = float(w1_poc), float(w2_poc)
    w1_vah, w1_val = float(w1_vah), float(w1_val)
    w2_vah, w2_val = float(w2_vah), float(w2_val)
    
    poc_delta = w1_poc - w2_poc
    w1_mid = (w1_vah + w1_val) / 2
    w2_mid = (w2_vah + w2_val) / 2
    mid_delta = w1_mid - w2_mid
    
    if poc_delta > 0 and mid_delta > 0:
        return 'UP'
    elif poc_delta < 0 and mid_delta < 0:
        return 'DOWN'
    else:
        return 'NEUTRAL'


def compute_interaction_tag(row):
    """
    Compute price interaction vs W-1 VAL/POC/VAH.
    Returns: TEST_POC | TEST_VAL | TEST_VAH | INSIDE_VALUE | BELOW_VALUE | ABOVE_VALUE
    """
    price = float(row['price'])
    val = float(row['final_val'])
    poc = float(row['final_poc'])
    vah = float(row['final_vah'])
    
    tol = config.TOLERANCE_PCT / 100  # Convert to decimal
    
    # Priority order
    if abs(price - poc) / poc <= tol:
        return 'TEST_POC'
    if abs(price - val) / val <= tol:
        return 'TEST_VAL'
    if abs(price - vah) / vah <= tol:
        return 'TEST_VAH'
    if val <= price <= vah:
        return 'INSIDE_VALUE'
    if price < val:
        return 'BELOW_VALUE'
    if price > vah:
        return 'ABOVE_VALUE'
    
    return 'UNKNOWN'


def pct_distance(price, level):
    """
    Compute signed % distance from level.
    Positive = price above level, Negative = price below level.
    """
    if pd.isna(level) or level == 0:
        return None
    return round((float(price) - float(level)) / float(level) * 100, 2)


def compute_warnings(row):
    """
    Compute list of warning tags.
    Returns: List of strings
    """
    warnings = []
    
    # LOW_CONFIDENCE
    coverage = row.get('coverage_flag', '')
    if coverage and coverage.lower() not in ['full', 'complete', '']:
        warnings.append('LOW_CONFIDENCE')
    
    # COMPRESSED
    va_width = row.get('va_width_pct')
    if va_width is not None and float(va_width) < config.COMPRESSION_THRESHOLD:
        warnings.append('COMPRESSED')
    
    # PINNED (near POC with narrow VA)
    pct_poc = row.get('pct_to_w_poc')
    if pct_poc is not None and abs(pct_poc) < 0.2:
        if va_width is not None and float(va_width) < 0.02:
            warnings.append('PINNED')
    
    # EXTENDED
    pct_val = row.get('pct_to_w_val')
    pct_vah = row.get('pct_to_w_vah')
    
    if pct_val is not None and pct_val < -config.EXTENDED_THRESHOLD:
        warnings.append('EXTENDED')
    if pct_vah is not None and pct_vah > config.EXTENDED_THRESHOLD:
        warnings.append('EXTENDED')
    
    return warnings if warnings else []


def compute_bias_compatibility(row):
    """
    Compute bias compatibility based on regime, direction, interaction, warnings.
    Returns: FAVORS_LONG | FAVORS_SHORT | NEUTRAL_WAIT
    """
    warnings = row.get('warnings', [])
    regime = row.get('regime_w1', 'TRANSITIONAL')
    htf_dir = row.get('htf_dir_w1', 'NEUTRAL')
    interaction = row.get('now_interaction_w1', 'UNKNOWN')
    
    # Override if pinned or compressed
    if 'PINNED' in warnings or 'COMPRESSED' in warnings:
        return 'NEUTRAL_WAIT'
    
    # TRENDING regime
    if regime == 'TRENDING':
        if htf_dir == 'UP':
            if interaction in ['BELOW_VALUE', 'TEST_VAL', 'TEST_POC', 'INSIDE_VALUE']:
                return 'FAVORS_LONG'
            else:
                return 'NEUTRAL_WAIT'
        elif htf_dir == 'DOWN':
            if interaction in ['ABOVE_VALUE', 'TEST_VAH', 'TEST_POC', 'INSIDE_VALUE']:
                return 'FAVORS_SHORT'
            else:
                return 'NEUTRAL_WAIT'
        else:
            return 'NEUTRAL_WAIT'
    
    # BALANCED regime
    if regime == 'BALANCED':
        if interaction in ['TEST_VAL', 'BELOW_VALUE']:
            return 'FAVORS_LONG'
        elif interaction in ['TEST_VAH', 'ABOVE_VALUE']:
            return 'FAVORS_SHORT'
        else:
            return 'NEUTRAL_WAIT'
    
    # TRANSITIONAL regime
    if regime == 'TRANSITIONAL':
        if interaction in ['TEST_VAL', 'BELOW_VALUE']:
            return 'FAVORS_LONG'
        elif interaction in ['TEST_VAH', 'ABOVE_VALUE']:
            return 'FAVORS_SHORT'
        else:
            return 'NEUTRAL_WAIT'
    
    return 'NEUTRAL_WAIT'
