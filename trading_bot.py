"""
Binance Spot Trading Bot
Strategy : EMA9/EMA21 crossover + RSI filter
Timeframe: 5 минут
Balance  : 10 тэнцүү хэсэгт хуваана (нэг position = 1/10)
"""

import os
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import logging
import threading
from datetime import datetime
from flask import Flask

TESTNET    = True          # True = Binance Testnet (аюулгүй туршилт)
                           # False = Бодит мөнгө

# Арилжаа хийх coin жагсаалт
SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "BNB/USDT",
    "SOL/USDT",
    "ADA/USDT",
]

TIMEFRAME      = "5m"    # 5 минутын свеч
BALANCE_SPLITS = 10      # Balance-ийг 10-д хуваана
STOP_LOSS_PCT  = 0.02    # 2% stop loss
TAKE_PROFIT_PCT= 0.03    # 3% take profit
CHECK_INTERVAL = 300     # 5 минут (секундээр)

# RSI хязгаар
RSI_BUY_MAX  = 65   # RSI энээс доош байвал BUY болно
RSI_SELL_MIN = 72   # RSI энээс дээш байвал SELL болно

# ─────────────────────────────────────────────
# 📋  LOG тохиргоо
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 🔌  EXCHANGE холболт
# ─────────────────────────────────────────────
def create_exchange():
    # Render-ийн Environment Variables-оос унших
    API_KEY = os.getenv('BINANCE_API_KEY')
    SECRET_KEY = os.getenv('BINANCE_SECRET')
    
    exchange = ccxt.binance({
        "apiKey": API_KEY,
        "secret": SECRET_KEY,
        "enableRateLimit": True,
        "options": {
            "defaultType": "spot"
        }
    })
    
    if TESTNET:
        exchange.set_sandbox_mode(True)
        log.info("🟡 TESTNET горимд ажиллаж байна")
    else:
        log.info("🔴 БОДИТ МӨНГӨТЭЙ ажиллаж байна")
        
    return exchange


# ─────────────────────────────────────────────
# 💰  BALANCE
# ─────────────────────────────────────────────
def get_usdt_balance(exchange: ccxt.binance) -> float:
    balance = exchange.fetch_balance()
    free = balance.get("USDT", {}).get("free", 0.0)
    return float(free)


def get_trade_amount(exchange: ccxt.binance) -> float:
    """Нийт balance-ийн 1/10"""
    total = get_usdt_balance(exchange)
    return round(total / BALANCE_SPLITS, 2)


# ─────────────────────────────────────────────
# 📊  INDICATOR тооцоолол
# ─────────────────────────────────────────────
def fetch_candles(exchange: ccxt.binance, symbol: str, limit: int = 100) -> pd.DataFrame:
    ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    return df

# ─────────────────────────────────────────────
# 🌐  RENDER ВЭБ СЕРВЕР (Унтахаас сэргийлэх)
# ─────────────────────────────────────────────
app = Flask('')

@app.route('/')
def home():
    return "Бот амжилттай ажиллаж байна!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ─────────────────────────────────────────────
# 🚀  ҮНДЭСЭН АЖИЛЛУУЛАХ ХЭСЭГ
# ─────────────────────────────────────────────
# Анхаар: Таны хуучин кодын хамгийн доор байсан run() функцийг 
# энд дуудаж өгөх хэрэгтэй. (Жишээлбэл доорх шиг)

def run():
    log.info("==================================================")
    log.info("🤖 Spot Trading Bot эхэллээ")
    log.info(f"   Symbols   : {SYMBOLS}")
    log.info(f"   Timeframe : {TIMEFRAME}")
    log.info(f"   SL / TP   : {STOP_LOSS_PCT*100}% / {TAKE_PROFIT_PCT*100}%")
    log.info("==================================================")
    
    exchange = create_exchange()
    
    while True:
        try:
            # Таны кодын үндсэн арилжаа хийдэг логик энд байна...
            # (Энд таны хуучин кодын while True доторх хэсэг үргэлжилнэ)
            pass 
        except Exception as e:
            log.error(f"Алдаа гарлаа: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # 1. Ботыг цаана нь (background) ажиллуулах
    bot_thread = threading.Thread(target=run)
    bot_thread.daemon = True
    bot_thread.start()
    
    # 2. Вэб серверийг наана нь ажиллуулах
    run_web_server()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df["ema9"]  = ta.ema(df["close"], length=9)
    df["ema21"] = ta.ema(df["close"], length=21)
    df["rsi"]   = ta.rsi(df["close"], length=14)
    return df


# ─────────────────────────────────────────────
# 📈  SIGNAL (BUY / SELL / HOLD)
# ─────────────────────────────────────────────
def get_signal(df: pd.DataFrame) -> str:
    """
    BUY  : EMA9 нь EMA21-ийг дээшээ огтолсон + RSI < RSI_BUY_MAX
    SELL : EMA9 нь EMA21-ийг доошоо огтолсон  + RSI > RSI_SELL_MIN
    HOLD : бусад тохиолдол
    """
if len(df) < 3:
        return "HOLD"
    cur  = df.iloc[-1]
    prev = df.iloc[-2]

    ema_cross_up   = (prev["ema9"] <= prev["ema21"]) and (cur["ema9"] > cur["ema21"])
    ema_cross_down = (prev["ema9"] >= prev["ema21"]) and (cur["ema9"] < cur["ema21"])

    rsi_ok_buy  = cur["rsi"] < RSI_BUY_MAX
    rsi_ok_sell = cur["rsi"] > RSI_SELL_MIN

    if ema_cross_up and rsi_ok_buy:
        return "BUY"
    if ema_cross_down or rsi_ok_sell:
        return "SELL"
    return "HOLD"


# ─────────────────────────────────────────────
# 🛒  ORDER
# ─────────────────────────────────────────────
def buy(exchange: ccxt.binance, symbol: str, usdt_amount: float, price: float) -> dict | None:
    try:
        qty = exchange.amount_to_precision(symbol, usdt_amount / price)
        order = exchange.create_market_buy_order(symbol, float(qty))
        log.info(f"✅ BUY  {symbol}  qty={qty}  price={price:.4f}  USDT={usdt_amount:.2f}")
        return {
            "symbol":       symbol,
            "qty":          float(qty),
            "entry_price":  price,
            "stop_loss":    round(price * (1 - STOP_LOSS_PCT), 6),
            "take_profit":  round(price * (1 + TAKE_PROFIT_PCT), 6),
            "opened_at":    datetime.utcnow().isoformat(),
        }
    except Exception as e:
        log.error(f"❌ BUY алдаа {symbol}: {e}")
        return None


def sell(exchange: ccxt.binance, position: dict, price: float, reason: str) -> None:
    symbol = position["symbol"]
    qty    = position["qty"]
    try:
        exchange.create_market_sell_order(symbol, qty)
        profit = round((price - position["entry_price"]) * qty, 4)
        pct    = round((price / position["entry_price"] - 1) * 100, 2)
        emoji  = "🟢" if profit >= 0 else "🔴"
        log.info(f"{emoji} SELL {symbol}  reason={reason}  profit={profit} USDT ({pct}%)")
    except Exception as e:
        log.error(f"❌ SELL алдаа {symbol}: {e}")


# ─────────────────────────────────────────────
# 🔄  НЭГ МӨЧЛӨГ (нэг символ)
# ─────────────────────────────────────────────
def process_symbol(
    exchange: ccxt.binance,
    symbol: str,
    position: dict | None,
    trade_usdt: float,
) -> dict | None:

    try:
        df = fetch_candles(exchange, symbol)
        df = add_indicators(df)
        signal = get_signal(df)
        price  = float(df.iloc[-1]["close"])
        rsi    = round(float(df.iloc[-1]["rsi"]), 1)
        log.info(f"  {symbol:<12} price={price:<12.4f} RSI={rsi:<6} signal={signal}")

        # Position байхгүй → BUY дохио хүлээх
        if position is None:
            if signal == "BUY":
                return buy(exchange, symbol, trade_usdt, price)
            return None

        # Position байна → Stop Loss / Take Profit / SELL дохио шалгах
        if price <= position["stop_loss"]:
            sell(exchange, position, price, "STOP_LOSS")
            return None
        if price >= position["take_profit"]:
            sell(exchange, position, price, "TAKE_PROFIT")
            return None
        if signal == "SELL":
            sell(exchange, position, price, "SIGNAL")
            return None

        return position  # Position хадгална

    except Exception as e:
        log.error(f"  {symbol} process алдаа: {e}")
        return position  # Алдааны үед position хадгална


# ─────────────────────────────────────────────
# 🚀  ГОЛ LOOP
# ─────────────────────────────────────────────
def run():
    log.info("=" * 50)
    log.info("🤖 Spot Trading Bot эхэллээ")
    log.info(f"   Symbols   : {SYMBOLS}")
    log.info(f"   Timeframe : {TIMEFRAME}")
    log.info(f"   SL / TP   : {STOP_LOSS_PCT*100}% / {TAKE_PROFIT_PCT*100}%")
    log.info("=" * 50)

    exchange  = create_exchange()
    positions = {sym: None for sym in SYMBOLS}   # хоосон position

    while True:
        # Python 3.13 хувилбарт тохируулан UTC цагийг засав
        now = datetime.now(datetime.UTC).strftime("%H:%M:%S")
        log.info(f"\n── {now} шалгаж байна ──")

        # 1/10 trade amount тооцоолно
        trade_usdt = get_trade_amount(exchange)
        balance    = get_usdt_balance(exchange)
        log.info(f"   Balance: {balance:.2f} USDT  |  Trade unit: {trade_usdt:.2f} USDT")

        # Хангалттай мөнгө байгаа эсэх
        if trade_usdt < 5:
            log.warning("⚠️  Balance хэтэрхий бага (< 50 USDT). Хүлээж байна...")
        else:
            for symbol in SYMBOLS:
                positions[symbol] = process_symbol(
                    exchange,
                    symbol,
                    positions[symbol],
                    trade_usdt,
                )

        log.info(f"   ⏱️  {CHECK_INTERVAL // 60} минут хүлээж байна...\n")
        time.sleep(CHECK_INTERVAL)


# ─────────────────────────────────────────────
if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        log.info("\n🛑 Bot зогссон (Ctrl+C)")
      import threading
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Бот амжилттай ажиллаж байна!"

def run_web_server():
    # Render-ийн шаарддаг портыг унших (өгөгдөөгүй бол 8080)
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Хэрэв таны үндсэн функц run() нэртэй бол:
if __name__ == "__main__":
    # 1. Ботыг цаана нь (background) тасралтгүй ажиллуулах
    bot_thread = threading.Thread(target=run) # 'run' нь таны ботыг ажиллуулдаг үндсэн функцийн нэр байна
    bot_thread.daemon = True
    bot_thread.start()
    
    # 2. Вэб серверийг наана нь ажиллуулах (Render-ийг унтраахаас сэргийлнэ)
    run_web_server()

