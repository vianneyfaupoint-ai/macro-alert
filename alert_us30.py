import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

PARIS_TZ = ZoneInfo("Europe/Paris")
NY_TZ = ZoneInfo("America/New_York")

EVENT_EXPLAINERS = {
    "non-farm": "Si Réel > CNS = US30 monte fort.",
    "jobless claims": "Si Réel > CNS = Mauvais signe éco = Baissier.",
    "unemployment": "Si Réel > CNS = Ralentissement éco = Baissier.",
    "labor costs": "Si Réel > CNS = Risque inflation = Mauvais pour US30.",
    "productivity": "Si Réel > CNS = Efficacité éco = Haussier.",
    "construction spending": "Si Réel > CNS = Secteur immo solide = Haussier.",
    "natural gas": "Si Réel > CNS = Offre abondante = Prix Gaz baisse.",
    "consumer credit": "Si Réel > CNS = Les gens consomment = Haussier.",
}

def main():
    try:
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=15)
        data = r.json()
    except: return

    today = datetime.now(NY_TZ).strftime("%Y-%m-%d")
    now_p = datetime.now(PARIS_TZ)
    
    lines = [f"🚀 *US30 Update — {now_p.strftime('%d/%m/%Y')}*", "_Vérification auto des résultats_", ""]
    
    found_any = False
    for e in data:
        if e.get("country") == "USD" and str(e.get("date", ""))[:10] == today:
            found_any = True
            name = e.get("title", "Event")
            # Correction Heure : Si l'API envoie rien, on met l'heure US par défaut
            time_val = e.get("time") if e.get("time") else "En cours"
            actual = str(e.get("actual", "")).strip()
            forecast = str(e.get("forecast", "")).strip()
            
            emoji = "🔴" if e.get("impact") == "High" else "🟡"
            lines.append(f"{emoji} `{time_val}` | *{name}*")
            
            # Bloc de résultat ultra-visible
            if actual and actual.lower() not in ["none", "null", ""]:
                lines.append(f"   ┗ ✅ *RÉEL : {actual}* (Prévu: {forecast})")
            elif forecast:
                lines.append(f"   ┗ ⏳ Attendu: {forecast}")
            
            for kw, expl in EVENT_EXPLAINERS.items():
                if kw in name.lower():
                    lines.append(f"   >> _{expl}_")
                    break
    
    if not found_any:
        lines.append("📅 Aucun événement USD aujourd'hui.")

    full_msg = "\n".join(lines) + "\n\n🗞 *Clair Tiktok* : [Guerre / Géopolitique](https://www.tiktok.com/@clair.officiel)\n🔗 [joncosoluce.fr](https://joncosoluce.fr/)"
    
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": full_msg, "parse_mode": "Markdown", "disable_web_page_preview": True})

if __name__ == "__main__":
    main()
