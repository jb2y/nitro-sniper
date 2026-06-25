import requests
import json
import re
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import websocket

# ===== CONFIGURATION =====
import os
TOKEN = os.environ.get("DISCORD_TOKEN")
PROXY_LIST = []  # Ajoute des proxies si tu veux : ["http://user:pass@ip:port", ...]
SERVEUR_IDS = []  # Laisse vide pour scruter tous les serveurs, ou mets des IDs ["123", "456"]

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ===== FONCTION POUR RÉCLAMER UN CODE =====
def redeem_code(code, proxy=None, retries=3):
    url = f"https://discord.com/api/v9/entitlements/gift-codes/{code}/redeem"
    for attempt in range(retries):
        try:
            proxies = {"http": proxy, "https": proxy} if proxy else None
            r = requests.post(url, headers=HEADERS, json={}, proxies=proxies, timeout=5)
            
            if r.status_code == 200:
                print(f"[+] RÉUSSI : {code}")
                return True
            elif r.status_code == 429:
                retry_after = r.json().get("retry_after", 5)
                print(f"[!] Rate-limit sur {code}, attente {retry_after}s")
                time.sleep(retry_after + random.uniform(0.5, 1.5))
                continue
            elif r.status_code == 404:
                print(f"[-] Code invalide : {code}")
                return False
            elif r.status_code == 400:
                print(f"[-] Déjà réclamé ou expiré : {code}")
                return False
            else:
                print(f"[-] Échec {code} : {r.status_code} - {r.text[:100]}")
                return False
        except Exception as e:
            print(f"[!] Erreur sur {code} (tentative {attempt+1}) : {e}")
            time.sleep(random.uniform(0.5, 2))
    return False

# ===== SNIPE CONCURRENT AVEC PRIORITÉ =====
def snipe_codes(codes):
    if not codes:
        return
    print(f"[*] {len(codes)} code(s) détecté(s), lancement du snipe...")
    
    # Trier les codes : les plus courts en premier (souvent les plus anciens/rares)
    codes_sorted = sorted(codes, key=len)
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = []
        for i, code in enumerate(codes_sorted):
            proxy = PROXY_LIST[i % len(PROXY_LIST)] if PROXY_LIST else None
            futures.append(executor.submit(redeem_code, code, proxy))
        
        for future in as_completed(futures):
            future.result()

# ===== WEBSOCKET POUR ÉCOUTER EN TEMPS RÉEL =====
def on_message(ws, message):
    try:
        data = json.loads(message)
        
        if data.get("t") == "MESSAGE_CREATE":
            d = data["d"]
            content = d.get("content", "")
            guild_id = d.get("guild_id")
            
            # Filtrer par serveur si configuré
            if SERVEUR_IDS and guild_id not in SERVEUR_IDS:
                return
            
            if "discord.gift/" in content or "discord.com/gifts/" in content:
                # Regex pour capturer tous les codes
                codes = re.findall(r"discord(?:\.gift|\.com/gifts)/([a-zA-Z0-9]+)", content)
                if codes:
                    # Vérifier aussi dans les embeds
                    if "embeds" in d:
                        for embed in d["embeds"]:
                            if "description" in embed:
                                codes += re.findall(r"discord(?:\.gift|\.com/gifts)/([a-zA-Z0-9]+)", embed["description"])
                            if "title" in embed:
                                codes += re.findall(r"discord(?:\.gift|\.com/gifts)/([a-zA-Z0-9]+)", embed["title"])
                    
                    codes = list(set(codes))  # Supprimer les doublons
                    threading.Thread(target=snipe_codes, args=(codes,), daemon=True).start()
                    
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"[!] Erreur WS : {e}")

def on_error(ws, error):
    print(f"[!] Erreur : {error}")

def on_close(ws, close_status_code, close_msg):
    print("[!] Déconnecté, reconnexion dans 5s...")
    time.sleep(5)
    start_websocket()

def on_open(ws):
    print("[+] Self-bot connecté !")
    print(f"[+] Surveille {len(SERVEUR_IDS) if SERVEUR_IDS else 'TOUS'} serveur(s)")

def start_websocket():
    ws_url = "wss://gateway.discord.gg/?v=9&encoding=json"
    ws = websocket.WebSocketApp(ws_url,
                                header={"Authorization": TOKEN},
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()

# ===== LANCEMENT =====
if __name__ == "__main__":
    print("[*] Démarrage du Nitro Sniper v2...")
    start_websocket()
