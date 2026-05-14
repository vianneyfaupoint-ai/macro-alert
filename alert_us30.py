import os
import urllib.request
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

PARIS_TZ = ZoneInfo("Europe/Paris")
NY_TZ = ZoneInfo("America/New_York")

# Dictionnaire complet avec les nouvelles références CNS
EVENT_EXPLAINERS = {
    "non-farm": "Chiffre le plus important du mois. Si Réel > CNS = US30 monte fort.",
    "nfp": "Chiffre le plus important du mois. Si Réel > CNS = US30 monte fort.",
    "payroll": "Emploi US. Réel > CNS = économie solide = Haussier.",
    "adp": "Avant-goût du NFP. Réel > CNS = souvent positif pour le dollar.",
    "jolts": "Offres emploi. Réel > CNS = marché tendu = la Fed peut rester ferme.",
    "jobless claims": "Inscriptions chômage. Si Réel > CNS = Mauvais signe éco = Baissier.",
    "unemployment": "Taux chômage. Si Réel > CNS = Ralentissement éco = Baissier.",
    "labor costs": "Coût main d'oeuvre. Si Réel > CNS = Risque inflation = Mauvais pour US30.",
    "productivity": "Productivité. Si Réel > CNS = Efficacité éco = Haussier.",
    "construction spending": "Dépenses construction. Si Réel > CNS = Secteur immo solide = Haussier.",
    "natural gas": "Stocks de Gaz. Si Réel > CNS = Offre abondante (ou demande faible) = Impact énergie.",
    "consumer credit": "Crédit conso. Si Réel > CNS = Les gens consomment/empruntent = Haussier.",
    "cpi": "Inflation. Si Réel > CNS = Inflation persistante = Pas de baisse de taux = Baissier.",
    "pce": "Inflation préférée Fed. Si Réel > CNS = Pression sur les taux = Baissier.",
    "ppi": "Inflation producteurs. Si Réel > CNS = Signal d'inflation future = Baissier.",
    "fomc": "Décision taux Fed. Catalyseur maximal. Volatilité extrême garantie.",
    "fed": "Discours membre Fed. Chaque mot peut bouger le marché.",
    "powell": "Discours Powell. Forte volatilité pendant et après.",
    "ism": "Activité éco. Si Réel > CNS (et > 50) = Expansion = Haussier.",
    "pmi": "Activité éco. Si Réel > CNS (et > 50) = Expansion = Haussier.",
    "gdp": "Croissance US (PIB). Si Réel > CNS = Économie forte = Haussier.",
    "retail sales": "Consommation. Si Réel > CNS = Les ménages dépensent = Haussier.",
}

USUAL_HOURS = {
    "adp": "14h15", "crude oil": "16h30", "fomc": "20h00", "cpi": "14h30",
    "nfp": "14h30", "retail sales": "14h30", "ism": "16h00", "unemployment claims": "14h30",
    "labor costs": "14h30", "productivity": "14h30", "construction spending": "16h00",
    "natural gas": "16h30"
}

def get_explainer(event_name):
    name_lower = str(event_name).lower()
    for keyword, explanation in EVENT_EXPLAINERS.items():
        if keyword in name_lower:
            return explanation
    return None

def convert_ny_to_paris(time_str, event_name=""):
    name_lower = str(event_name).lower()
    if not time_str or any(x in str(time_str).lower() for x in ["all day", "tentative", "?", "day"]):
        for keyword, usual_time in USUAL_HOURS.items():
            if keyword in name_lower:
                return usual_time
        return "Journée"
    try:
        now_ny = datetime.now(NY_TZ)
        t_clean = str(time_str).lower().replace(" ", "")
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
        resp.raise_for_status()
        data = resp.json()
        today_str = datetime.now(NY_TZ).strftime("%Y-%m-%d")
        events = []
        for e in data:
            if e.get("country") == "USD" and str(e.get("date", ""))[:10] == today_str:
                events.append({
                    "time_ny": e.get("time", ""),
                    "name": e.get("title", "Event"),
                    "impact": e.get("impact", ""),
                    "forecast": e.get("forecast", ""),
                    "actual": e.get("actual", "")
                })
        return events
    except:
        return []

def build_message(events):
    now = datetime.now(PARIS_TZ)
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = ["jan", "fev", "mars", "avr", "mai", "juin", "juil", "aout", "sep", "oct", "nov", "dec"]
    date_str = f"{jours[now.weekday()]} {now.day} {mois[now.month-1]} {now.year}"

    lines = [f"🚀 *US30 Update — {date_str}*", "_Heure de Paris_", ""]

    if not events:
        lines.append("📅 Aucun event macro majeur aujourd'hui")
    else:
        lines.append("📊 *CALENDRIER ÉCO*")
        for e in events:
            paris = convert_ny_to_paris(e["time_ny"], e["name"])
            actual_val = str(e.get('actual', '')).strip()
            res = f" | ✅ *Réel: {actual_val}*" if actual_val else ""
            cns = f" (cns: {e['forecast']})" if e.get('forecast') and not actual_val else ""
            emoji = "🔴" if e.get('impact') == "High" else "🟡"
            lines.append(f"{emoji} `{paris}` | {e['name']}{cns}{res}")
            exp = get_explainer(e["name"])
            if exp: lines.append(f"  >> _{exp}_")
        lines.append("")
            
    return "\n".join(lines)

def main():
    events = get_events()
    message = build_message(events)
    live_links = "\n\n" + "🗞 *Clair Tiktok* : [Guerre / Géopolitique](https://www.tiktok.com/@clair.officiel)(https://joncosoluce.fr/)"
    full_message = message + live_links
    
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": full_message, "parse_mode": "Markdown", "disable_web_page_preview": True}
        requests.post(url, json=payload)

if __name__ == "__main__":
    main()
