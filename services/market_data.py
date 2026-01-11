import requests
import pandas as pd
import numpy as np
import streamlit as st
import config
import random
from datetime import datetime, timedelta

class BinanceService:
    def __init__(self):
        self.base_url = config.BINANCE_BASE_URL
        
    def _get_request(self, endpoint, params=None):
        """Helper to route requests through proxy if configured."""
        if config.BINANCE_PROXY_URL:
            # Proxy Mode
            proxy_params = {"endpoint": endpoint}
            if params:
                proxy_params.update(params)
            
            # Request to Proxy
            try:
                resp = requests.get(config.BINANCE_PROXY_URL, params=proxy_params)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                # Fallback or Error
                raise Exception(f"Proxy Error: {e}")
        else:
            # Direct Mode
            url = f"{self.base_url}{endpoint}"
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    def _generate_mock_price(self, symbol):
        """Generates a realistic-looking random price."""
        # Bitcoinish base + variance
        base = 95000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 100
        return base * (1 + random.uniform(-0.05, 0.05))

    def _generate_mock_klines(self, symbol, interval, limit):
        """Generates mock kline data."""
        end_time = datetime.now()
        data = []
        price = self._generate_mock_price(symbol)
        
        # Minutes multiplier
        mult = 5 if interval == '5m' else 15 if interval == '15m' else 30 if interval =='30m' else 240
        
        for i in range(limit):
            ts = end_time - timedelta(minutes=mult * (limit - i))
            open_p = price
            close_p = price * (1 + random.uniform(-0.002, 0.002))
            high_p = max(open_p, close_p) * (1 + random.uniform(0, 0.001))
            low_p = min(open_p, close_p) * (1 - random.uniform(0, 0.001))
            volume = random.uniform(100, 5000)
            taker_buy = volume * random.uniform(0.4, 0.6)
            
            # [time, open, high, low, close, volume, close_time, quote, trades, taker_buy_base, ...]
            row = [
                int(ts.timestamp() * 1000),
                open_p, high_p, low_p, close_p, volume,
                int((ts + timedelta(minutes=mult)).timestamp() * 1000),
                volume * close_p, 100, taker_buy, 0, 0
            ]
            data.append(row)
            price = close_p # Next candle starts at close
            
        return data

    @st.cache_data(ttl=60)  # Short cache for current prices
    def get_current_prices(_self):
        """
        Fetches all perp prices. Uses Mock if configured.
        """
        if config.USE_MOCK_DATA:
            # Mock 10 common symbols
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
            prices = {s: _self._generate_mock_price(s) for s in symbols}
            return pd.Series(prices)

        try:
            data = _self._get_request("/fapi/v1/ticker/price")
            # Filter for USDT perps only usually ideal
            df = pd.DataFrame(data)
            df = df[df['symbol'].str.endswith('USDT')] 
            df.set_index('symbol', inplace=True)
            return df['price'].astype(float)
        except Exception as e:
            st.error(f"Binance Price Fetch Error: {e}")
            return pd.Series()

    def get_klines(self, symbol, interval, limit=100):
        """
        Fetches OHLCV data. Uses Mock if configured.
        """
        if config.USE_MOCK_DATA:
            data = self._generate_mock_klines(symbol, interval, limit)
        else:
            try:
                params = {
                    "symbol": symbol,
                    "interval": interval,
                    "limit": limit
                }
                data = self._get_request("/fapi/v1/klines", params=params)
            except Exception as e:
                st.error(f"Binance Kline Fetch Error ({symbol}): {e}")
                return pd.DataFrame()
        
        # Binance Kline Format: 
        cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_vol', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore']
        df = pd.DataFrame(data, columns=cols)
        
        # Numeric conversion
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'taker_buy_base']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, axis=1)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df

    def calculate_cvd(self, df):
        """
        Calculates Cumulative Volume Delta (CVD) from Taker Buy/Sell data.
        """
        if df.empty:
            return pd.Series()
            
        # Delta = (2 * TakerBuyBase) - TotalVolume
        delta = (2 * df['taker_buy_base']) - df['volume']
        cvd = delta.cumsum()
        return cvd
