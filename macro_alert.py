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

def get_estimated_time(event_name):
    name = event_name.lower()
    for k, v in USUAL_TIMES.items():
        if k in name:
            return v + " (est.)"
    return "?"

# =========================
# EXPLICATIONS
# =========================
EVENT_EXPLAINERS = {
    "non-farm": "Chiffre le plus important du mois. Dessus consensus = US30 monte fort",
    "nfp": "Chiffre le plus important du mois. Dessus consensus = US30 monte fort",
    "payroll": "Emploi US. Bon chiffre = economie solide = haussier",
    "adp": "Avant-gout du NFP vendredi. Donne le ton en debut de semaine",
    "jolts": "Offres emploi. Marche tendu = Fed maintient taux hauts",
    "jobless claims": "Hausse = ralentissement eco",
    "unemployment": "Hausse = negatif pour economie",
    "cpi": "Inflation. Eleve = pression sur actions",
    "pce": "Inflation cle pour la Fed",
    "ppi": "Precurseur du CPI",
    "fomc": "Decision Fed = volatilite maximale",
    "powell": "Discours = volatilite forte",
    "ism": "Activite eco (>50 expansion / <50 contraction)",
    "gdp": "Croissance US",
    "retail sales": "Consommation US",
}

def get_explainer(event_name):
    name_lower = event_name.lower()
    for keyword, explanation in EVENT_EXPLAINERS.items():
        if keyword in name_lower:
            return explanation
    return None

# =========================
# FETCH EVENTS
# =========================
def get_events_forexfactory():
    url = "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        today_str = datetime.now(NY_TZ).strftime("%Y-%m-%d")

        events = []
        for e in data:
            if e.get("country") != "USD":
                continue
            if e.get("date", "")[:10] != today_str:
                continue

            events.append({
                "time": e.get("time", ""),
                "name": e.get("title", ""),
                "impact": e.get("impact", ""),
                "forecast": e.get("forecast", "") or "",
                "previous": e.get("previous", "") or "",
            })

        return events

    except Exception as e:
        print("Erreur API:", e)
        return []

# =========================
# TIME CONVERSION
# =========================
def convert_time(time_str, event_name):
    if not time_str or "all" in time_str.lower():
        return get_estimated_time(event_name)

    try:
        now_ny = datetime.now(NY_TZ)
        t_clean = time_str.lower().replace(" ", "")

        if "am" in t_clean or "pm" in t_clean:
            t = datetime.strptime(t_clean, "%I:%M%p")
        else:
            t = datetime.strptime(t_clean, "%H:%M")

        dt_ny = now_ny.replace(hour=t.hour, minute=t.minute, second=0)
        return dt_ny.astimezone(PARIS_TZ).strftime("%Hh%M")

    except:
        return get_estimated_time(event_name)

# =========================
# MESSAGE
# =========================
def build_message(events):
    now = datetime.now(PARIS_TZ)

    date_str = now.strftime("%A %d %b %Y")

    high = [e for e in events if e["impact"] == "High"]
    medium = [e for e in events if e["impact"] == "Medium"]

    lines = [
        f"US30 Briefing - {date_str}",
        "",
    ]

    if not events:
        lines.append("Aucun event majeur aujourd'hui")

    if high:
        lines.append("=== FORT IMPACT ===")
        lines.append("")

        for e in high:
            t = convert_time(e["time"], e["name"])
            lines.append(f"{t} | {e['name']}")

            if e["forecast"] or e["previous"]:
                lines.append(f"  Cns: {e['forecast']} | Prec: {e['previous']}")

            exp = get_explainer(e["name"])
            if exp:
                lines.append(f"  -> {exp}")

            lines.append("")

    if medium:
        lines.append("=== IMPACT MOYEN ===")
        lines.append("")

        for e in medium:
            t = convert_time(e["time"], e["name"])
            lines.append(f"{t} | {e['name']}")

            exp = get_explainer(e["name"])
            if exp:
                lines.append(f"  -> {exp}")

        lines.append("")

    lines += [
        "--------------------",
        "Ouverture US : 14h30",
        "Fenetre : 14h30 - 15h30",
        "",
        "Bonne seance",
    ]

    return "\n".join(lines)

# =========================
# TELEGRAM
# =========================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    })

# =========================
# MAIN
# =========================
def main():
    events = get_events_forexfactory()
    msg = build_message(events)

    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
