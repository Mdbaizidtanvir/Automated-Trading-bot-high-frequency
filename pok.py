import MetaTrader5 as mt5
from datetime import datetime
import pandas as pd
import ollama
import json
import re
import time
import os
import openai 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from driver import get_driver


from dotenv import load_dotenv
import os

load_dotenv()  # read .env file





# =====================
# 1️⃣ Initialize WebDriver
# =====================
driver = get_driver()
print("✅ Driver launched")

driver.get("https://pocketoption.com/en/cabinet/demo-high-low/?")
print("✅ Opened pocketoption")

wait = WebDriverWait(driver, 30)

# =====================
# 2️⃣ Initialize MT5
# =====================
if not mt5.initialize():
    print("MT5 initialize() failed")
    mt5.shutdown()
    exit()

# 🔄 Function to get active asset from Quotex tab
# =====================
def get_active_asset():
    try:
        # Locate the active asset container
        active_item = wait.until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "#js-assets-favorites-slider .assets-favorites-item.assets-favorites-item--active"
            ))
        )

        # Find the label inside the active item
        label_element = active_item.find_element(By.CSS_SELECTOR, ".assets-favorites-item__label")
        asset_name = label_element.text.strip()

        # Map Quotex/PO format (EUR/USD) -> MT5 (EURUSD)
        return asset_name.replace("/", "")
    
    except Exception as e:
        print("⚠️ Could not detect active asset:", e)
        return None

# =====================
# 3️⃣ Initialize OpenAI
# =====================
client = openai.api_key =os.getenv("OPENAI_API_KEY")

# =====================
# 4️⃣ Trading functions
# =====================
def click_buy():
    try:
        btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="put-call-buttons-chart-1"]/div/div[2]/div[2]/div[1]/a')))
        btn.click()
        print("✅ Buy button clicked")
    except Exception as e:
        print("⚠️ Could not click Buy:", e)

def click_sell():
    try:
        btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="put-call-buttons-chart-1"]/div/div[2]/div[2]/div[2]/a')))
        btn.click()
        print("✅ Sell button clicked")
    except Exception as e:
        print("⚠️ Could not click Sell:", e)

# =====================
# 5️⃣ System message template
# =====================
system_message = "\n".join([
    "ROLE: You are a hyper-cautious, data-bound binary trading assistant.",
    "OUTPUT: Emit ONE JSON object only. No prose, no code fences.",
    "SCOPE: Use ONLY user-provided candles and embedding. Do NOT rely on external knowledge.",
    "EVIDENCE STANDARD: If evidence is insufficient or conflicting, choose 'hold'. Never guess.",
    "CERTAINTY: Never claim certainty. Confidence must reflect observable evidence.",
    "HALLUCINATION GUARDRAILS:",
    "- Do not invent indicators, prices, timestamps, or volumes not present in input.",
    "- If required value cannot be grounded, set signal='hold', confidence<=0.20, price_target_usd=last_close.",
    "SCHEMA: { signal: buy/sell/hold, confidence: number, price_target_usd: number, reason: string }",
    "VALIDATION RULES: confidence [0,1], reason <=200 chars, no NaN/Infinity, keys exact.",
    "DECISION POLICY: Strong micro-trend => buy/sell, conflicting => hold, embeddings weighted if corroborated."
])

# =====================
# 6️⃣ Real-time trading loop
# =====================
seen_candles = set()
PERIOD = 60  # 1-minute candles
current_symbol = None

try:
    while True:
        
        # 1. Check current active tab asset
        new_symbol = get_active_asset()
        if new_symbol and new_symbol != current_symbol:
            current_symbol = new_symbol
            symbol = current_symbol
            print(f"🔄 Active tab changed → Using symbol: {symbol}")

        if not current_symbol:
            print("⚠️ No active symbol found, retrying...")
            time.sleep(1)
            continue
        
        # Fetch last 10 1-min candles
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 10)
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df = df[['open', 'high', 'low', 'close']]

        # Prepare prompt
        prompt = "\n".join([f"{t.strftime('%Y-%m-%d %H:%M')} O:{r['open']} H:{r['high']} L:{r['low']} C:{r['close']}"
                            for t, r in df.iterrows()])

        # Generate embeddings
        embedding_vector = ollama.embeddings(model="nomic-embed-text", prompt=prompt)["embedding"]

        # Prepare user message
        user_message = f"""
SYMBOL: {symbol}
TIMEFRAME: 1-minute (last 10 candles; newest last)

CANDLES (ISO_TIME, open, high, low, close):
{prompt}

EMBEDDING (first 50 dims):
{embedding_vector[:50]}

TASK:
- Determine short-term direction using ONLY the data above.
- If uncertain or inputs anomalous, output hold with low confidence and set price_target_usd to the most recent close.
RESPOND WITH ONLY VALID JSON.
"""

        # Call OpenAI
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0,
            presence_penalty=0,
            frequency_penalty=0
        )

        response_text = response.choices[0].message.content

        # Parse JSON safely
        try:
            pred = json.loads(response_text)
        except json.JSONDecodeError:
            raw = response_text
            pred = {
                "signal": re.search(r'"signal"\s*:\s*"(\w+)"', raw).group(1) if re.search(r'"signal"\s*:\s*"(\w+)"', raw) else "hold",
                "confidence": float(re.search(r'"confidence"\s*:\s*([0-9.]+)', raw).group(1)) if re.search(r'"confidence"\s*:\s*([0-9.]+)', raw) else 0,
                "price_target_usd": float(re.search(r'"price_target_usd"\s*:\s*([0-9.]+)', raw).group(1)) if re.search(r'"price_target_usd"\s*:\s*([0-9.]+)', raw) else df['close'][-1],
                "reason": re.search(r'"reason"\s*:\s*"([^"]+)"', raw).group(1) if re.search(r'"reason"\s*:\s*"([^"]+)"', raw) else "Parsing failed"
            }

        print("ChatGPT prediction:", pred, "\n")


        # Take action once per candle
        latest_candle_time = int(df.index[-1].timestamp())
        if latest_candle_time not in seen_candles:
            seen_candles.add(latest_candle_time)
            print(f"New Candle at {df.index[-1]}, executing trade based on signal ")
            
            if pred["signal"] == "buy":
                click_buy()
            elif pred["signal"] == "sell":
                click_sell()
            else:
                print("⚠️ Hold signal, no trade executed.")

        # Wait before next iteration
        time.sleep(5)

except KeyboardInterrupt:
    print("⏹️ Real-time trading loop stopped by user.")

finally:
    mt5.shutdown()
