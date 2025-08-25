"""
FIXED ALERT SYSTEM - Bulletproof Deduplication
Prevents any duplicate alerts while maintaining signal accuracy
"""

import os
import requests
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging

class DeduplicationManager:
    """FIXED: Bulletproof deduplication preventing duplicate alerts"""
    
    def __init__(self, cache_dir):
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "deduplication_cache.json"
        self.cache = {}
        self.logger = logging.getLogger(__name__)
        self.load_cache()
    
    def load_cache(self):
        """Load deduplication cache from disk"""
        if self.cache_file.exists():
            try:
                cache_data = json.loads(self.cache_file.read_text())
                # Clean old entries (older than 24 hours)
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                self.cache = {
                    key: data for key, data in cache_data.items()
                    if datetime.fromisoformat(data.get('timestamp', '2000-01-01')) > cutoff_time
                }
                self.logger.info(f"Loaded {len(self.cache)} deduplication entries")
            except Exception as e:
                self.logger.error(f"Cache loading error: {e}")
                self.cache = {}
        else:
            self.cache = {}
    
    def save_cache(self):
        """Save deduplication cache to disk"""
        try:
            self.cache_file.write_text(json.dumps(self.cache, indent=2))
        except Exception as e:
            self.logger.error(f"Cache saving error: {e}")
    
    def create_cache_key(self, coin, signal):
        """FIXED: Ultra-robust cache key preventing all duplicates"""
        try:
            symbol = coin['symbol'].upper()
            action = signal['signal_type'].upper()
            
            # FIXED: Aggressive rounding to eliminate floating point issues
            wt1_bucket = int(round(signal.get('wt1', 0) / 5) * 5)  # Round to nearest 5
            wt2_bucket = int(round(signal.get('wt2', 0) / 5) * 5)  # Round to nearest 5
            stoch_k_bucket = int(round(signal.get('stoch_rsi_k', 0) / 5) * 5)  # Round to nearest 5
            stoch_d_bucket = int(round(signal.get('stoch_rsi_d', 0) / 5) * 5)  # Round to nearest 5
            
            # FIXED: Normalize candle timestamp to hourly buckets
            candle_ts = signal.get('candle_timestamp')
            if isinstance(candle_ts, str):
                try:
                    dt = datetime.fromisoformat(candle_ts.replace('Z', '+00:00'))
                    hour_bucket = dt.strftime('%Y-%m-%d_%H:00')
                except:
                    hour_bucket = candle_ts[:13] + ':00'
            else:
                hour_bucket = candle_ts.strftime('%Y-%m-%d_%H:00')
            
            # Simple, reliable cache key
            cache_key = f"{symbol}_{action}_{hour_bucket}_{wt1_bucket}_{wt2_bucket}_{stoch_k_bucket}_{stoch_d_bucket}"
            return cache_key
            
        except Exception as e:
            self.logger.error(f"Cache key error: {e}")
            return f"{coin.get('symbol', 'UNK')}_{signal.get('signal_type', 'UNK')}_{int(time.time() // 3600)}"
    
    def is_duplicate(self, coin, signal):
        """FIXED: Enhanced duplicate checking"""
        try:
            cache_key = self.create_cache_key(coin, signal)
            
            if cache_key in self.cache:
                cache_time_str = self.cache[cache_key].get('timestamp', '2000-01-01')
                cache_time = datetime.fromisoformat(cache_time_str)
                time_diff = datetime.utcnow() - cache_time
                
                if time_diff.total_seconds() < 14400:  # 4 hours
                    self.logger.info(f"🔄 Duplicate prevented: {cache_key}")
                    return True
                else:
                    del self.cache[cache_key]
                    self.logger.info(f"🧹 Expired entry removed: {cache_key}")
            
            return False
            
        except Exception as e:
            self.logger.error(f"Duplicate check error: {e}")
            return False
    
    def mark_sent(self, coin, signal):
        """FIXED: Mark signal as sent"""
        try:
            cache_key = self.create_cache_key(coin, signal)
            
            self.cache[cache_key] = {
                'symbol': coin['symbol'],
                'signal_type': signal['signal_type'],
                'timestamp': datetime.utcnow().isoformat(),
                'wt1': signal.get('wt1', 0),
                'wt2': signal.get('wt2', 0),
                'stoch_k': signal.get('stoch_rsi_k', 0),
                'stoch_d': signal.get('stoch_rsi_d', 0),
                'price': coin.get('current_price', 0)
            }
            
            # Save immediately
            self.save_cache()
            self.logger.info(f"✅ Signal cached: {cache_key}")
            
        except Exception as e:
            self.logger.error(f"Mark sent error: {e}")

class ChartURLResolver:
    """
    Smart chart URL resolver with exchange fallback and caching
    Tests actual URLs to ensure TradingView charts load properly
    """
    
    def __init__(self, cache_dir):
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "chart_cache.json"
        self.chart_cache = {}
        self.logger = logging.getLogger(__name__)
        self.load_cache()
    
    def load_cache(self):
        """Load chart URL cache"""
        if self.cache_file.exists():
            try:
                cache_data = json.loads(self.cache_file.read_text())
                # Keep cache entries that are less than 24 hours old
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                self.chart_cache = {
                    symbol: data for symbol, data in cache_data.items()
                    if datetime.fromisoformat(data.get('timestamp', '2000-01-01')) > cutoff_time
                }
                self.logger.info(f"Loaded {len(self.chart_cache)} chart URL cache entries")
            except Exception as e:
                self.logger.error(f"Chart cache loading error: {e}")
                self.chart_cache = {}
    
    def save_cache(self):
        """Save chart URL cache"""
        try:
            self.cache_file.write_text(json.dumps(self.chart_cache, indent=2))
        except Exception as e:
            self.logger.error(f"Chart cache saving error: {e}")
    
    def test_chart_url(self, url):
        """Test if TradingView chart URL actually works"""
        try:
            response = requests.head(url, timeout=3, allow_redirects=True)
            return response.status_code == 200
        except:
            return False
    
    def get_working_chart_url(self, symbol):
        """Get working TradingView chart URL with smart fallback"""
        # Check cache first
        if symbol in self.chart_cache:
            cached_data = self.chart_cache[symbol]
            cache_age = datetime.utcnow() - datetime.fromisoformat(cached_data['timestamp'])
            
            if cache_age.total_seconds() < 86400:  # 24 hours
                return cached_data['url'], cached_data['exchange']
        
        # Exchange priority list with correct URL formats
        exchanges = [
            ('BYBIT', f"https://www.tradingview.com/chart/?symbol=BYBIT:{symbol}USDT"),
            ('BINANCE', f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}USDT"),
            ('OKX', f"https://www.tradingview.com/chart/?symbol=OKX:{symbol}USDT"),
            ('COINBASE', f"https://www.tradingview.com/chart/?symbol=COINBASE:{symbol}USD"),
        ]
        
        # Test each exchange
        for exchange, url in exchanges:
            if self.test_chart_url(url):
                # Cache the working URL
                self.chart_cache[symbol] = {
                    'url': url,
                    'exchange': exchange,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Save cache periodically
                if len(self.chart_cache) % 10 == 0:
                    self.save_cache()
                
                return url, exchange
        
        # Force Bybit fallback (even if test fails, Bybit has best coverage)
        fallback_url = f"https://www.tradingview.com/chart/?symbol=BYBIT:{symbol}USDT"
        return fallback_url, "BYBIT"


class TelegramAlertManager:
    """
    Enhanced Telegram alert manager with premium formatting
    Handles dual-tier alerts with comprehensive signal information
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Load Telegram credentials
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.high_risk_chat_id = os.environ.get('HIGH_RISK_CHAT_ID')
        self.standard_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if not self.bot_token:
            self.logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
    
    def get_ist_time(self):
        """Get IST time in 12-hour format"""
        from datetime import datetime, timedelta
        utc = datetime.utcnow()
        ist = utc + timedelta(hours=5, minutes=30)
        return ist.strftime('%I:%M %p %d-%m-%Y'), ist.strftime('%A, %d %B %Y')
    
    def format_price(self, price):
        """Format price with appropriate precision"""
        if price >= 1:
            return f"${price:,.2f}"
        elif price >= 0.01:
            return f"${price:.4f}"
        else:
            return f"${price:.8f}"
    
    def format_change(self, change):
        """Format price change with emoji"""
        if change > 0:
            return f"📈 +{change:.2f}%"
        elif change < 0:
            return f"📉 {change:.2f}%"
        else:
            return f"➡️ {change:.2f}%"
    
    def get_market_cap_category(self, coin):
        """Get market cap category with emoji"""
        market_cap = coin.get('market_cap', 0)
        cap_billions = market_cap / 1_000_000_000
        
        if cap_billions >= 1:
            return f"🔷 Large Cap (${cap_billions:.1f}B)"
        else:
            cap_millions = market_cap / 1_000_000
            if cap_millions >= 100:
                return f"💎 Mid Cap (${cap_millions:.0f}M)"
            else:
                return f"💎 Small Cap (${cap_millions:.0f}M)"
    
    def create_alert_message(self, coin, signal, tier_type):
        """Create premium alert message with all signal details"""
        try:
            action = signal['signal_type']
            action_emoji = '🟢' if action == 'BUY' else '🔴'
            
            # Tier-specific formatting
            if tier_type == "HIGH_RISK":
                title = f"{action_emoji} HIGH RISK SIGNAL {action_emoji}"
                timeframe_info = "📊 1H Heikin Ashi TrendPulse + 2H StochRSI"
                urgency = "⚡ PREMIUM AUTHENTICATED SIGNAL ⚡"
            else:
                title = f"{action_emoji} STANDARD SIGNAL {action_emoji}"
                timeframe_info = "📊 1H Heikin Ashi TrendPulse + 2H StochRSI"
                urgency = "💎 QUALITY CONFIRMED SIGNAL 💎"
            
            # Get formatted data
            time_str, date_str = self.get_ist_time()
            price_str = self.format_price(coin['current_price'])
            change_str = self.format_change(coin.get('price_change_24h', 0))
            cap_category = self.get_market_cap_category(coin)
            
            # Build comprehensive message
            message = f"""{title}
**{coin['symbol']}-USD — {action}**
{cap_category}
{urgency}

💰 **Price**: {price_str}
📊 **24h Change**: {change_str}
📈 **TrendPulse**: WT1:{signal.get('wt1', 0):.2f} | WT2:{signal.get('wt2', 0):.2f}
🎯 **StochRSI 2H**: K:{signal.get('stoch_rsi_k', 0):.1f} D:{signal.get('stoch_rsi_d', 0):.1f}
💪 **Signal Strength**: {signal.get('strength', 0):.1f}
✅ **Confirmation**: {signal.get('confirmation_reason', 'Authenticated')}
🕐 **Time**: {time_str} IST
📅 **Date**: {date_str}
{timeframe_info}

🔗 [**Live Chart**]({signal.get('chart_url', 'https://tradingview.com')})"""

            return message
            
        except Exception as e:
            self.logger.error(f"Message creation error: {e}")
            return f"Signal Alert: {coin.get('symbol', 'UNKNOWN')} {signal.get('signal_type', 'UNKNOWN')}"
    
    def send_alert(self, coin, signal, tier_type):
        """Send alert to appropriate Telegram channel"""
        try:
            # Determine chat ID based on tier
            if tier_type == "HIGH_RISK":
                chat_id = self.high_risk_chat_id
            else:
                chat_id = self.standard_chat_id
            
            if not self.bot_token or not chat_id:
                self.logger.error(f"Missing Telegram credentials for {tier_type}")
                return False
            
            # Create message
            message = self.create_alert_message(coin, signal, tier_type)
            
            # Send to Telegram
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                self.logger.info(f"Alert sent successfully: {coin['symbol']} {signal['signal_type']}")
                return True
            else:
                self.logger.error(f"Telegram API error {response.status_code}: {response.text[:100]}")
                return False
                
        except Exception as e:
            self.logger.error(f"Alert sending error: {e}")
            return False
