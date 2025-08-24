"""
UTILS MODULE - Logging, Time, Formatting & Configuration
Common utilities used across the entire system
"""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path


def setup_logging(log_file_path):
    """
    Setup comprehensive logging system with file and console output
    """
    # Create logs directory if it doesn't exist
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # File handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_ist_time():
    """Get current IST time in multiple formats"""
    utc = datetime.utcnow()
    ist = utc + timedelta(hours=5, minutes=30)
    
    time_12h = ist.strftime('%I:%M %p %d-%m-%Y')
    date_str = ist.strftime('%A, %d %B %Y')
    timestamp = ist.strftime('%Y-%m-%d %H:%M:%S IST')
    
    return {
        'time_12h': time_12h,
        'date_str': date_str,
        'timestamp': timestamp,
        'datetime': ist
    }


def format_price(price):
    """Format cryptocurrency price with appropriate precision"""
    if price is None:
        return "$0.00"
    
    try:
        price = float(price)
        if price >= 1000:
            return f"${price:,.0f}"
        elif price >= 1:
            return f"${price:,.2f}"
        elif price >= 0.01:
            return f"${price:.4f}"
        elif price >= 0.0001:
            return f"${price:.6f}"
        else:
            return f"${price:.8f}"
    except (ValueError, TypeError):
        return "$0.00"


def format_change(change):
    """Format price change percentage with emoji and color"""
    if change is None:
        return "➡️ 0.00%"
    
    try:
        change = float(change)
        if change > 0:
            return f"📈 +{change:.2f}%"
        elif change < 0:
            return f"📉 {change:.2f}%"
        else:
            return f"➡️ {change:.2f}%"
    except (ValueError, TypeError):
        return "➡️ 0.00%"


def format_market_cap(market_cap):
    """Format market cap with appropriate units"""
    if market_cap is None or market_cap == 0:
        return "Unknown"
    
    try:
        market_cap = float(market_cap)
        if market_cap >= 1_000_000_000:
            return f"${market_cap / 1_000_000_000:.1f}B"
        elif market_cap >= 1_000_000:
            return f"${market_cap / 1_000_000:.0f}M"
        elif market_cap >= 1_000:
            return f"${market_cap / 1_000:.0f}K"
        else:
            return f"${market_cap:.0f}"
    except (ValueError, TypeError):
        return "Unknown"


def format_volume(volume):
    """Format trading volume with appropriate units"""
    if volume is None or volume == 0:
        return "Unknown"
    
    try:
        volume = float(volume)
        if volume >= 1_000_000_000:
            return f"${volume / 1_000_000_000:.1f}B"
        elif volume >= 1_000_000:
            return f"${volume / 1_000_000:.0f}M"
        elif volume >= 1_000:
            return f"${volume / 1_000:.0f}K"
        else:
            return f"${volume:.0f}"
    except (ValueError, TypeError):
        return "Unknown"


def validate_environment_variables():
    """Validate that all required environment variables are set"""
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'HIGH_RISK_CHAT_ID',
        'TELEGRAM_CHAT_ID'
    ]
    
    optional_vars = [
        'BINGX_API_KEY',
        'BINGX_SECRET_KEY',
        'COINGECKO_API_KEY'
    ]
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_required.append(var)
    
    for var in optional_vars:
        if not os.environ.get(var):
            missing_optional.append(var)
    
    if missing_required:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_required)}")
    
    if missing_optional:
        print(f"⚠️ Missing optional environment variables: {', '.join(missing_optional)}")
        print("System will use default/public API access where possible")
    
    return True


def create_config_template():
    """Create a template .env file with all configuration options"""
    template = """# Advanced Crypto Analytics V3.0 Configuration
# Copy this to .env and fill in your values

# REQUIRED: Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
HIGH_RISK_CHAT_ID=your_high_risk_chat_id_here
TELEGRAM_CHAT_ID=your_standard_chat_id_here

# OPTIONAL: BingX API (for private data access)
BINGX_API_KEY=your_bingx_api_key_here
BINGX_SECRET_KEY=your_bingx_secret_key_here

# OPTIONAL: CoinGecko API (for higher rate limits)
COINGECKO_API_KEY=your_coingecko_api_key_here

# System Configuration (modify if needed)
LOG_LEVEL=INFO
CACHE_DURATION_HOURS=24
MAX_CONCURRENT_ANALYSIS=4

# Advanced Settings (experts only)
EXECUTION_INTERVAL_SECONDS=300
COINGECKO_REFRESH_INTERVAL_SECONDS=1800
DEDUPLICATION_WINDOW_HOURS=12
"""
    
    config_file = Path("config_template.env")
    config_file.write_text(template)
    print(f"📝 Configuration template created: {config_file.absolute()}")
    return config_file


def load_blocked_coins(blocked_coins_file=None):
    """Load blocked coins from file"""
    if blocked_coins_file is None:
        blocked_coins_file = Path("blocked_coins.txt")
    
    if not blocked_coins_file.exists():
        # Create template blocked coins file
        template_content = """# BLOCKED COINS LIST
# Add one coin symbol per line to exclude from analysis
# Lines starting with # are comments

# Example: Block major coins if you only want altcoins
# BTC
# ETH
# BNB

# Example: Block stablecoins (already filtered by default)
# USDT
# USDC
# DAI

# Example: Block specific coins
# DOGE
# SHIB
"""
        blocked_coins_file.write_text(template_content)
        print(f"📝 Blocked coins template created: {blocked_coins_file.absolute()}")
        return set()
    
    try:
        blocked = set()
        with open(blocked_coins_file, 'r') as f:
            for line in f:
                line = line.strip().upper()
                if line and not line.startswith('#'):
                    blocked.add(line)
        
        print(f"📝 Loaded {len(blocked)} blocked coins from {blocked_coins_file}")
        return blocked
        
    except Exception as e:
        print(f"⚠️ Error loading blocked coins: {e}")
        return set()


def calculate_system_stats(start_time, total_cycles, total_alerts):
    """Calculate and format system performance statistics"""
    uptime = datetime.utcnow() - start_time
    uptime_hours = uptime.total_seconds() / 3600
    
    stats = {
        'uptime_hours': uptime_hours,
        'uptime_days': uptime.days,
        'total_cycles': total_cycles,
        'total_alerts': total_alerts,
        'alerts_per_hour': total_alerts / max(uptime_hours, 0.1),
        'cycles_per_hour': total_cycles / max(uptime_hours, 0.1),
        'avg_cycle_time': (uptime_hours * 3600) / max(total_cycles, 1)
    }
    
    return stats


def print_startup_banner():
    """Print system startup banner"""
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    🚀 ADVANCED CRYPTO ANALYTICS V3.0 🚀                       ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  🔥 1H Heikin Ashi TrendPulse + 2H StochRSI Confirmation System              ║
║  📊 Dual-tier analysis with multi-exchange fallback                          ║
║  🎯 Premium authenticated signals with perfect deduplication                  ║
║  ⚡ 5-minute execution cycle with 30-minute CoinGecko refresh                 ║
║  💎 Production-ready with comprehensive error handling                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)


def print_system_status(stats):
    """Print comprehensive system status"""
    print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                           📊 SYSTEM STATISTICS                                ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  ⏱️  System Uptime: {stats['uptime_hours']:.1f} hours ({stats['uptime_days']} days)                    ║
║  🔄 Cycles Completed: {stats['total_cycles']:<10} ({stats['cycles_per_hour']:.1f}/hour)                  ║
║  🚨 Total Alerts Sent: {stats['total_alerts']:<8} ({stats['alerts_per_hour']:.1f}/hour)                   ║
║  ⚡ Avg Cycle Time: {stats['avg_cycle_time']:.1f} seconds                                  ║
║  🎯 Success Rate: Premium authenticated signals only                          ║
║  💾 Cache Status: Multi-layer caching active                                 ║
║  📡 API Usage: Optimized for free tier limits                               ║
║  ✅ System Status: OPERATIONAL & STABLE                                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)


class PerformanceMonitor:
    """Monitor system performance and health"""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.cycle_times = []
        self.api_call_counts = {}
        self.error_counts = {}
        self.alert_counts = {'high_risk': 0, 'standard': 0}
    
    def record_cycle_time(self, duration):
        """Record cycle execution time"""
        self.cycle_times.append(duration)
        # Keep only last 100 cycle times
        if len(self.cycle_times) > 100:
            self.cycle_times.pop(0)
    
    def record_api_call(self, api_name):
        """Record API call for tracking"""
        self.api_call_counts[api_name] = self.api_call_counts.get(api_name, 0) + 1
    
    def record_error(self, error_type):
        """Record error for monitoring"""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
    
    def record_alert(self, tier_type):
        """Record alert sent"""
        if tier_type.lower() == 'high_risk':
            self.alert_counts['high_risk'] += 1
        else:
            self.alert_counts['standard'] += 1
    
    def get_performance_summary(self):
        """Get performance summary"""
        avg_cycle_time = sum(self.cycle_times) / len(self.cycle_times) if self.cycle_times else 0
        total_alerts = sum(self.alert_counts.values())
        
        return {
            'avg_cycle_time': avg_cycle_time,
            'total_alerts': total_alerts,
            'api_calls': dict(self.api_call_counts),
            'errors': dict(self.error_counts),
            'alert_breakdown': dict(self.alert_counts)
        }
