import pandas as pd
import numpy as np

def calculate_context_primitives(structure_df, current_prices):
    """
    Inputs:
    - structure_df: Raw BQ DataFrame (mixed timeframes, multiple dates).
    - current_prices: Series of live prices {symbol: price}.
    
    Output:
    - context_df: One row per symbol with all primitives calculated.
    """
    if structure_df.empty:
        return pd.DataFrame()

    # 0. Normalize Symbols (Strip .P suffix from BQ data)
    structure_df = structure_df.copy()
    structure_df['symbol_clean'] = structure_df['symbol'].str.replace('.P', '', regex=False)

    # 1. Normalize & Filter Latest Structure
    # Normalize timeframe: 'Daily'/'D' -> 'D', 'Weekly'/'W' -> 'W'
    structure_df['timeframe'] = structure_df['timeframe'].map({
        'Daily': 'D', 'D': 'D', 
        'Weekly': 'W', 'W': 'W'
    })
    
    # Sort by date desc to get latest
    structure_df = structure_df.sort_values('period_start_date', ascending=False)
    
    # Split D and W - Use symbol_clean as index for joining with Binance
    daily_df = structure_df[structure_df['timeframe'] == 'D'].drop_duplicates('symbol_clean').set_index('symbol_clean')
    weekly_df = structure_df[structure_df['timeframe'] == 'W'].drop_duplicates('symbol_clean').set_index('symbol_clean')

    # Keys: symbol is index
    # We only care about symbols present in Weeklies (Anchor)
    context = weekly_df.join(daily_df, lsuffix='_w', rsuffix='_d', how='inner')
    
    # Join Price
    context['current_price'] = current_prices
    context = context.dropna(subset=['current_price']) # Drop if no price data

    # Apply Logic
    context['weekly_auction_state'] = context.apply(_get_auction_state, axis=1)
    context['dw_alignment'] = context.apply(_get_alignment, axis=1)
    context['price_loc_w'] = context.apply(_get_price_loc_w, axis=1)
    context['price_loc_d'] = context.apply(_get_price_loc_d, axis=1)
    context['flags'] = context.apply(_get_flags, axis=1)
    
    return context

def _get_auction_state(row):
    # Logic: Balanced if high overlap. Trending if shift + low overlap.
    overlap = row.get('value_overlap_pct_w', 0)
    # Handle NaN overlap (first week)
    if pd.isna(overlap): return 'TRANSITIONAL'
    
    if overlap > 0.70:
        return 'BALANCED'
    elif overlap < 0.30:
        return 'TRENDING'
    else:
        return 'TRANSITIONAL'

def _get_alignment(row):
    # Logic: D value relationship to W value
    # Simple check for now: Is Daily Value *completely* outside Weekly POC?
    # Or just check simple trend alignment?
    # Let's use: ALIGNED if Daily Value is consistent with Weekly Trend direction?
    # Simpler v1: ALIGNED if Daily POC is inside Weekly Value.
    
    d_poc = row['final_poc_d']
    w_vah = row['final_vah_w']
    w_val = row['final_val_w']
    
    if w_val <= d_poc <= w_vah:
        return 'ALIGNED'
    else:
        # If D is outside W value, it could be Trending (good) or Counter (bad).
        # We label it MIXED for now unless we look at direction, which is harder without history here.
        return 'MIXED'

def _get_price_loc_w(row):
    p = float(row['current_price'])
    vah, val = float(row['final_vah_w']), float(row['final_val_w'])
    poc = float(row['final_poc_w'])
    tol = poc * 0.005 # 0.5% tolerance
    
    if abs(p - poc) < tol: return 'TEST_POC'
    if val <= p <= vah: return 'INSIDE'
    if p > vah: return 'ABOVE'
    if p < val: return 'BELOW'
    return 'UNKNOWN'

def _get_price_loc_d(row):
    p = float(row['current_price'])
    vah, val = float(row['final_vah_d']), float(row['final_val_d'])
    
    if val <= p <= vah: return 'INSIDE'
    if p > vah: return 'ABOVE'
    if p < val: return 'BELOW'
    return 'UNKNOWN'

def _get_flags(row):
    flags = []
    # 1. Compression
    width = float(row.get('va_width_pct_w', 0.05) or 0.05)
    if width < 0.015: # < 1.5% VA width is very tight for Crypto Weekly
        flags.append('COMPRESSION')
        
    # 2. Pinned (Price stuck at Weekly POC)
    poc_w = float(row['final_poc_w'])
    current_price = float(row['current_price'])
    dist = abs(current_price - poc_w) / poc_w if poc_w else 0
    if dist < 0.002: # 0.2% from POC
        flags.append('PINNED')
        
    return flags if flags else ['OK']
