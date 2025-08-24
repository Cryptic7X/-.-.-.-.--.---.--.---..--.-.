"""
DATA MANAGER MODULE - CoinGecko & Multi-Exchange Integration
Handles coin discovery, filtering, and multi-timeframe data collection
Optimized for API limits with smart caching
"""

import requests
import pandas as pd
import ccxt
import json
import time
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

class CoinGeckoManager:
    """
    CoinGecko API manager with optimized caching and pagination
    Stays within free tier limits while providing comprehensive coverage
    """
    
    def __init__(self, cache_dir):
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "coingecko_cache.json"
        self.api_calls_used = 0
        self.logger = logging.getLogger(__name__)
    
    def load_cache(self):
        """Load cached coin data with timestamp validation"""
        if self.cache_file.exists():
            try:
                cache_data = json.loads(self.cache_file.read_text())
                coins = cache_data.get('coins', [])
                timestamp = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
                return coins, timestamp
            except Exception as e:
                self.logger.error(f"Cache loading error: {e}")
                return [], datetime.min
        return [], datetime.min
    
    def save_cache(self, coins):
        """Save coins to cache with timestamp"""
        cache_data = {
            'coins': coins,
            'timestamp': datetime.utcnow().isoformat(),
            'total_coins': len(coins),
            'cache_version': '3.0'
        }
        try:
            self.cache_file.write_text(json.dumps(cache_data, indent=2))
        except Exception as e:
            self.logger.error(f"Cache saving error: {e}")
    
    def get_dual_tier_coins(self):
        """Fetch coins with pagination and dual-tier filtering"""
        cached_coins, cache_time = self.load_cache()
        now = datetime.utcnow()
        
        # Use cache if less than 30 minutes old
        cache_age_minutes = (now - cache_time).total_seconds() / 60
        if cache_age_minutes < 30:
            self.logger.info(f"Using cached CoinGecko data (age: {cache_age_minutes:.1f} min)")
            return self.categorize_coins(cached_coins), 0
        
        # Fetch fresh data
        self.logger.info("Fetching fresh CoinGecko data with pagination...")
        api_key = os.environ.get('COINGECKO_API_KEY', '')
        url = "https://api.coingecko.com/api/v3/coins/markets"
        headers = {'x-cg-demo-api-key': api_key} if api_key else {}
        
        all_coins = []
        api_calls = 0
        
        try:
            # Fetch 5 pages to get ~1250 coins
            for page in range(1, 6):
                params = {
                    'vs_currency': 'usd',
                    'order': 'market_cap_desc',
                    'per_page': 250,
                    'page': page,
                    'sparkline': 'false'
                }
                
                self.logger.info(f"Fetching CoinGecko page {page}...")
                response = requests.get(url, params=params, headers=headers, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                api_calls += 1
                
                if not data:
                    break
                
                all_coins.extend(data)
                time.sleep(0.2)  # Rate limiting
            
            self.logger.info(f"Fetched {len(all_coins)} total coins from {api_calls} API calls")
            
            # Apply dual-tier filtering
            filtered_coins = self.filter_coins(all_coins)
            
            # Save to cache
            self.save_cache(filtered_coins)
            self.api_calls_used += api_calls
            
            categorized = self.categorize_coins(filtered_coins)
            self.logger.info(f"HIGH RISK: {len(categorized['high_risk'])}, STANDARD: {len(categorized['standard'])}")
            
            return categorized, api_calls
            
        except Exception as e:
            self.logger.error(f"CoinGecko API error: {e}")
            # Fallback to cached data
            return self.categorize_coins(cached_coins), 0
    
    def filter_coins(self, raw_coins):
        """Apply market cap and volume filtering"""
        filtered = []
        stablecoins = {'USDT', 'USDC', 'DAI', 'BUSD', 'USDE', 'FDUSD', 'TUSD'}
        
        for coin in raw_coins:
            market_cap = coin.get('market_cap', 0) or 0
            volume_24h = coin.get('total_volume', 0) or 0
            current_price = coin.get('current_price', 0) or 0
            
            # Skip coins with missing critical data
            if market_cap <= 0 or volume_24h <= 0 or current_price <= 0:
                continue
            
            # Dual-tier qualification
            high_risk_qualified = (
                market_cap >= 10_000_000 and 
                market_cap < 500_000_000 and 
                volume_24h >= 10_000_000
            )
            
            standard_qualified = (
                market_cap >= 500_000_000 and 
                volume_24h >= 30_000_000
            )
            
            # Include if qualified and not a stablecoin
            if ((high_risk_qualified or standard_qualified) and 
                coin['symbol'].upper() not in stablecoins):
                
                filtered.append({
                    'id': coin['id'],
                    'symbol': coin['symbol'].upper(),
                    'name': coin['name'],
                    'market_cap': market_cap,
                    'total_volume': volume_24h,
                    'current_price': current_price,
                    'price_change_24h': coin.get('price_change_percentage_24h', 0)
                })
        
        return filtered
    
    def categorize_coins(self, coins):
        """Separate coins into HIGH RISK and STANDARD tiers"""
        high_risk = [coin for coin in coins if coin['market_cap'] < 500_000_000]
        standard = [coin for coin in coins if coin['market_cap'] >= 500_000_000]
        
        return {
            'high_risk': high_risk,
            'standard': standard
        }
    
    def get_cached_coins(self):
        """Get coins from cache only (for 5-minute cycles)"""
        cached_coins, _ = self.load_cache()
        return self.categorize_coins(cached_coins), 0


class MultiExchangeManager:
    """
    Multi-exchange manager with intelligent fallback
    Prioritizes BingX but falls back to other exchanges for better coverage
    """
    
    def __init__(self):
        self.exchanges = {}
        self.symbol_cache = {}
        self.logger = logging.getLogger(__name__)
        self.initialize_exchanges()
    
    def initialize_exchanges(self):
        """Initialize all exchanges with error handling"""
        exchange_configs = {
            'bingx': {
                'class': ccxt.bingx,
                'config': {
                    'apiKey': os.environ.get('BINGX_API_KEY', ''),
                    'secret': os.environ.get('BINGX_SECRET_KEY', ''),
                    'enableRateLimit': True,
                    'timeout': 30000,
                }
            },
            'binance': {
                'class': ccxt.binance,
                'config': {
                    'enableRateLimit': True,
                    'timeout': 30000,
                }
            },
            'okx': {
                'class': ccxt.okx,
                'config': {
                    'enableRateLimit': True,
                    'timeout': 30000,
                }
            },
            'bybit': {
                'class': ccxt.bybit,
                'config': {
                    'enableRateLimit': True,
                    'timeout': 30000,
                }
            }
        }
        
        for name, config in exchange_configs.items():
            try:
                exchange = config['class'](config['config'])
                exchange.load_markets()
                self.exchanges[name] = exchange
                self.logger.info(f"✅ {name.upper()} exchange initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to initialize {name}: {str(e)[:50]}")
    
    def find_symbol_on_exchange(self, exchange_name, base_symbol):
        """Find working symbol format on specific exchange"""
        if exchange_name not in self.exchanges:
            return None
        
        exchange = self.exchanges[exchange_name]
        symbol_variations = [
            f"{base_symbol}/USDT",
            f"{base_symbol}/BUSD",
            f"{base_symbol}/USD"
        ]
        
        # Add futures variations for applicable exchanges
        if exchange_name in ['bingx', 'bybit', 'okx']:
            symbol_variations.extend([
                f"{base_symbol}/USDT:USDT",
                f"{base_symbol}/USD:USD"
            ])
        
        for symbol_format in symbol_variations:
            try:
                if symbol_format in exchange.markets:
                    market = exchange.markets[symbol_format]
                    if market.get('active', True):
                        return symbol_format
            except:
                continue
        
        return None
    
    def fetch_ohlcv_with_retry(self, exchange_name, symbol, timeframe, limit):
        """Fetch OHLCV data with retry mechanism"""
        if exchange_name not in self.exchanges:
            return None
        
        exchange = self.exchanges[exchange_name]
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                
                if ohlcv and len(ohlcv) >= 30:
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    # Convert to numeric
                    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    df = df.dropna()
                    
                    if len(df) >= 30:
                        return df
                
                return None
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                return None
        
        return None
    
    def get_multi_timeframe_data(self, symbol, timeframes):
        """
        Get multi-timeframe data with exchange fallback
        timeframes: dict like {'1h': 50, '2h': 100} (timeframe: limit)
        """
        data = {}
        exchange_priority = ['bingx', 'binance', 'okx', 'bybit']
        
        # Find working symbol format
        working_symbol = None
        working_exchange = None
        
        for exchange_name in exchange_priority:
            symbol_format = self.find_symbol_on_exchange(exchange_name, symbol)
            if symbol_format:
                working_symbol = symbol_format
                working_exchange = exchange_name
                break
        
        if not working_symbol or not working_exchange:
            return {}
        
        # Fetch data for all required timeframes
        for timeframe, limit in timeframes.items():
            df = self.fetch_ohlcv_with_retry(working_exchange, working_symbol, timeframe, limit)
            if df is not None:
                data[timeframe] = df
        
        return data
