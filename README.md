# 📈  AI Trading Bot (embedding + OpenAI + MetaTrader 5 )

# (embedding + OpenAI + MetaTrader 5 + binary )

This project is an **automated trading bot** that connects **MetaTrader 5 (MT5)** with **OpenAI**.  
It fetches the last 10 candlesticks from MT5, uses OpenAI to **predict the next move** (buy/sell/hold), and then places a **market order** automatically with stop-loss and take-profit.

---

## 📥 Prerequisites

### 🔹 Must Install Ollama + .NET
- [Download Ollama](https://ollama.com/download)  
- [Download .NET 6.0](https://dotnet.microsoft.com/en-us/download/dotnet/6.0)  

---


## 🚀 Features
- 🔑 Secure login to **MetaTrader 5** with `.env` credentials  
- 📊 Fetches **last 10 × 15-min candles** for analysis  
- 🤖 Uses **OpenAI GPT models** (e.g., `gpt-4o-mini`) for predictions  
- 📦 Returns clean **JSON response** with trading signal:
  ```json
  {
    "signal": "buy",
    "confidence": 0.82,
    "price_target_usd": 1.0952,
    "take_profit_pips": 20,
    "stop_loss_pips": 100,
    "reason": "EURUSD is showing bullish momentum after support bounce."
  }

📊 Workflow Diagram

        ┌─────────────┐
        │   MetaTrader│
        │   5 (MT5)   │
        └──────┬──────┘
               │
        Fetch candles
               │
               ▼
        ┌─────────────┐
        │   
            embedding │
        │  Prediction │
        └──────┬──────┘
        ┌─────────────┐
        │   
            OpenAI    │
        │  Prediction │
        └──────┬──────┘
               │
         JSON Signal
               │
               ▼
        ┌─────────────┐
        │   Trading   │
        │    Bot      │
        └──────┬──────┘
               │
         Place Order

✅ Logged in to account 1234567 on Broker-Server
✅ Obtained embedding (len=1536)
Signal: buy | Confidence: 0.82 | Target: 1.0952 | TP: 20 | SL: 100
Reason: EURUSD is showing bullish momentum after support bounce.
✅ Valid tick data: Bid=1.0945, Ask=1.0947
✅ Order executed successfully

1️⃣ Clone the Repository
``` 

[https://github.com/Mdbaizidtanvir/Automated-Trading-bot-high-frequency.git]
cd mt5-ai-trading-bot

pip install -r requirements.txt


```


# 2️⃣ Create .env File
``` 
OPENAI_API_KEY=your_openai_api_key
MT5_ACCOUNT=1234567
MT5_PASSWORD=your_mt5_password
MT5_SERVER=Broker-Server

LOT_SIZE=0.01
DEVIATION=20
TP_PIPS=20
SL_PIPS=100
SYMBOL=EURUSD

```


#3️⃣ Run the Bot

```
python app.py

```


---
``
python pok.py 

python qot.py 

 ```



