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
    if not time_str or ":" not in time_str: return "Journée"
    try:
        now_ny = datetime.now(NY_TZ)
        t_clean = time_str.lower().replace(" ", "")
        fmt = "%I:%M%p" if ("am" in t_clean or "pm" in t_clean) else "%H:%M"
        t = datetime.strptime(t_clean, fmt)
        dt_ny = now_ny.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        return dt_ny.astimezone(PARIS_TZ).strftime("%Hh%M")
    except: return "Soon"

def get_events():
    # On utilise un lien direct vers le flux complet sans filtrage agressif
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
        today = datetime.now(NY_TZ).strftime("%Y-%m-%d")
        # On prend TOUT ce qui est USD pour aujourd'hui
        return [e for e in data if e.get("country") == "USD" and e.get("date", "")[:10] == today]
    except: return []

def main():
    events = get_events()
    now = datetime.now(PARIS_TZ)
    date_str = now.strftime("%A %d %B %Y").replace("Tuesday", "Mardi").replace("May", "Mai")

    lines = [f"🚀 *US30 Briefing — {date_str}*", "_Heure de Paris_", ""]

    high = [e for e in events if e["impact"] == "High"]
    # On force l'affichage de TOUS les impacts Medium et Low pour voir si ça débloque
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
