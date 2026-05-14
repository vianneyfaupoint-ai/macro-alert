import os
import json
import urllib.request
from datetime import datetime, timedelta

# Récupération sécurisée des secrets
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Fuseaux horaires
PARIS_TZ = ZoneInfo("Europe/Paris")
NY_TZ = ZoneInfo("America/New_York")

# Dictionnaire des explications pour le trading US30
EVENT_EXPLAINERS = {
    "non-farm": "Chiffre majeur. > consensus = US30 haussier (économie forte)",
    "nfp": "Chiffre majeur. > consensus = US30 haussier (économie forte)",
    "payroll": "Emploi US. Bon chiffre = économie solide = haussier",
    "adp": "Avant-goût du NFP. Donne le ton du marché de l'emploi",
    "jolts": "Offres d'emploi. Élevé = Fed peut rester restrictive",
    "jobless claims": "Chômage hebdo. Hausse = signal de ralentissement",
    "unemployment": "Taux de chômage. Hausse = signe de faiblesse économique",
    "cpi": "Inflation. Élevée = Fed garde les taux hauts = pression baissière",
    "consumer price": "Inflation. Élevée = Fed garde les taux hauts = pression baissière",
    "pce": "Inflation préférée de la Fed. Très surveillé avant le FOMC",
    "ppi": "Inflation producteurs. Indicateur avancé du CPI",
    "fomc": "Décision Fed. Volatilité maximale garantie",
    "interest rate": "Décision taux. Impact direct sur le coût du crédit",
    "powell": "Discours Powell. Chaque mot peut faire dévisser ou décoller l'indice",
    "ism": "Activité éco. > 50 = Expansion. < 50 = Contraction",
    "pmi": "Activité éco. > 50 = Expansion. < 50 = Contraction",
    "gdp": "Croissance US. Bon chiffre = moteur pour les actions",
    "retail sales": "Consommation. Moteur principal de l'économie US",
    "michigan": "Moral des ménages. Indicateur de consommation future",
}

def get_explainer(event_name):
    name_lower = event_name.lower()
    for keyword, explanation in EVENT_EXPLAINERS.items():
        if keyword in name_lower:
            return explanation
    return None

def convert_ny_to_paris(time_str):
    """Convertit l'heure de ForexFactory (NY) en heure de Paris."""
    if not time_str or ":" not in time_str:
        return "Journée"
    try:
        now_ny = datetime.now(NY_TZ)
        t_clean = time_str.lower().replace(" ", "")
        
        # Gestion format 10:30am ou 14:30
        if "am" in t_clean or "pm" in t_clean:
            t = datetime.strptime(t_clean, "%I:%M%p")
        else:
            t = datetime.strptime(t_clean, "%H:%M")
            
        dt_ny = now_ny.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        return dt_ny.astimezone(PARIS_TZ).strftime("%Hh%M")
    except:
        return "Bientôt"

def get_events():
    """Récupère les événements du jour via le CDN de ForexFactory."""
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        data = resp.json()
        
        today_str = datetime.now(NY_TZ).strftime("%Y-%m-%d")
        events = []
        
        for e in data:
            # On ne garde que l'USD et les news du jour (Heure NY)
            if e.get("country") == "USD" and e.get("date", "")[:10] == today_str:
                events.append({
                    "time_ny": e.get("time", ""),
                    "name": e.get("title", ""),
                    "impact": e.get("impact", ""),
                    "forecast": e.get("forecast", ""),
                    "previous": e.get("previous", ""),
                    "actual": e.get("actual", "")
                })
        return events
    except Exception as ex:
        print(f"Erreur lors de la récupération : {ex}")
        return []

def build_message(events):
    now = datetime.now(PARIS_TZ)
    date_str = now.strftime("%A %d %B %Y")
    
    # Traduction rapide du jour pour le style
    translations = {"Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi", 
                    "Thursday": "Jeudi", "Friday": "Vendredi", "May": "Mai"}
    for eng, fra in translations.items():
        date_str = date_str.replace(eng, fra)

    lines = [
        f"🚀 *US30 Briefing — {date_str}*",
        "_Heure de Paris_",
        ""
    ]

    if not events:
        lines += ["🚫 Aucun événement macro majeur aujourd'hui.", "Séance pilotée par le flux technique."]
    else:
        # Tri par impact
        high = [e for e in events if e["impact"] == "High"]
        medium = [e for e in events if e["impact"] == "Medium"]

        if high:
            lines.append("🔴 *FORT IMPACT*")
            for e in high:
                h_paris = convert_ny_to_paris(e["time_ny"])
                lines.append(f"• `{h_paris}` | *{e['name']}*")
                if e['forecast']: lines.append(f"  └ Cns: `{e['forecast']}` | Préc: `{e['previous']}`")
                exp = get_explainer(e['name'])
                if exp: lines.append(f"  >> _{exp}_")
            lines.append("")

        if medium:
            lines.append("🟡 *IMPACT MOYEN*")
            for e in medium:
                h_paris = convert_ny_to_paris(e["time_ny"])
                lines.append(f"• `{h_paris}` | {e['name']}")
            lines.append("")

    lines += [
        "─────────────────",
        "🔔 *Ouverture* : `15h30` Paris",
        "🕒 *Fenêtre*   : `15h30 → 16h30` (Volatilité)",
        "📈 *ATH US30*  : `50 539 pts` (À surveiller)",
        "",
        "🌍 *Watch* : Iran · Détroit · Pétrole · Trump",
        "",
        "Bonne séance ! 📉"
    ]
    return "\n".join(lines)

def send_msg(text):
    if not TOKEN or not CHAT_ID:
        print("Erreur: Secrets manquants")
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.getcode() == 200:
                print("✅ Message envoyé à Telegram !")
    except Exception as e:
        print(f"❌ Erreur envoi: {e}")
