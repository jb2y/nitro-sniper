from flask import Flask
import threading
import requests
import json
import re
import time
import random
import websocket
import os

# ==== 1. CRÉER UN PETIT SERVEUR WEB POUR RENDER ====
app = Flask('')

@app.route('/')
def home():
    return "Bot Nitro Sniper actif !"

def run_web_server():
    # Render attend le port 10000 par défaut
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# ==== 2. LANCER LE SERVEUR DANS UN THREAD ====
threading.Thread(target=run_web_server).start()

# ==== 3. CODE DE TON SELF-BOT ====
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    print("[!] ERREUR: Token Discord non trouvé. Définis la variable DISCORD_TOKEN.")
    exit()

HEADERS = {"Authorization": TOKEN, "Content-Type": "application/json"}

def redeem_code(code):
    url = f"https://discord.com/api/v9/entitlements/gift-codes/{code}/redeem"
    try:
        r = requests.post(url, headers=HEADERS, timeout=5)
        if r.status_code == 200:
            print(f"[+] RÉUSSI : {code}")
        else:
            print(f"[-] Échec {code} : {r.status_code}")
    except Exception as e:
        print(f"[!] Erreur : {e}")

def on_message(ws, message):
    try:
        data = json.loads(message)
        if data.get("t") == "MESSAGE_CREATE":
            content = data["d"].get("content", "")
            codes = re.findall(r"discord\.gift/([a-zA-Z0-9]+)", content)
            if codes:
                print(f"[*] Codes trouvés : {codes}")
                for code in codes:
                    threading.Thread(target=redeem_code, args=(code,)).start()
    except Exception as e:
        print(f"[!] WS error : {e}")

def on_open(ws):
    print("[+] Self-bot connecté !")
    print("[+] En écoute sur les serveurs...")

def start_ws():
    ws_url = "wss://gateway.discord.gg/?v=9&encoding=json"
    ws = websocket.WebSocketApp(ws_url, header={"Authorization": TOKEN}, on_open=on_open, on_message=on_message)
    ws.run_forever()

if __name__ == "__main__":
    start_ws()
