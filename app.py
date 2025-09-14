import os
import json
import time
from datetime import datetime

import pandas as pd
import MetaTrader5 as mt5
import openai


from dotenv import load_dotenv
import os

load_dotenv()  # read .env file

openai.api_key = os.getenv("OPENAI_API_KEY")
account   = int(os.getenv("MT5_ACCOUNT"))
password  = os.getenv("MT5_PASSWORD")
server    = os.getenv("MT5_SERVER")

lot_size  = float(os.getenv("LOT_SIZE", "0.01"))
deviation = int(os.getenv("DEVIATION", "20"))
Tp_pips   = int(os.getenv("TP_PIPS", "20"))
Sl_pips   = int(os.getenv("SL_PIPS", "100"))
symbol    = os.getenv("SYMBOL", "EURUSD")

# =====================
# Initialize MT5 and Login
# =====================
if not mt5.initialize():
    print("❌ MT5 initialization failed")
    quit()

authorized = mt5.login(account, password=password, server=server)
if not authorized:
    print("❌ Login failed. Check account/password/server.")
    mt5.shutdown()
    quit()

print(f"✅ Logged in to account {account} on {server}")

# =====================
# Fetch last 10 intraday 15-min candles (MT5)
# =====================
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 10)

if rates is None or len(rates) == 0:
    print("❌ No data retrieved from MT5. Exiting.")
    mt5.shutdown()
    quit()

df = pd.DataFrame(rates)
df["time"] = pd.to_datetime(df["time"], unit="s")
df = df.rename(columns={
    "open": "Open",
    "high": "High",
    "low": "Low",
    "close": "Close",
    "tick_volume": "Volume"
})

# Build a compact textual prompt of recent candles
prompt = "10 most recent 15-min candlestick history:\n"
for _, row in df.iterrows():
    prompt += f"{row['time'].strftime('%Y-%m-%d %H:%M')} O:{row['Open']} H:{row['High']} L:{row['Low']} C:{row['Close']}\n"

# =====================
# Get embedding from OpenAI (optional, mirrors your previous embedding step)
# =====================
try:
    emb_resp = openai.Embedding.create(
        model="text-embedding-3-small",  # or "text-embedding-3-large" depending on needs
        input=prompt
    )
    embedding_vector = emb_resp["data"][0]["embedding"]
    print("✅ Obtained embedding (len={} )".format(len(embedding_vector)))
except Exception as e:
    print("⚠️ Embedding request failed:", e)
    embedding_vector = None

# =====================
# Ask OpenAI to predict the next move and return JSON
# =====================
# We force the assistant to return JSON only — later we parse it safely.
# You can change the model to gpt-4o, gpt-4o-mini, gpt-4, etc. depending on availability & billing.
chat_messages = [
    {"role": "system", "content": "You are a trading assistant AI. Answer strictly in valid JSON with the fields specified."},
    {"role": "user", "content": (
        "Here is the 10 most recent 15-min candlestick history:\n\n"
        f"{prompt}\n\n"
        "Also, if available, embedding vector first 50 dims:\n"
        f"{(embedding_vector[:50] if embedding_vector is not None else 'None')}\n\n"
        "Please predict the next move for EURUSD. **Return only JSON** with these keys:\n"
        '- \"signal\": one of \"buy\", \"sell\", or \"hold\"\n'
        '- \"confidence\": number between 0 and 1\n'
        '- \"price_target_usd\": estimated target price (float)\n'
        '- \"take_profit_pips\": integer suggested TP in pips\n'
        '- \"stop_loss_pips\": integer suggested SL in pips\n'
        '- \"reason\": short explanation (1-2 sentences)\n\n'
        "IMPORTANT: output must be valid JSON (no surrounding backticks or extra commentary)."
    )}
]

try:
    completion = openai.ChatCompletion.create(
        model="gpt-4o-mini",     # choose an available model for your account (gpt-4o-mini, gpt-4o, gpt-4, gpt-3.5-turbo, etc.)
        messages=chat_messages,
        temperature=0.0,
        max_tokens=400
    )
    raw_text = completion["choices"][0]["message"]["content"].strip()
except Exception as e:
    print("⚠️ OpenAI chat completion failed:", e)
    raw_text = ""

# =====================
# Parse the JSON safely
# =====================
pred = {"signal": "hold", "confidence": 0.0, "price_target_usd": None,
        "reason": "Parsing failed or model error", "take_profit_pips": 10, "stop_loss_pips": 10}

if raw_text:
    # Try to extract a JSON object inside the text robustly
    try:
        # If model returns code fencing or extra text, attempt to find the first { ... } block
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start != -1 and end != -1 and end > start:
            json_text = raw_text[start:end]
        else:
            json_text = raw_text

        pred = json.loads(json_text)
    except Exception as e:
        print("⚠️ JSON parse failed:", e)
        print("Raw model output:\n", raw_text)

print(f"Signal: {pred.get('signal')} | Confidence: {pred.get('confidence')} | "
      f"Target: {pred.get('price_target_usd')} | TP: {pred.get('take_profit_pips')} | SL: {pred.get('stop_loss_pips')}")
print("Reason:", pred.get("reason"))

# =====================
# Symbol check & Market Watch
# =====================
if not mt5.symbol_select(symbol, True):
    print(f"❌ Symbol {symbol} not available in Market Watch.")
    mt5.shutdown()
    quit()

# =====================
# Wait for valid tick data
# =====================
tick = None
for attempt in range(20):
    tick = mt5.symbol_info_tick(symbol)
    if tick is not None and tick.ask != tick.bid:
        break
    print(f"⏳ Waiting for valid tick data for {symbol}... attempt {attempt+1}")
    time.sleep(1)

if tick is None or tick.ask == tick.bid:
    print(f"❌ Still no valid tick data for {symbol}. Cannot trade.")
    mt5.shutdown()
    quit()

print(f"✅ Valid tick data: Bid={tick.bid}, Ask={tick.ask}")

# =====================
# Prepare market order (respecting hold)
# =====================
ai_signal = (pred.get('signal') or "hold").lower()




if ai_signal not in ("buy", "sell"):
    print("No actionable AI signal (buy/sell). Exiting without placing order.")
    mt5.shutdown()
    quit()

order_type = mt5.ORDER_TYPE_BUY if ai_signal == "buy" else mt5.ORDER_TYPE_SELL
price      = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

point = mt5.symbol_info(symbol).point
tp = price + Tp_pips * point if order_type == mt5.ORDER_TYPE_BUY else price - Tp_pips * point
sl = price - Sl_pips * point if order_type == mt5.ORDER_TYPE_BUY else price + Sl_pips * point

request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbol,
    "volume": lot_size,
    "type": order_type,
    "price": price,
    "sl": sl,
    "tp": tp,
    "deviation": deviation,
    "magic": 202003,
    "comment": "Python Auto Trade (OpenAI)",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_IOC
}

# =====================
# Send the order
# =====================
result = mt5.order_send(request)

if result is None:
    print("❌ order_send returned None (no response).")
elif getattr(result, "retcode", None) != mt5.TRADE_RETCODE_DONE:
    print(f"❌ Order failed, retcode = {getattr(result,'retcode', None)}")
    # If result has request details (sometimes returned), print them
    if hasattr(result, "request"):
        print("Request details:", result.request)
    else:
        print("Raw result:", result)
else:
    print("✅ Order executed successfully:", result)

# =====================
# Shutdown MT5
# =====================
mt5.shutdown()
