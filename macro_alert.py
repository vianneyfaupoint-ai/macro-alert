import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

# Config
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
PARIS_TZ = ZoneInfo("Europe/Paris")
NY_TZ = ZoneInfo("America/New_York")

EVENT_EXPLAINERS = {
    "non-farm": "Chiffre majeur. > consensus = US30 haussier",
    "nfp": "Chiffre majeur. > consensus = US30 haussier",
    "payroll": "Emploi US. Bon chiffre = économie solide = haussier",
    "adp": "Avant-goût du NFP. Donne le ton du marché",
    "jolts": "Offres d'emploi. Élevé = Fed peut rester restrictive",
    "jobless claims": "Chômage hebdo. Hausse = signal de ralentissement",
    "unemployment": "Taux de chômage. Hausse = mauvais pour l'indice",
    "cpi": "Inflation. Élevée = Pression baissière sur l'US30",
    "consumer price": "Inflation. Élevée = Pression baissière sur l'US30",
    "pce": "Inflation préférée de la Fed. Très surveillé",
    "ppi": "Inflation producteurs. Précurseur du CPI",
    "fomc": "Décision Fed. Volatilité maximale garantie",
    "interest rate": "Décision taux. Impact direct sur le marché",
    "powell": "Discours Powell. Attention forte volatilité",
    "ism": "Activité éco. > 50 = Expansion. < 50 = Contraction",
    "pmi": "Activité éco. > 50 = Expansion. < 50 = Contraction",
    "gdp": "Croissance US. Bon chiffre = haussier actions",
    "retail sales": "Consommation. Moteur principal de l'économie US",
    "michigan": "Moral des ménages. Indicateur de consommation",
    "confidence": "Confiance des consommateurs. Impacte la demande",
}

def get_explainer(event_name):
    name_lower = event_name.lower()
    for keyword, explanation in EVENT_EXPLAINERS.items():
        if keyword in name_lower:
            return explanation
    return None

def convert_ny_to_paris(time_str):
    if not time_str or ":" not in time_str:
        return "Journée"
    try:
        now_ny = datetime.now(NY_TZ)
        t_clean = time_str.lower().replace(" ", "")
        if "am" in t_clean or "pm" in t_clean:
            t = datetime.strptime(t_clean, "%I:%M%p")
        else:
            t = datetime.strptime(t_clean, "%H:%M")
        dt_ny = now_ny.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        return dt_ny.astimezone(PARIS_TZ).strftime("%Hh%M")
    except:
        return "Soon"

def get_events_json():
    """Source 1 : Rapide et propre"""
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        today = datetime.now(NY_TZ).strftime("%Y-%m-%d")
        return [e for e in data if e.get("country") == "USD" and e.get("date", "")[:10] == today]
    except:
        return []

def get_events_scrape():
    """Source 2 : Complète (Scraping)"""
    url = "https://www.forexfactory.com/calendar"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        events = []
        curr_time = ""
        for row in soup.select("tr.calendar__row"):
            time_cell = row.select_one("td.calendar__time")
            if time_cell and time_cell.text.strip(): curr_time = time_cell.text.strip()
            
            currency = row.select_one("td.calendar__currency")
            if not currency or "USD" not in currency.text: continue
            
            impact_span = row.select_one("td.calendar__impact span")
            impact_class = " ".join(impact_span.get("class", [])) if impact_span else ""
            if "high" not in impact_class and "medium" not in impact_class: continue

            title = row.select_one("span.calendar__event-title").text.strip()
            forecast = row.select_one("td.calendar__forecast").text.strip()
            previous = row.select_one("td.calendar__previous").text.strip()

            events.append({
                "time_ny": curr_time,
                "title": title,
                "impact": "High" if "high" in impact_class else "Medium",
                "forecast": forecast,
                "previous": previous
            })
        return events
    except:
        return []

def build_message(events):
    now = datetime.now(PARIS_TZ)
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = ["Jan", "Fév", "Mars", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
    date_str = f"{jours[now.weekday()]} {now.day} {mois[now.month-1]} {now.year}"

    lines = [f"🚀 *US30 Briefing — {date_str}*", "_Heure de Paris_", ""]

    if not events:
        lines += ["🚫 Aucun événement majeur aujourd'hui.", "Focus sur le flux technique US30."]
    else:
        high = [e for e in events if e["impact"] == "High"]
        med = [e for e in events if e["impact"] == "Medium"]

        if high:
            lines.append("🔴 *FORT IMPACT*")
            for e in high:
                t = convert_ny_to_paris(e.get("time_ny") or e.get("time"))
                name = e.get("title") or e.get("name")
                lines.append(f"• `{t}` | *{name}*")
                if e.get("forecast"): lines.append(f"  └ Cns: `{e['forecast']}` | Préc: `{e['previous']}`")
                exp = get_explainer(name)
                if exp: lines.append(f"  >> _{exp}_")
            lines.append("")

        if med:
            lines.append("🟡 *IMPACT MOYEN*")
            for e in med:
                t = convert_ny_to_paris(e.get("time_ny") or e.get("time"))
                name = e.get("title") or e.get("name")
                lines.append(f"• `{t}` | {name}")
                exp = get_explainer(name)
                if exp and "Bowman" not in name and "Barr" not in name: # Évite de spammer sur les discours
                     lines.append(f"  >> _{exp}_")
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
    return "\n".join(lines)

def main():
    # On tente le JSON, si on a moins de 5 events (souvent signe qu'il manque les discours), on scrape
    events = get_events_json()
    if len(events) < 5:
        events = get_events_scrape()
    
    msg = build_message(events)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True})

if __name__ == "__main__":
    main()
