import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

PARIS_TZ = ZoneInfo("Europe/Paris")
NY_TZ = ZoneInfo("America/New_York")

#notes# 

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
    "cpi": "Inflation. Si Réel > CNS = Inflation persistante = Baissier.",
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

def get_explainer(event_name):
    name_lower = str(event_name).lower()
    for keyword, explanation in EVENT_EXPLAINERS.items():
        if keyword in name_lower: return explanation
    return None

def convert_ny_to_paris(time_str):
    if not time_str or any(x in str(time_str).lower() for x in ["all day", "tentative", "day"]):
        return "Journée"
    try:
        now_ny = datetime.now(NY_TZ)
        t_clean = str(time_str).lower().replace(" ", "")
        if "am" in t_clean or "pm" in t_clean: t = datetime.strptime(t_clean, "%I:%M%p")
        elif ":" in t_clean: t = datetime.strptime(t_clean, "%H:%M")
        else: return "Journée"
        dt_ny = now_ny.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        return dt_ny.astimezone(PARIS_TZ).strftime("%Hh%M")
    except: return "Journée"

def main():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
    except: return

    today_ny = datetime.now(NY_TZ).strftime("%Y-%m-%d")
    events = [e for e in data if e.get("country") == "USD" and str(e.get("date", ""))[:10] == today_ny]

    now_p = datetime.now(PARIS_TZ)
    date_str = f"{now_p.day}/{now_p.month}/{now_p.year}"
    
    lines = [f"🚀 *US30 Update — {date_str}*", "_Heure de Paris_", ""]
    lines.append("📊 *CALENDRIER ÉCO*")

    for e in events:
        name = e.get("title", "Event")
        paris = convert_ny_to_paris(e.get("time", ""))
        actual = str(e.get("actual", "")).strip()
        forecast = str(e.get("forecast", "")).strip()
        impact = e.get("impact", "")
        
        emoji = "🔴" if impact == "High" else "🟡"
        
        # Logique d'affichage : si le réel est là, on le met en avant
        if actual:
            msg_line = f"{emoji} `{paris}` | {name} | ✅ *Réel: {actual}*"
        else:
            cns_str = f" (cns: {forecast})" if forecast else ""
            msg_line = f"{emoji} `{paris}` | {name}{cns_str}"
        
        lines.append(msg_line)
        exp = get_explainer(name)
        if exp: lines.append(f"  >> _{exp}_")
    
    full_message = "\n".join(lines) + "\n\n🗞 *Clair Tiktok* : [Guerre / Géopolitique](https://www.tiktok.com/@clair.officiel)\n🔗 [joncosoluce.fr](https://joncosoluce.fr/)"
    
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        t_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(t_url, json={"chat_id": TELEGRAM_CHAT_ID, "text": full_message, "parse_mode": "Markdown", "disable_web_page_preview": True})

if __name__ == "__main__":
    main()
