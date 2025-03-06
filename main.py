import os
import json
import requests
from flask import Flask, request, jsonify
from telegram import Bot
from datetime import datetime

# 🔹 Your Telegram Bot Token & Chat ID
TELEGRAM_BOT_TOKEN = "7841195146:AAF4DbFsAqphttY1Tm3lWsqmTJh53nm_ykQ"
TELEGRAM_CHAT_ID = 1119850623  # Replace with your actual chat ID

# 🔹 Helius API Key
HELIUS_API_KEY = "b8c7e3e5-d0ff-4532-8f28-84031a29a356"

# 🔹 Helius API Endpoint
HELIUS_TRANSACTIONS_URL = "https://api.helius.xyz/v0/addresses/{}/transactions?api-key=" + HELIUS_API_KEY

# 🔹 Wallets File
WALLETS_FILE = "Kol_wallets.txt"

# 🔹 Dictionary to Track Last Seen Transactions
last_transactions = {}

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
        data = request.get_json(force=True)  # Force Flask to parse JSON
        if data is None:
            return jsonify({"error": "Invalid JSON format"}), 400
        
        print("🔹 Received Webhook Data:", json.dumps(data, indent=2))
        process_transaction(data)
        return jsonify({"status": "received"}), 200
    except Exception as e:
        print("❌ JSON Parsing Error:", str(e))
        return jsonify({"error": "Invalid JSON"}), 400

# 📌 Load Wallets from File
def load_wallets():
    try:
        with open(WALLETS_FILE, "r", encoding="utf-8") as file:
            wallets_data = json.load(file)
        wallets = {wallet["address"]: wallet for wallet in wallets_data}
        return wallets
    except Exception as e:
        print(f"❌ Error loading wallets: {e}")
        return {}

# 📌 Fetch Recent Transactions from Helius API
def fetch_recent_transactions(wallet_address: str, limit: int = 5) -> list:
    url = HELIUS_TRANSACTIONS_URL.format(wallet_address)
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json().get("transactions", [])
    else:
        print(f"⚠️ Failed to fetch transactions for {wallet_address}: {response.status_code}")
        return []

# 📌 Extract Coin Symbol from Transaction
def extract_coin_info(transaction: dict) -> str:
    instructions = transaction.get("instructions", [])
    for instruction in instructions:
        if instruction.get("type") == "transfer":
            return instruction.get("tokenSymbol", "Unknown Coin")
    return "Unknown Coin"

# 📌 Send Telegram Alert
def send_telegram_alert(wallet_name, wallet_address, transaction, coin, emoji):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    message = (
        f"🚀 *New Transaction Alert* 🚀\n\n"
        f"👤 *Wallet Name:* {wallet_name} {emoji}\n"
        f"📍 *Wallet Address:* `{wallet_address[:6]}...{wallet_address[-6:]}`\n"
        f"🔗 *Transaction:* `{transaction['signature'][:10]}...{transaction['signature'][-10:]}`\n"
        f"⏳ *Time:* {datetime.utcfromtimestamp(transaction['blockTime']).strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"💰 *Coin:* {coin}\n"
        f"📝 *Description:* {transaction.get('description', 'N/A')}"
    )
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")

# 📌 Process Incoming Transaction Data
def process_transaction(data):
    wallets = load_wallets()
    
    for txn in data.get("transactions", []):
        wallet_address = txn.get("account", None)
        
        if wallet_address and wallet_address in wallets:
            if wallet_address not in last_transactions or txn["signature"] != last_transactions[wallet_address]:
                coin = extract_coin_info(txn)
                send_telegram_alert(
                    wallets[wallet_address]["name"],
                    wallet_address,
                    txn,
                    coin,
                    wallets[wallet_address].get("emoji", ""),
                )
                last_transactions[wallet_address] = txn["signature"]

# 🔥 Run Flask Server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
