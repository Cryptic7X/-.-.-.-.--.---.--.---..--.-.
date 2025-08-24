"""
SCHEDULED MAIN - GitHub Actions Optimized Version
Modified for scheduled runs instead of continuous execution
Perfect for hybrid 0,5,15,30,45-minute schedule
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import logging

# Custom modules
from data_manager import CoinGeckoManager, MultiExchangeManager
from analyzers import TrendPulseAnalyzer, StochRSICalculator, HeikinAshiConverter
from alert_system import TelegramAlertManager, ChartURLResolver, DeduplicationManager
from utils import setup_logging, format_price

# GitHub Actions optimized config
MAX_WORKERS = 2
GITHUB_ACTIONS_MODE = os.environ.get('GITHUB_ACTIONS_MODE', '').lower() == 'true'

# Paths
BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "cache"
LOGS_DIR = BASE_DIR / "logs"

CACHE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

class GitHubActionsAnalytics:
    def __init__(self):
        self.logger = setup_logging(LOGS_DIR / "github_actions.log")
        self.logger.info("🚀 GitHub Actions Crypto Analytics V3.0 - Scheduled Mode")
        self.coingecko = CoinGeckoManager(CACHE_DIR)
        self.exchange = MultiExchangeManager()
        self.tp = TrendPulseAnalyzer()
        self.stoch = StochRSICalculator()
        self.ha = HeikinAshiConverter()
        self.dedupe = DeduplicationManager(CACHE_DIR)
        self.chart = ChartURLResolver(CACHE_DIR)
        self.telegram = TelegramAlertManager()
        self.start_time = datetime.utcnow()
        self.found = 0
        self.sent = 0

    def get_coin_data(self):
        self.logger.info("🌐 Fetching fresh CoinGecko data")
        data, calls = self.coingecko.get_dual_tier_coins()
        self.logger.info(f"✅ Retrieved {len(data['high_risk'])+len(data['standard'])} coins ({calls} calls)")
        return data

    def fetch_data(self, symbol):
        timeframes = {'1h':50, '2h':100}
        return self.exchange.get_multi_timeframe_data(symbol, timeframes)

    def analyze(self, coin, tier):
        symbol=coin['symbol']
        market = self.fetch_data(symbol)
        if not market: return None, f"❌ No data: {symbol}"
        ha_df = self.ha.convert(market['1h'])
        if ha_df is None: return None, f"❌ HA fail: {symbol}"
        tp_sig = self.tp.analyze(ha_df, tier)
        if not tp_sig['has_signal']: return None, f"📊 No TP: {symbol}"
        stoch = self.stoch.calculate(market['2h'])
        if not stoch: return None, f"❌ Stoch fail: {symbol}"
        k,d = stoch['current_k'], stoch['current_d']
        action=tp_sig['signal_type']
        if action=='BUY':
            confirmed = k<20 and d<20
            reason = f"Stoch2H_Ovsl(K:{k:.1f},D:{d:.1f})"
        else:
            confirmed = k>80 and d>80
            reason = f"Stoch2H_Ovbt(K:{k:.1f},D:{d:.1f})"
        if not confirmed: return None, f"📊 No Stoch: {symbol}"
        sig={**tp_sig,'stoch_rsi_k':k,'stoch_rsi_d':d,'confirmation_reason':reason,'candle_timestamp':ha_df.index[-2]}
        return {'coin':coin,'signal':sig,'tier':tier}, f"✅ {action}: {symbol} ({reason})"

    def process_signals(self, results):
        sent=0
        for res in results:
            coin=res['coin']; sig=res['signal']; tier=res['tier']
            if self.dedupe.is_duplicate(coin,sig):
                self.logger.info(f"🔄 Duplicate: {coin['symbol']}")
                continue
            url, ex = self.chart.get_working_chart_url(coin['symbol'])
            sig['chart_url']=url; sig['chart_exchange']=ex
            if self.telegram.send_alert(coin,sig,tier):
                self.dedupe.mark_sent(coin,sig); sent+=1
                self.logger.info(f"✅ Alert: {coin['symbol']} {sig['signal_type']} @ {format_price(coin['current_price'])}")
                if sent<len(results): time.sleep(10)
        return sent

    def run(self):
        self.logger.info("🔄 Scheduled analysis start")
        data = self.get_coin_data()
        all_coins = data['high_risk']+data['standard']
        results=[]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = [ex.submit(self.analyze,c,'HIGH_RISK') for c in data['high_risk']]
            futures += [ex.submit(self.analyze,c,'STANDARD') for c in data['standard']]
            for f in futures:
                try:
                    r,log=f.result(timeout=30)
                    if r: results.append(r)
                    self.logger.info(log)
                except Exception as e:
                    self.logger.error(f"Timeout/Error: {e}")
        self.found=len(results)
        self.sent=self.process_signals(results)
        dur=(datetime.utcnow()-self.start_time).total_seconds()
        self.logger.info(f"🎉 Completed: {self.sent} alerts sent in {dur:.1f}s")

def main():
    print("🚀 Crypto Analytics V3.0 - GitHub Actions Mode")
    sys.exit( GitHubActionsAnalytics().run()>=0 )

if __name__=="__main__":
    main()
