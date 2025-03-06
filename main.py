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
        data = request.get_json(force=True)

        # Debugging: Print raw webhook data
        print("🔹 Raw Webhook Data Received:", json.dumps(data, indent=2))

        if not data:
            print("❌ No JSON data received!")
            return jsonify({"error": "Invalid JSON format"}), 400

        print("✅ Parsed Webhook Data:", json.dumps(data, indent=2))
        process_transaction(data)
        return jsonify({"status": "received"}), 200

    except Exception as e:
        print(f"❌ Webhook Error: {str(e)}")
        return jsonify({"error": "Invalid JSON"}), 400

# 📌 Load Wallets from File
def load_wallets():
    try:
        with open(WALLETS_FILE, "r", encoding="utf-8") as file:
            wallets_data = json.load(file)
        wallets = {wallet["address"]: wallet for wallet in wallets_data}
        print("✅ Loaded Wallets:", wallets.keys())  # Debugging print
        return wallets
    except Exception as e:
        print(f"❌ Error loading wallets: {e}")
        return {}

# 📌 Process Incoming Transaction Data (Only Buys & Sells)
def process_transaction(data):
    wallets = load_wallets()  # Load wallets from file

    for txn in data.get("transactions", []):
        print(f"📌 Processing Transaction: {txn['signature']}")  # Debugging print
        
        # Check if transaction contains token transfers
        if "tokenTransfers" in txn and txn["tokenTransfers"]:
            for transfer in txn["tokenTransfers"]:
                from_user = transfer["fromUserAccount"]
                to_user = transfer["toUserAccount"]
                token_amount = transfer["tokenAmount"]
                token_mint = transfer["mint"]

                if from_user in wallets:  # SELL action
                    send_telegram_alert(
                        "SELL",
                        wallets[from_user]["name"],
                        from_user,
                        txn,
                        token_mint,
                        wallets[from_user].get("emoji", ""),
                        token_amount
                    )

                elif to_user in wallets:  # BUY action
                    send_telegram_alert(
                        "BUY",
                        wallets[to_user]["name"],
                        to_user,
                        txn,
                        token_mint,
                        wallets[to_user].get("emoji", ""),
                        token_amount
                    )

# 📌 Send Telegram Alert for Buys & Sells
def send_telegram_alert(action, wallet_name, wallet_address, transaction, coin, emoji, amount):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    action_emoji = "🟢" if action == "BUY" else "🔴"
    
    message = (
        f"{action_emoji} *{action} Alert!* {action_emoji}\n\n"
        f"👤 *Wallet:* {wallet_name} {emoji}\n"
        f"📍 *Address:* `{wallet_address[:6]}...{wallet_address[-6:]}`\n"
        f"💰 *Amount:* {amount}\n"
        f"🪙 *Token:* `{coin}`\n"
        f"🔗 *Transaction:* `{transaction['signature'][:10]}...{transaction['signature'][-10:]}`\n"
        f"⏳ *Time:* {datetime.utcfromtimestamp(transaction['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    
    try:
        response = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")
        print(f"✅ Telegram Alert Sent: {response}")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

# 🔥 Run Flask Server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
