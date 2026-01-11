import pandas as pd
import numpy as np

def calculate_zscore(series, window=20):
    """Calculate rolling Z-Score for a series."""
    mean = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    zscore = (series - mean) / std
    return zscore

def calculate_cvd_momentum(df, short_period=11, long_period=21):
    """
    Calculate CVD and its momentum (short MA vs long MA).
    Returns: 'BULLISH', 'BEARISH', or 'NEUTRAL'
    """
    if df.empty or len(df) < long_period:
        return 'NEUTRAL', None
    
    # CVD = cumsum of (2 * taker_buy_base - volume)
    delta = (2 * df['taker_buy_base']) - df['volume']
    cvd = delta.cumsum()
    
    # Moving averages
    cvd_short = cvd.rolling(window=short_period).mean()
    cvd_long = cvd.rolling(window=long_period).mean()
    
    # Latest values
    latest_short = cvd_short.iloc[-1]
    latest_long = cvd_long.iloc[-1]
    
    if pd.isna(latest_short) or pd.isna(latest_long):
        return 'NEUTRAL', None
    
    # Momentum direction
    if latest_short > latest_long * 1.01:  # Short above long by > 1%
        return 'BULLISH', float(latest_short - latest_long)
    elif latest_short < latest_long * 0.99:  # Short below long by > 1%
        return 'BEARISH', float(latest_short - latest_long)
    else:
        return 'NEUTRAL', float(latest_short - latest_long)

def detect_signals(symbol, klines_df, context_row, zscore_threshold=2.5):
    """
    Detect signals for a single symbol.
    
    Inputs:
    - symbol: Ticker string
    - klines_df: OHLCV DataFrame from Binance
    - context_row: Row from Stage 1 context (auction state, price loc, etc.)
    
    Output:
    - List of signal dicts, or empty list if no signals
    """
    signals = []
    
    if klines_df.empty or len(klines_df) < 25:
        return signals
    
    # 1. Volume Z-Score
    klines_df['vol_zscore'] = calculate_zscore(klines_df['volume'], window=20)
    latest_zscore = klines_df['vol_zscore'].iloc[-1]
    
    # 2. CVD Momentum
    cvd_momentum, cvd_delta = calculate_cvd_momentum(klines_df)
    
    # 3. Signal Conditions
    # Condition A: High volume at a key level
    price_loc = context_row.get('price_loc_w', 'UNKNOWN')
    is_at_level = price_loc in ['TEST_POC', 'ABOVE', 'BELOW']
    
    if not pd.isna(latest_zscore) and latest_zscore >= zscore_threshold and is_at_level:
        signals.append({
            'symbol': symbol,
            'trigger': 'VOL_ZSCORE',
            'zscore': round(float(latest_zscore), 2),
            'cvd_momentum': cvd_momentum,
            'price_loc': price_loc,
            'auction_state': context_row.get('weekly_auction_state', 'N/A'),
            'current_price': float(context_row.get('current_price', 0)),
        })
    
    # Condition B: Strong CVD momentum alignment with structure
    auction_state = context_row.get('weekly_auction_state', 'N/A')
    if cvd_momentum == 'BULLISH' and auction_state == 'TRENDING' and price_loc in ['BELOW', 'TEST_POC']:
        signals.append({
            'symbol': symbol,
            'trigger': 'CVD_BULLISH_ALIGN',
            'zscore': round(float(latest_zscore), 2) if not pd.isna(latest_zscore) else None,
            'cvd_momentum': cvd_momentum,
            'price_loc': price_loc,
            'auction_state': auction_state,
            'current_price': float(context_row.get('current_price', 0)),
        })
    elif cvd_momentum == 'BEARISH' and auction_state == 'TRENDING' and price_loc in ['ABOVE', 'TEST_POC']:
        signals.append({
            'symbol': symbol,
            'trigger': 'CVD_BEARISH_ALIGN',
            'zscore': round(float(latest_zscore), 2) if not pd.isna(latest_zscore) else None,
            'cvd_momentum': cvd_momentum,
            'price_loc': price_loc,
            'auction_state': auction_state,
            'current_price': float(context_row.get('current_price', 0)),
        })
    
    return signals

def format_ticket(signal):
    """Format a signal dict as a copy-paste friendly string."""
    return (
        f"{signal['symbol']} | "
        f"{signal['trigger']} | "
        f"Z:{signal.get('zscore', 'N/A')} | "
        f"CVD:{signal['cvd_momentum']} | "
        f"Loc:{signal['price_loc']} | "
        f"State:{signal['auction_state']} | "
        f"@{signal['current_price']:.2f}"
    )
