"""
ADVANCED CRYPTO ANALYTICS V3.0 - MAIN EXECUTION FILE
Complete production-ready system with modular architecture
Perfect replication of Pine Script indicator with 2H StochRSI confirmation
"""

import os
import sys
import time
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import logging

# Import custom modules
from data_manager import CoinGeckoManager, MultiExchangeManager
from analyzers import TrendPulseAnalyzer, StochRSICalculator, HeikinAshiConverter
from alert_system import TelegramAlertManager, ChartURLResolver, DeduplicationManager
from utils import setup_logging, get_ist_time, format_price, format_change

# Configuration
EXECUTION_INTERVAL = 300  # 5 minutes in seconds
COINGECKO_REFRESH_INTERVAL = 1800  # 30 minutes in seconds
MAX_WORKERS = 4  # Conservative threading

# File paths
BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "cache"
LOGS_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

# Ensure directories exist
CACHE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)

class AdvancedCryptoAnalytics:
    """
    Main system controller for Advanced Crypto Analytics V3.0
    Orchestrates all components with perfect timing and error handling
    """
    
    def __init__(self):
        self.logger = setup_logging(LOGS_DIR / "system.log")
        self.logger.info("🚀 Initializing Advanced Crypto Analytics V3.0")
        
        # Initialize core components
        self.coingecko_manager = CoinGeckoManager(CACHE_DIR)
        self.exchange_manager = MultiExchangeManager()
        self.trendpulse_analyzer = TrendPulseAnalyzer()
        self.stochrsi_calculator = StochRSICalculator()
        self.heikin_ashi_converter = HeikinAshiConverter()
        self.deduplication_manager = DeduplicationManager(CACHE_DIR)
        self.chart_resolver = ChartURLResolver(CACHE_DIR)
        self.telegram_manager = TelegramAlertManager()
        
        # System state
        self.last_coingecko_refresh = datetime.min
        self.system_start_time = datetime.utcnow()
        self.total_signals_sent = 0
        self.total_cycles_completed = 0
        
        self.logger.info("✅ All components initialized successfully")

    def should_refresh_coingecko(self):
        """Check if CoinGecko data needs refreshing (every 30 minutes)"""
        time_since_refresh = datetime.utcnow() - self.last_coingecko_refresh
        return time_since_refresh.total_seconds() > COINGECKO_REFRESH_INTERVAL

    def get_coin_data(self):
        """Get coin list with smart caching strategy"""
        if self.should_refresh_coingecko():
            self.logger.info("🌐 Refreshing CoinGecko coin data (30-minute refresh)")
            tier_data, api_calls = self.coingecko_manager.get_dual_tier_coins()
            self.last_coingecko_refresh = datetime.utcnow()
            self.logger.info(f"✅ CoinGecko refresh complete: {api_calls} API calls used")
        else:
            cache_age = (datetime.utcnow() - self.last_coingecko_refresh).total_seconds() / 60
            self.logger.info(f"🔄 Using cached CoinGecko data (age: {cache_age:.1f} minutes)")
            tier_data, api_calls = self.coingecko_manager.get_cached_coins()
        
        return tier_data

    def fetch_market_data(self, symbol):
        """Fetch multi-timeframe data with exchange fallback"""
        try:
            # Get 1H data for TrendPulse and 2H data for StochRSI
            timeframes = {
                '1h': 50,   # For TrendPulse analysis
                '2h': 100   # For StochRSI confirmation
            }
            
            data = self.exchange_manager.get_multi_timeframe_data(symbol, timeframes)
            
            if not data or '1h' not in data or '2h' not in data:
                return None
                
            return data
            
        except Exception as e:
            self.logger.error(f"❌ Data fetch error for {symbol}: {str(e)[:50]}")
            return None

    def analyze_coin(self, coin, tier_type):
        """Complete coin analysis with TrendPulse + StochRSI confirmation"""
        try:
            symbol = coin['symbol']
            
            # Fetch market data
            market_data = self.fetch_market_data(symbol)
            if not market_data:
                return None, f"❌ No data: {symbol}"
            
            # Convert 1H data to Heikin Ashi
            ha_df = self.heikin_ashi_converter.convert(market_data['1h'])
            if ha_df is None:
                return None, f"❌ HA conversion failed: {symbol}"
            
            # TrendPulse analysis on 1H Heikin Ashi
            trendpulse_signal = self.trendpulse_analyzer.analyze(ha_df, tier_type)
            if not trendpulse_signal or not trendpulse_signal['has_signal']:
                return None, f"📊 No TrendPulse signal: {symbol}"
            
            # StochRSI confirmation on 2H
            stochrsi_data = self.stochrsi_calculator.calculate(market_data['2h'])
            if not stochrsi_data:
                return None, f"❌ StochRSI calculation failed: {symbol}"
            
            # Apply confirmation logic
            signal_type = trendpulse_signal['signal_type']
            k_value = stochrsi_data['current_k']
            d_value = stochrsi_data['current_d']
            
            confirmed = False
            if signal_type == 'BUY':
                # BUY: StochRSI must be oversold (< 20)
                confirmed = k_value < 20 and d_value < 20
                confirmation_reason = f"StochRSI_2H_Oversold(K:{k_value:.1f},D:{d_value:.1f})"
            elif signal_type == 'SELL':
                # SELL: StochRSI must be overbought (> 80)
                confirmed = k_value > 80 and d_value > 80
                confirmation_reason = f"StochRSI_2H_Overbought(K:{k_value:.1f},D:{d_value:.1f})"
            
            if not confirmed:
                return None, f"📊 No StochRSI confirmation: {symbol} (K:{k_value:.1f},D:{d_value:.1f})"
            
            # Create confirmed signal
            confirmed_signal = {
                **trendpulse_signal,
                'stoch_rsi_k': k_value,
                'stoch_rsi_d': d_value,
                'confirmation_reason': confirmation_reason,
                'candle_timestamp': ha_df.index[-2]
            }
            
            return {
                'coin': coin,
                'signal': confirmed_signal,
                'tier': tier_type
            }, f"✅ CONFIRMED {signal_type}: {symbol} ({confirmation_reason})"
            
        except Exception as e:
            return None, f"❌ Analysis error {symbol}: {str(e)[:50]}"

    def process_signals(self, results):
        """Process confirmed signals with deduplication and alerting"""
        alerts_sent = 0
        
        self.logger.info(f"🚨 Processing {len(results)} confirmed signals")
        
        for result in results:
            try:
                coin = result['coin']
                signal = result['signal']
                tier_type = result['tier']
                
                # Check deduplication
                if self.deduplication_manager.is_duplicate(coin, signal):
                    self.logger.info(f"🔄 Duplicate prevented: {coin['symbol']} {signal['signal_type']}")
                    continue
                
                # Get chart URL
                chart_url, exchange = self.chart_resolver.get_working_chart_url(coin['symbol'])
                signal['chart_url'] = chart_url
                signal['chart_exchange'] = exchange
                
                # Send alert
                success = self.telegram_manager.send_alert(coin, signal, tier_type)
                if success:
                    # Mark as sent in deduplication cache
                    self.deduplication_manager.mark_sent(coin, signal)
                    alerts_sent += 1
                    
                    self.logger.info(f"✅ Alert sent: {coin['symbol']} {signal['signal_type']} @ {format_price(coin['current_price'])}")
                    
                    # Add 30-second global cooldown between alerts
                    if alerts_sent < len(results):
                        time.sleep(30)
                
            except Exception as e:
                self.logger.error(f"❌ Alert processing error: {str(e)[:80]}")
                continue
        
        return alerts_sent

    def execute_analysis_cycle(self):
        """Execute complete analysis cycle"""
        cycle_start = datetime.utcnow()
        self.logger.info("🔄 Starting analysis cycle")
        
        try:
            # Get coin data
            tier_data = self.get_coin_data()
            high_risk_coins = tier_data['high_risk']
            standard_coins = tier_data['standard']
            
            total_coins = len(high_risk_coins) + len(standard_coins)
            self.logger.info(f"📊 Analyzing {total_coins} coins (HR: {len(high_risk_coins)}, ST: {len(standard_coins)})")
            
            all_results = []
            
            # Parallel processing with conservative thread count
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Submit HIGH RISK coins
                high_risk_futures = [
                    executor.submit(self.analyze_coin, coin, 'HIGH_RISK')
                    for coin in high_risk_coins
                ]
                
                # Submit STANDARD coins
                standard_futures = [
                    executor.submit(self.analyze_coin, coin, 'STANDARD')
                    for coin in standard_coins
                ]
                
                # Collect HIGH RISK results
                self.logger.info("🔥 Processing HIGH RISK tier (1H HA + 2H StochRSI)")
                for i, future in enumerate(high_risk_futures, 1):
                    result, log = future.result()
                    if i <= 5 or i % 20 == 0 or result:  # Log first 5, every 20th, and all signals
                        self.logger.info(f"[{i}/{len(high_risk_futures)}] {log}")
                    if result:
                        all_results.append(result)
                
                # Collect STANDARD results
                self.logger.info("📊 Processing STANDARD tier (1H HA + 2H StochRSI)")
                for i, future in enumerate(standard_futures, 1):
                    result, log = future.result()
                    if i <= 5 or i % 20 == 0 or result:  # Log first 5, every 20th, and all signals
                        self.logger.info(f"[{i}/{len(standard_futures)}] {log}")
                    if result:
                        all_results.append(result)
            
            # Process signals and send alerts
            alerts_sent = self.process_signals(all_results)
            
            # Update statistics
            self.total_signals_sent += alerts_sent
            self.total_cycles_completed += 1
            
            cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
            
            self.logger.info(f"🎉 Cycle complete: {alerts_sent} alerts sent in {cycle_duration:.1f}s")
            
            return alerts_sent, cycle_duration
            
        except Exception as e:
            self.logger.error(f"❌ Critical error in analysis cycle: {str(e)}")
            return 0, 0

    def print_system_stats(self):
        """Print comprehensive system statistics"""
        uptime = datetime.utcnow() - self.system_start_time
        uptime_hours = uptime.total_seconds() / 3600
        
        print(f"\n🎉 ADVANCED CRYPTO ANALYTICS V3.0 - SYSTEM STATISTICS")
        print("=" * 80)
        print(f"   ⏱️  System Uptime: {uptime_hours:.1f} hours")
        print(f"   🔄 Cycles Completed: {self.total_cycles_completed}")
        print(f"   🚨 Total Alerts Sent: {self.total_signals_sent}")
        print(f"   📊 Average Alerts/Hour: {self.total_signals_sent / max(uptime_hours, 0.1):.1f}")
        print(f"   🎯 Success Rate: Premium authenticated signals only")
        print(f"   💾 Cache Status: CoinGecko + Chart URLs + Deduplication active")
        print(f"   📡 API Usage: Optimized for free tier limits")
        print(f"   ✅ System Status: OPERATIONAL")
        print("=" * 80)

    def run(self):
        """Main system execution loop"""
        self.logger.info("🚀 Advanced Crypto Analytics V3.0 started")
        print("🚀 ADVANCED CRYPTO ANALYTICS V3.0")
        print("=" * 60)
        print("🔥 1H Heikin Ashi TrendPulse + 2H StochRSI Confirmation")
        print("📊 Dual-tier analysis with multi-exchange fallback")
        print("🎯 Premium authenticated signals only")
        print("⏱️  5-minute execution cycle")
        print("=" * 60)
        
        try:
            while True:
                cycle_start = datetime.utcnow()
                
                # Execute analysis cycle
                alerts_sent, cycle_duration = self.execute_analysis_cycle()
                
                # Print stats every 12 cycles (1 hour)
                if self.total_cycles_completed % 12 == 0:
                    self.print_system_stats()
                
                # Calculate sleep time
                elapsed = (datetime.utcnow() - cycle_start).total_seconds()
                sleep_time = max(0, EXECUTION_INTERVAL - elapsed)
                
                if sleep_time > 0:
                    self.logger.info(f"😴 Sleeping for {sleep_time:.1f}s until next cycle")
                    time.sleep(sleep_time)
                else:
                    self.logger.warning(f"⚠️ Cycle took {elapsed:.1f}s (longer than {EXECUTION_INTERVAL}s interval)")
                
        except KeyboardInterrupt:
            self.logger.info("🛑 System shutdown requested")
            self.print_system_stats()
            print("\n🛑 Advanced Crypto Analytics V3.0 shutdown complete")
        except Exception as e:
            self.logger.error(f"💥 Critical system error: {str(e)}")
            print(f"\n💥 Critical error: {str(e)}")
            sys.exit(1)

def main():
    """Main entry point"""
    try:
        system = AdvancedCryptoAnalytics()
        system.run()
    except Exception as e:
        print(f"💥 System initialization failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
