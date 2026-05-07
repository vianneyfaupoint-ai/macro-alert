import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

PARIS_TZ = ZoneInfo("Europe/Paris")
NY_TZ = ZoneInfo("America/New_York")

# On force les heures car l'API les efface parfois après le passage
FIXED_HOURS = {
    "unemployment claims": "14:30",
    "productivity": "14:30",
    "labor costs": "14:30",
    "construction spending": "16:00",
    "natural gas": "16:30",
    "kashkari": "20:00",
    "hammack": "20:00",
    "williams": "20:00",
    "consumer credit": "21:00"
}

EVENT_EXPLAINERS = {
    "non-farm": "Si Réel > CNS = US30 monte fort.",
    "jobless claims": "Si Réel > CNS = Mauvais signe éco = Baissier.",
    "unemployment": "Si Réel > CNS = Ralentissement éco = Baissier.",
    "labor costs": "Si Réel > CNS = Risque inflation = Mauvais pour US30.",
    "productivity": "Si Réel > CNS = Efficacité éco = Haussier.",
    "construction spending": "Si Réel > CNS = Secteur immo solide = Haussier.",
    "natural gas": "Si Réel > CNS = Offre abondante = Prix Gaz baisse.",
    "consumer credit": "Si Réel > CNS = Les gens consomment = Haussier.",
    "fomc": "Catalyseur maximal. Volatilité extrême.",
}

def main():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
    except: return

    today_ny = datetime.now(NY_TZ).strftime("%Y-%m-%d")
    now_p = datetime.now(PARIS_TZ)
    
    lines = [f"🚀 *US30 Update — {now_p.strftime('%d/%m/%Y')}*", "_Mise à jour en direct_", ""]
    lines.append("📊 *RÉSULTATS ET CALENDRIER*")

    for e in data:
        if e.get("country") == "USD" and str(e.get("date", ""))[:10] == today_ny:
            name = e.get("title", "Event")
            name_low = name.lower()
            
            # Récupération de l'heure : API ou Dictionnaire de secours
            time_raw = e.get("time", "")
            if not time_raw or time_raw == "":
                for kw, hr in FIXED_HOURS.items():
                    if kw in name_low:
                        time_raw = hr
                        break
            
            actual = str(e.get("actual", "")).strip()
            forecast = str(e.get("forecast", "")).strip()
            emoji = "🔴" if e.get("impact") == "High" else "🟡"

            # Formatage de la ligne de l'événement
            lines.append(f"{emoji} `{time_raw}` | {name}")
            
            # Affichage du RÉSULTAT (On force l'affichage si l'info existe)
            if actual and actual.lower() not in ["none", "null", ""]:
                lines.append(f"   ┗ ✅ *Réel: {actual}* (cns: {forecast})")
            elif forecast:
                lines.append(f"   ┗ (cns: {forecast})")
            
            # Ajout de l'explication
            for kw, expl in EVENT_EXPLAINERS.items():
                if kw in name_low:
                    lines.append(f"   >> _{expl}_")
                    break
    
    full_message = "\n".join(lines) + "\n\n🗞 *Clair Tiktok* : [Guerre / Géopolitique](https://www.tiktok.com/@clair.officiel)\n🔗 [joncosoluce.fr](https://joncosoluce.fr/)"
    
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        t_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(t_url, json={"chat_id": TELEGRAM_CHAT_ID, "text": full_message, "parse_mode": "Markdown", "disable_web_page_preview": True})

if __name__ == "__main__":
    main()
