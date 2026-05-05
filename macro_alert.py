import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Config
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
PARIS_TZ = ZoneInfo("Europe/Paris")
NY_TZ = ZoneInfo("America/New_York")

def convert_ny_to_paris(time_str):
    """Force la conversion de l'heure peu importe le format (10:30am, 14:30, etc.)"""
    if not time_str or time_str.lower() in ["all day", "tentative"]:
        return "Journée"
    
    try:
        # Nettoyage du texte (ex: "10:30am" -> "10:30AM")
        t_clean = time_str.replace(" ", "").upper()
        now_ny = datetime.now(NY_TZ)
        
        # Test format 12h (AM/PM)
        if "AM" in t_clean or "PM" in t_clean:
            t = datetime.strptime(t_clean, "%I:%M%p")
        # Test format 24h
        else:
            t = datetime.strptime(t_clean, "%H:%M")
            
        dt_ny = now_ny.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        return dt_ny.astimezone(PARIS_TZ).strftime("%Hh%M")
    except:
        # Si le format est juste "10am" sans les minutes
        try:
            t_clean = time_str.replace(" ", "").upper()
            if "AM" in t_clean or "PM" in t_clean:
                t = datetime.strptime(t_clean, "%I%p")
                dt_ny = datetime.now(NY_TZ).replace(hour=t.hour, minute=0)
                return dt_ny.astimezone(PARIS_TZ).strftime("%Hh%M")
        except:
            pass
        return "Journée"

def get_events():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
        today = datetime.now(NY_TZ).strftime("%Y-%m-%d")
        return [e for e in data if e.get("country") == "USD" and e.get("date", "")[:10] == today]
    except:
        return []

def main():
    events = get_events()
    now = datetime.now(PARIS_TZ)
    
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    date_str = f"{jours[now.weekday()]} {now.day} {mois[now.month-1]} {now.year}"

    lines = [f"🚀 *US30 Briefing — {date_str}*", "_Heure de Paris_", ""]

    high = [e for e in events if e["impact"] == "High"]
    med = [e for e in events if e["impact"] in ["Medium", "Low"]]

    if high:
        lines.append("🔴 *FORT IMPACT*")
        for e in high:
            t = convert_ny_to_paris(e.get("time"))
            lines.append(f"• `{t}` | *{e.get('title')}*")
            if e.get("forecast"): lines.append(f"  └ Cns: `{e['forecast']}` | Préc: `{e['previous']}`")
        lines.append("")

    if med:
        lines.append("🟡 *AUTRES NEWS*")
        for e in med:
            t = convert_ny_to_paris(e.get("time"))
            lines.append(f"• `{t}` | {e.get('title')}")
        lines.append("")

    lines += [
        "─────────────────",
        "🔔 *Ouverture* : `15h30` Paris",
        "🕒 *Fenêtre*   : `15h30 → 16h30` (Volatilité)",
        "📈 *ATH US30*  : `50 539 pts`",
        "",
        "🌍 *Watch* : Iran · Détroit · Pétrole · Trump",
        "",
        "Bonne séance ! 📉"
    ]
    
    msg = "\n".join(lines)
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    main()
