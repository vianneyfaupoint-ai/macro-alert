import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Config
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PARIS_TZ = ZoneInfo("Europe/Paris")
NY_TZ = ZoneInfo("America/New_York")

def convert_ny_to_paris(time_str):
    if not time_str or time_str.lower() in ["all day", "tentative"]:
        return "Journée"
    try:
        t_clean = time_str.replace(" ", "").upper()
        now_ny = datetime.now(NY_TZ)
        if "AM" in t_clean or "PM" in t_clean:
            t = datetime.strptime(t_clean, "%I:%M%p")
        else:
            t = datetime.strptime(t_clean, "%H:%M")
        dt_ny = now_ny.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        return dt_ny.astimezone(PARIS_TZ).strftime("%Hh%M")
    except:
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
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

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
        lines.append("")

    if med:
        lines.append("🟡 *AUTRES NEWS*")
        for e in med:
            t = convert_ny_to_paris(e.get("time"))
            lines.append(f"• `{t}` | {e.get('title')}")
        lines.append("")

    lines += [
     
        "🌍 *Watch* : Iran · Pétrole",
        # AJOUT DES LIENS ICI
        "🗞 *Flux Live* : [Guerre / Géopolitique](https://news.google.com/search?q=guerre) · [Trump News](https://news.google.com/search?q=Trump)",
        "",
        "Bonne séance ! 📉"
    ]
    
    msg = "\n".join(lines)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True})

if __name__ == "__main__":
    main()
