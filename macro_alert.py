import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

PARIS_TZ = ZoneInfo("Europe/Paris")
NY_TZ = ZoneInfo("America/New_York")

# =========================
# HEURES HABITUELLES
# =========================
USUAL_TIMES = {
    "ism services": "16h00",
    "ism manufacturing": "16h00",
    "jolts": "16h00",
    "nfp": "14h30",
    "non-farm": "14h30",
    "cpi": "14h30",
    "ppi": "14h30",
    "retail sales": "14h30",
    "gdp": "14h30",
    "pce": "14h30",
    "durable goods": "14h30",
    "adp": "14h15",
    "jobless claims": "14h30",
    "consumer confidence": "16h00",
    "michigan": "16h00",
    "new home sales": "16h00",
    "trade balance": "14h30",
}

# =========================
# EXPLICATIONS
# =========================
EVENT_EXPLAINERS = {
    "non-farm": "Chiffre le plus important du mois. Dessus consensus = US30 monte fort",
    "nfp": "Chiffre le plus important du mois. Dessus consensus = US30 monte fort",
    "payroll": "Emploi US. Bon chiffre = economie solide = haussier",
    "adp": "Avant-gout du NFP vendredi. Donne le ton",
    "jolts": "Offres emploi. Marche tendu = Fed restrictive",
    "jobless claims": "Hausse = ralentissement eco",
    "unemployment": "Hausse = negatif economie",
    "cpi": "Inflation elevee = pression actions",
    "pce": "Inflation cle Fed",
    "ppi": "Precurseur CPI",
    "fomc": "Decision Fed = volatilite max",
    "powell": "Discours = volatilite",
    "ism": ">50 expansion / <50 contraction",
    "gdp": "Croissance eco",
    "retail sales": "Consommation US",
}

def get_explainer(event_name):
    name = event_name.lower()
    for k, v in EVENT_EXPLAINERS.items():
        if k in name:
            return v
    return None

# =========================
# FETCH EVENTS (CDN)
# =========================
def get_events():
    url = "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json"

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        today = datetime.now(NY_TZ).strftime("%Y-%m-%d")

        events = []
        for e in data:
            if e.get("country") != "USD":
                continue
            if e.get("date", "")[:10] != today:
                continue

            events.append({
                "time_ny": e.get("time", ""),
                "name": e.get("title", ""),
                "high_impact": e.get("impact") == "High",
                "forecast": e.get("forecast", "") or "",
                "previous": e.get("previous", "") or "",
                "actual": e.get("actual", "") or "",
            })

        return events

    except Exception as e:
        print("Erreur API:", e)
        return []

# =========================
# CONVERT TIME
# =========================
def convert_ny_to_paris(time_str, event_name):
    if not time_str:
        return None

    t = time_str.lower().strip()

    # 🔥 Gestion "Journée"
    if "all" in t or "jour" in t:
        name = event_name.lower()
        for k, v in USUAL_TIMES.items():
            if k in name:
                return v + " (est.)"
        return "?"

    try:
        now_ny = datetime.now(NY_TZ)
        t = t.replace(" ", "")

        if "am" in t or "pm" in t:
            parsed = datetime.strptime(t, "%I:%M%p")
        else:
            parsed = datetime.strptime(t, "%H:%M")

        dt_ny = now_ny.replace(hour=parsed.hour, minute=parsed.minute, second=0)
        return dt_ny.astimezone(PARIS_TZ).strftime("%Hh%M")

    except:
        return None

# =========================
# BUILD MESSAGE (FORMAT ORIGINAL)
# =========================
def build_message(events):
    now = datetime.now(PARIS_TZ)

    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = ["jan", "fev", "mars", "avr", "mai", "juin",
            "juil", "aout", "sep", "oct", "nov", "dec"]

    date_str = f"{jours[now.weekday()]} {now.day} {mois[now.month-1]} {now.year}"

    high = [e for e in events if e["high_impact"]]
    medium = [e for e in events if not e["high_impact"]]

    lines = [
        f"US30 Briefing — {date_str}",
        "Heure de Paris",
        "",
    ]

    if not events:
        lines.append("Aucun event macro majeur aujourd'hui")

    if high:
        lines.append("🔴 FORT IMPACT")
        for e in high:
            paris = convert_ny_to_paris(e["time_ny"], e["name"])
            lines.append(f"• {paris} | {e['name']}")

            if e["forecast"] or e["previous"]:
                lines.append(f"  Cns: {e['forecast']} | Préc: {e['previous']}")

            exp = get_explainer(e["name"])
            if exp:
                lines.append(f"  >> {exp}")

            lines.append("")

    if medium:
        lines.append("🟡 AUTRES NEWS")
        for e in medium:
            paris = convert_ny_to_paris(e["time_ny"], e["name"])
            lines.append(f"• {paris} | {e['name']}")

    lines += [
        "",
        "--------------------",
        "🔔 Ouverture : 15h30 Paris",
        "🕒 Fenêtre : 15h30 - 16h30 (Volatilité)",
        "📈 ATH US30 : 50 539 pts",
        "",
        "🌍 Watch : Iran · Détroit · Pétrole · Trump",
        "",
        "Bonne séance !",
    ]

    return "\n".join(lines)

# =========================
# TELEGRAM
# =========================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": None
    })

# =========================
# MAIN
# =========================
def main():
    print("Run...")
    events = get_events()

    msg = build_message(events)

    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
