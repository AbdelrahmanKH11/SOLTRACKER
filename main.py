import os
import json
import requests
import asyncio
import threading
import time
from flask import Flask, request, jsonify
from telegram import Bot
from datetime import datetime

# 🔹 Your Telegram Bot Token & Chat ID
TELEGRAM_BOT_TOKEN = "7841195146:AAF4DbFsAqphttY1Tm3lWsqmTJh53nm_ykQ"
TELEGRAM_CHAT_ID = 1119850623  # Replace with your actual chat ID

# 🔹 Helius API Key
HELIUS_API_KEY = "b8c7e3e5-d0ff-4532-8f28-84031a29a356"

# 🔹 Wallets File
WALLETS_FILE = "Kol_wallets.txt"

# 🔹 Initialize Flask App
app = Flask(__name__)

# 🔹 Route: Home Page for Debugging
@app.route("/", methods=["GET"])
def home():
    return "Flask server is running!"

# 🔹 Route: Handle Webhooks from Helius API
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        print("🔹 Headers Received:", request.headers)
        
        # Read raw data before parsing
        raw_data = request.data.decode("utf-8")
        print("🔹 Raw Webhook Data Received:", raw_data)

        # Try parsing JSON
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            print("❌ JSON Parsing Error: Malformed request from Helius")
            return jsonify({"error": "Malformed JSON"}), 400

        # Validate JSON format
        if not isinstance(data, list):
            print("❌ Invalid JSON structure: Expected a list")
            return jsonify({"error": "Invalid JSON format"}), 400

        # Send quick response to Helius
        print("✅ Webhook Received, Processing in Background")
        threading.Thread(target=process_transaction, args=({"transactions": data},)).start()
        return jsonify({"status": "received"}), 200

    except Exception as e:
        print(f"❌ Webhook Error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# 📌 Load Wallets from File
def load_wallets():
    try:
        with open(WALLETS_FILE, "r", encoding="utf-8") as file:
            wallets_data = json.load(file)
        return {wallet["address"]: wallet for wallet in wallets_data}
    except Exception as e:
        print(f"❌ Error loading wallets: {e}")
        return {}

# 📌 Get Token Info (Name & Price in SOL) from Helius
def get_token_info(token_mint):
    url = f"https://api.helius.xyz/v0/tokens/prices?api-key={HELIUS_API_KEY}"

    try:
        response = requests.post(url, json={"tokens": [token_mint]})
        data = response.json()

        if "prices" in data and token_mint in data["prices"]:
            token_data = data["prices"][token_mint]
            return token_data.get("name", "Unknown Token"), token_data["price"]
        return "Unknown Token", None

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error fetching token info from Helius: {e}")
        return "Unknown Token", None

# 📌 Get SOL Price in USD
def get_sol_price_in_usd():
    url = f"https://api.helius.xyz/v0/tokens/prices?api-key={HELIUS_API_KEY}"

    try:
        response = requests.post(url, json={"tokens": ["So11111111111111111111111111111111111111112"]})
        data = response.json()
        return data["prices"]["So11111111111111111111111111111111111111112"]["price"] if "prices" in data else None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error fetching SOL price from Helius: {e}")
        return None

# 📌 Process Incoming Transaction Data
USDC_MINTS = [
    "Es9vMFrzaCERhA68D7Z8yFPmHe6LLwZ9keWxETn3WNh7",
    "BXXkv6zGskqmy7tsVj4rUtP9xVB2pNVQpHrkajFkayR3"
]

token_activity = {}

def process_transaction(data):
    global token_activity
    wallets = load_wallets()
    current_time = time.time()

    for txn in data.get("transactions", []):
        signature = txn.get("signature", "UNKNOWN")
        print(f"📌 Processing Transaction: {signature}")

        if "tokenTransfers" in txn and isinstance(txn["tokenTransfers"], list):
            for transfer in txn["tokenTransfers"]:
                from_user = transfer.get("fromUserAccount")
                to_user = transfer.get("toUserAccount")
                token_amount = transfer.get("tokenAmount", 0)
                token_mint = transfer.get("mint", "UNKNOWN")

                # ✅ Skip USDC transactions
                if token_mint in USDC_MINTS:
                    print(f"⚠️ Skipping USDC transaction: {signature}")
                    continue

                # ✅ Get Token Name & Price in SOL
                token_name, token_price_in_sol = get_token_info(token_mint)
                sol_price_in_usd = get_sol_price_in_usd()

                # ✅ Convert Token Amount to USD
                if token_price_in_sol and sol_price_in_usd:
                    usd_value = round(token_amount * token_price_in_sol * sol_price_in_usd, 2)
                else:
                    usd_value = "Unknown"

                # ✅ Store buy/sell activity
                if token_mint not in token_activity:
                    token_activity[token_mint] = {"name": token_name, "buys": 0, "sells": 0, "timestamps": []}

                if from_user in wallets:
                    token_activity[token_mint]["sells"] += 1
                    send_telegram_alert("SELL", wallets[from_user]["name"], token_name, token_amount, usd_value)

                elif to_user in wallets:
                    token_activity[token_mint]["buys"] += 1
                    send_telegram_alert("BUY", wallets[to_user]["name"], token_name, token_amount, usd_value)

    # ✅ Check for Strong Buy/Sell Alerts
    check_strong_alerts()

# 📌 Function to Check if 3+ Buys/Sells Happened in a Time Window
def check_strong_alerts():
    global token_activity
    current_time = time.time()
    time_window = 300  # 5 minutes

    for token, data in token_activity.items():
        if data["buys"] >= 3:
            send_strong_alert("🔥 STRONG BUY ALERT 🔥", data["name"], data["buys"])
            token_activity[token]["buys"] = 0  

        if data["sells"] >= 3:
            send_strong_alert("🚨 STRONG SELL ALERT 🚨", data["name"], data["sells"])
            token_activity[token]["sells"] = 0  

# 📌 Send Telegram Alert
def send_telegram_alert(action, wallet_name, token_name, amount, usd_value):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    message = (
        f"{action} Alert! 🚀\n\n"
        f"👤 Wallet: {wallet_name}\n"
        f"🪙 Token: {token_name}\n"
        f"💰 Amount: {amount}\n"
        f"💵 USD Value: ${usd_value}\n"
    )

    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")

# 🔥 Run Flask Server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
