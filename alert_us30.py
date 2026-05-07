import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

PARIS_TZ = ZoneInfo("Europe/Paris")
NY_TZ = ZoneInfo("America/New_York")

EVENT_EXPLAINERS = {
    "non-farm": "Chiffre le plus important du mois. Dessus consensus = US30 monte fort",
    "nfp": "Chiffre le plus important du mois. Dessus consensus = US30 monte fort",
    "payroll": "Emploi US. Bon chiffre = economie solide = haussier",
    "adp": "Avant-gout du NFP vendredi. Donne le ton en debut de semaine",
    "jolts": "Offres emploi. Beaucoup = marche tendu = Fed garde taux hauts",
    "jobless claims": "Inscriptions chomage hebdo. Hausse = signal ralentissement eco",
    "unemployment": "Taux chomage. Hausse = mauvais pour economie = baissier",
    "cpi": "Inflation. Chiffre eleve = Fed ne baisse pas taux = pression sur actions",
    "consumer price": "Inflation. Chiffre eleve = Fed ne baisse pas taux = pression sur actions",
    "pce": "Inflation preferee Fed. Tres surveillee avant chaque reunion FOMC",
    "ppi": "Inflation producteurs. Precurseur du CPI a venir",
    "fomc": "Decision taux Fed. Catalyseur maximal. Volatilite extreme garantie",
    "fed": "Discours membre Fed. Chaque mot peut bouger le marche",
    "powell": "Discours Powell. Forte volatilite pendant et apres",
    "ism": "Activite eco. Dessus 50 = expansion = haussier. Dessous 50 = contraction = baissier",
    "pmi": "Activite eco. Dessus 50 = expansion = haussier. Dessous 50 = contraction = baissier",
    "gdp": "Croissance US. Bon chiffre = economie solide = haussier pour les actions",
    "retail sales": "Consommation menages. Moteur principal de l economie US",
}

# Mise à jour des heures habituelles (Ajout de Unemployment Claims)
USUAL_HOURS = {
    "adp": "14h15",
    "crude oil": "16h30",
    "fomc": "20h00",
    "cpi": "14h30",
    "nfp": "14h30",
    "retail sales": "14h30",
    "ism": "16h00",
    "unemployment claims": "14h30",
    "productivity": "14h30",
    "labor costs": "14h30",
}

def get_explainer(event_name):
    name_lower = event_name.lower()
    for keyword, explanation in EVENT_EXPLAINERS.items():
        if keyword in name_lower:
            return explanation
    return None

def convert_ny_to_paris(time_str, event_name=""):
    name_lower = event_name.lower()
    if not time_str or any(x in time_str.lower() for x in ["all day", "tentative", "?", "day"]):
        for keyword, usual_time in USUAL_HOURS.items():
            if keyword in name_lower:
                return usual_time
        return "Journée"
    try:
        now_ny = datetime.now(NY_TZ)
        t_clean = time_str.lower().replace(" ", "")
        if "am" in t_clean or "pm" in t_clean:
            t = datetime.strptime(t_clean, "%I:%M%p")
        elif ":" in t_clean:
            t = datetime.strptime(t_clean, "%H:%M")
        else:
            return "Journée"
        dt_ny = now_ny.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        return dt_ny.astimezone(PARIS_TZ).strftime("%Hh%M")
    except:
        return "Journée"

def get_events():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        today_str = datetime.now(NY_TZ).strftime("%Y-%m-%d")
        events = []
        for e in data:
            if e.get("country") == "USD" and e.get("date", "")[:10] == today_str:
                events.append({
                    "time_ny": e.get("time", ""),
                    "name": e.get("title", ""),
                    "high_impact": e.get("impact", "") == "High",
                    "forecast": e.get("forecast", "") or "",
                    "actual": e.get("actual", "") or "" 
                })
        return events
    except:
        return []

def build_message(events):
    now = datetime.now(PARIS_TZ)
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = ["jan", "fev", "mars", "avr", "mai", "juin", "juil", "aout", "sep", "oct", "nov", "dec"]
    date_str = f"{jours[now.weekday()]} {now.day} {mois[now.month-1]} {now.year}"

    high = [e for e in events if e["high_impact"]]
    medium = [e for e in events if not e["high_impact"]]

    lines = [f"🚀 *US30 Update — {date_str}*", "_Heure de Paris_", ""]

    if not events:
        lines.append("📅 Aucun event macro majeur aujourd'hui")
    else:
        if high:
            lines.append("🔴 *FORT IMPACT*")
            for e in high:
                paris = convert_ny_to_paris(e["time_ny"], e["name"])
                actual_str = f" | ✅ *Réel: {e['actual']}*" if e['actual'] else ""
                lines.append(f"• `{paris}` | *{e['name']}*{actual_str}")
                exp = get_explainer(e["name"])
                if exp: lines.append(f"  >> _{exp}_")
            lines.append("")

        if medium:
            lines.append("🟡 *IMPACT MOYEN*")
            for e in medium:
                paris = convert_ny_to_paris(e["time_ny"], e["name"])
                actual_str = f" | ✅ *Réel: {e['actual']}*" if e['actual'] else ""
                cns = f" (cns: {e['forecast']})" if e['forecast'] else ""
                lines.append(f"• `{paris}` | {e['name']}{cns}{actual_str}")
                exp = get_explainer(e["name"])
                if exp: lines.append(f"  >> _{exp}_")
            lines.append("")
            
    return "\n".join(lines)

def main():
    events = get_events()
    message = build_message(events)
    live_links = "\n\n" + "🗞 *Clair Tiktok* : [Guerre / Géopolitique](https://www.tiktok.com/@clair.officiel)\n🔗 [joncosoluce.fr](https://joncosoluce.fr/)"
    full_message = message + live_links
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": full_message, "parse_mode": "Markdown", "disable_web_page_preview": True})
    print("Done")

if __name__ == "__main__":
    main()
