import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Config via Secrets GitHub
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
# Nettoyage de l'ID (enlève les espaces ou "ID:" si présents)
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").replace("ID:", "").strip()

def get_macro_data():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        # On compare avec la date d'aujourd'hui à New York
        today_ny = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        
        lines = [f"🚀 *US30 Update — {datetime.now(ZoneInfo('Europe/Paris')).strftime('%d/%m/%Y')}*", ""]
        
        found = False
        for e in data:
            if e.get("country") == "USD" and str(e.get("date", ""))[:10] == today_ny:
                found = True
                name = e.get("title", "Event")
                actual = str(e.get("actual", "")).strip()
                forecast = str(e.get("forecast", "")).strip()
                
                lines.append(f"🔹 *{name}*")
                if actual and actual.lower() not in ["none", "null", ""]:
                    lines.append(f"   ┗ ✅ *RÉEL : {actual}*")
                elif forecast:
                    lines.append(f"   ┗ (cns: {forecast})")
        
        return "\n".join(lines) if found else "📅 Aucun événement USD aujourd'hui."
    except Exception as e:
        return f"❌ Erreur API : {e}"

def send_telegram(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Erreur : TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID manquant.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    res = requests.post(url, json=payload)
    print(f"Statut envoi : {res.status_code}")

if __name__ == "__main__":
    message = get_macro_data()
    send_telegram(message)
