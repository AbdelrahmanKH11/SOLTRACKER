import os
import json
import requests
import asyncio  # Ensure async support for Telegram
import threading
from flask import Flask, request, jsonify
from telegram import Bot
from datetime import datetime

# 🔹 Your Telegram Bot Token & Chat ID
TELEGRAM_BOT_TOKEN = "7841195146:AAF4DbFsAqphttY1Tm3lWsqmTJh53nm_ykQ"
TELEGRAM_CHAT_ID = 1119850623  # Replace with your actual chat ID

# 🔹 Wallets File
WALLETS_FILE = "Kol_wallets.txt"

# 🔹 Initialize Flask App
app = Flask(__name__)

# 🔹 Route: Home Page for Debugging
@app.route("/", methods=["GET"])
def home():
    return "Flask server is running!"

# 🔹 Route: Handle Webhooks from Helius API (Now Fully Fixed)
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        print("🔹 Headers Received:", request.headers)
        
        # Read raw data before parsing
        raw_data = request.data.decode("utf-8")
        print("🔹 Raw Webhook Data Received:", raw_data)

        # Try parsing JSON
        try:
            data = json.loads(raw_data)  # Safe JSON parsing
        except json.JSONDecodeError:
            print("❌ JSON Parsing Error: Malformed request from Helius")
            return jsonify({"error": "Malformed JSON"}), 400

        # Validate that the data structure matches what we expect
        if not isinstance(data, list):
            print("❌ Invalid JSON structure: Expected a list")
            return jsonify({"error": "Invalid JSON format"}), 400

        # Send quick response to Helius
        print("✅ Fast Response Sent to Helius")
        threading.Thread(target=process_transaction, args=({"transactions": data},)).start()
        return jsonify({"status": "received"}), 200

    except Exception as e:
        print(f"❌ Webhook Error: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

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
        signature = txn.get("signature", "UNKNOWN")
        print(f"📌 Processing Transaction: {signature}")  # Debugging print

        # Check if 'tokenTransfers' exists and is a list
        if "tokenTransfers" in txn and isinstance(txn["tokenTransfers"], list):
            for transfer in txn["tokenTransfers"]:
                from_user = transfer.get("fromUserAccount")
                to_user = transfer.get("toUserAccount")
                token_amount = transfer.get("tokenAmount", 0)
                token_mint = transfer.get("mint", "UNKNOWN")

                if not from_user or not to_user or not token_mint or token_amount == 0:
                    print(f"⚠️ Skipping invalid token transfer in transaction {signature}")
                    continue  # Skip transfers with missing data

                print(f"✅ Transaction detected: {signature}, {token_amount} {token_mint}")

                if from_user in wallets:  # SELL action
                    print(f"🔴 SELL detected for {from_user}")
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
                    print(f"🟢 BUY detected for {to_user}")
                    send_telegram_alert(
                        "BUY",
                        wallets[to_user]["name"],
                        to_user,
                        txn,
                        token_mint,
                        wallets[to_user].get("emoji", ""),
                        token_amount
                    )

# 📌 Send Telegram Alert for Buys & Sells (Now Properly Awaiting `send_message()`)
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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown"))
        print(f"✅ Telegram Alert Sent: {response}")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

# 🔥 Run Flask Server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
