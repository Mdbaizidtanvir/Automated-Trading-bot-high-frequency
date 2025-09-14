📈  AI Trading Bot (OpenAI + MetaTrader 5 + binary )

This project is an automated trading bot that connects MetaTrader 5 (MT5) with OpenAI.
It fetches the last 10 candlesticks from MT5, uses OpenAI to predict the next move (buy/sell/hold), and then places a market order automatically with stop-loss and take-profit.

🚀 Features

Connects securely to MetaTrader 5 using account credentials.

Fetches the last 10 × 15-minute candles for analysis.

Uses OpenAI GPT models (e.g., gpt-4o-mini) to predict the next market move.

AI returns a structured JSON response:

{
  "signal": "buy",
  "confidence": 0.82,
  "price_target_usd": 1.0952,
  "take_profit_pips": 20,
  "stop_loss_pips": 100,
  "reason": "EURUSD is showing bullish momentum after support bounce."
}


Automatically places Buy/Sell orders in MT5 with defined TP & SL.

Exits safely if the signal is "hold".

⚙️ Requirements

Python 3.8+

MetaTrader 5 account (login credentials)

OpenAI API key

Python Packages
pip install MetaTrader5 openai python-dotenv pandas

📂 Project Setup

Clone the repo

git clone https://github.com/your-username/mt5-ai-trading-bot.git
cd mt5-ai-trading-bot


Create .env file in the project root with your credentials:

OPENAI_API_KEY=your_openai_api_key
MT5_ACCOUNT=1234567
MT5_PASSWORD=your_mt5_password
MT5_SERVER=Broker-Server
LOT_SIZE=0.01
DEVIATION=20
TP_PIPS=20
SL_PIPS=100
SYMBOL=EURUSD


Run the bot

python trade_bot.py

🛠 How It Works

Initialize MetaTrader 5 and log in.

Retrieve 10 recent 15-min candles.

Send the candlestick data to OpenAI for prediction.

Parse the AI’s JSON response.

If "buy" or "sell" → place a market order with TP/SL.

If "hold" → do nothing.

Print results and shut down safely.

⚠️ Disclaimer

This bot is for educational purposes only.
⚠️ Trading is risky — use at your own responsibility. Test with demo accounts before live trading.
