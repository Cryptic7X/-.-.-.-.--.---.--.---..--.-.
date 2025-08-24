


"""
GitHub Actions Crypto Analytics V3.0 - Scheduled Mode
Optimized for hybrid 0,5,15,30,45 minute schedule
"""

"""
GitHub Actions Crypto Analytics V3.0 - WITH BLOCKED COINS SUPPORT
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import logging

from data_manager import CoinGeckoManager, MultiExchangeManager
from analyzers import TrendPulseAnalyzer, StochRSICalculator, HeikinAshiConverter
from alert_system import TelegramAlertManager, ChartURLResolver, DeduplicationManager
from utils import setup_logging, format_price, load_blocked_coins  # Added load_blocked_coins

MAX_WORKERS = 2
BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "cache"
LOGS_DIR = BASE_DIR / "logs"

CACHE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

class GitHubActionsAnalytics:
    def __init__(self):
        self.logger = setup_logging(LOGS_DIR / "github_actions.log")
        self.logger.info("🚀 GitHub Actions Crypto Analytics V3.0")
        
        # Load blocked coins at startup
        self.blocked_coins = load_blocked_coins()  # ADDED THIS
        
        self.coingecko = CoinGeckoManager(CACHE_DIR)
        self.exchange = MultiExchangeManager()
        self.trendpulse = TrendPulseAnalyzer()
        self.stochrsi = StochRSICalculator()
        self.heikin_ashi = HeikinAshiConverter()
        self.deduplication = DeduplicationManager(CACHE_DIR)
        self.chart_resolver = ChartURLResolver(CACHE_DIR)
        self.telegram = TelegramAlertManager()
        
        self.start_time = datetime.utcnow()
        self.total_signals = 0
        self.total_alerts = 0

    def analyze_coin(self, coin, tier):
        try:
            symbol = coin['symbol']
            
            # BLOCKED COINS CHECK - ADDED THIS
            if symbol.upper() in self.blocked_coins:
                return None, f"🚫 BLOCKED: {symbol}"
            
            # Get market data
            data = self.fetch_market_data(symbol)
            if not data:
                return None, f"❌ No data: {symbol}"
            
            # Convert to Heikin Ashi
            ha_df = self.heikin_ashi.convert(data['1h'])
            if ha_df is None:
                return None, f"❌ HA failed: {symbol}"
            
            # TrendPulse analysis
            tp_signal = self.trendpulse.analyze(ha_df, tier)
            if not tp_signal['has_signal']:
                return None, f"📊 No TrendPulse: {symbol}"
            
            # StochRSI confirmation
            stoch = self.stochrsi.calculate(data['2h'])
            if not stoch:
                return None, f"❌ StochRSI failed: {symbol}"
            
            # Apply confirmation logic
            signal_type = tp_signal['signal_type']
            k, d = stoch['current_k'], stoch['current_d']
            
            if signal_type == 'BUY':
                confirmed = k < 20 and d < 20
                reason = f"StochRSI_2H_Oversold(K:{k:.1f},D:{d:.1f})"
            else:  # SELL
                confirmed = k > 80 and d > 80
                reason = f"StochRSI_2H_Overbought(K:{k:.1f},D:{d:.1f})"
            
            if not confirmed:
                return None, f"📊 No StochRSI confirmation: {symbol}"
            
            # Create confirmed signal
            signal = {
                **tp_signal,
                'stoch_rsi_k': k,
                'stoch_rsi_d': d,
                'confirmation_reason': reason,
                'candle_timestamp': ha_df.index[-2],
                'github_run_time': datetime.utcnow().isoformat()
            }
            
            return {
                'coin': coin,
                'signal': signal,
                'tier': tier
            }, f"✅ CONFIRMED {signal_type}: {symbol} ({reason})"
            
        except Exception as e:
            return None, f"❌ Error {symbol}: {str(e)[:50]}"


    def process_signals(self, results):
        sent = 0
        self.logger.info(f"🚨 Processing {len(results)} signals")
        
        for result in results:
            coin = result['coin']
            signal = result['signal']
            tier = result['tier']
            
            # Check for duplicates
            if self.deduplication.is_duplicate(coin, signal):
                self.logger.info(f"🔄 Duplicate prevented: {coin['symbol']}")
                continue
            
            # Get chart URL
            chart_url, exchange = self.chart_resolver.get_working_chart_url(coin['symbol'])
            signal['chart_url'] = chart_url
            signal['chart_exchange'] = exchange
            
            # Send alert
            if self.telegram.send_alert(coin, signal, tier):
                self.deduplication.mark_sent(coin, signal)
                sent += 1
                price = format_price(coin['current_price'])
                self.logger.info(f"✅ Alert sent: {coin['symbol']} {signal['signal_type']} @ {price}")
                
                # Cooldown between alerts
                if sent < len(results):
                    time.sleep(10)
        
        return sent

    def run(self):
        try:
            self.logger.info("🔄 Starting scheduled analysis")
            
            # Get coin data
            coin_data = self.get_coins()
            high_risk = coin_data['high_risk']
            standard = coin_data['standard']
            
            if not high_risk and not standard:
                self.logger.warning("⚠️ No coins to analyze")
                return 0
            
            results = []
            
            # Parallel analysis
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Submit all coins
                futures = []
                futures.extend([executor.submit(self.analyze_coin, coin, 'HIGH_RISK') for coin in high_risk])
                futures.extend([executor.submit(self.analyze_coin, coin, 'STANDARD') for coin in standard])
                
                # Collect results
                for future in futures:
                    try:
                        result, log = future.result(timeout=30)
                        self.logger.info(log)
                        if result:
                            results.append(result)
                    except Exception as e:
                        self.logger.error(f"Analysis timeout: {e}")
            
            # Send alerts
            self.total_signals = len(results)
            self.total_alerts = self.process_signals(results)
            
            duration = (datetime.utcnow() - self.start_time).total_seconds()
            self.logger.info(f"🎉 Complete: {self.total_alerts} alerts in {duration:.1f}s")
            
            return self.total_alerts
            
        except Exception as e:
            self.logger.error(f"❌ Critical error: {e}")
            return -1

def main():
    print("🚀 CRYPTO ANALYTICS V3.0 - GitHub Actions")
    print("=" * 50)
    print("🔥 1H TrendPulse + 2H StochRSI Confirmation")
    print("⏰ Hybrid schedule: 0,5,15,30,45 minutes")
    print("🎯 Premium authenticated signals only")
    print("=" * 50)
    
    try:
        system = GitHubActionsAnalytics()
        result = system.run()
        
        if result >= 0:
            print(f"✅ Success: {result} alerts sent")
            sys.exit(0)
        else:
            print("❌ Execution failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"💥 Startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

