import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

PARIS_TZ = ZoneInfo("Europe/Paris")
NY_TZ = ZoneInfo("America/New_York")

# Dictionnaire des impacts CNS
EVENT_EXPLAINERS = {
    "non-farm": "Si Réel > CNS = US30 monte fort.",
    "jobless claims": "Si Réel > CNS = Mauvais signe éco = Baissier.",
    "unemployment": "Si Réel > CNS = Ralentissement éco = Baissier.",
    "labor costs": "Si Réel > CNS = Risque inflation = Mauvais pour US30.",
    "productivity": "Si Réel > CNS = Efficacité éco = Haussier.",
    "construction spending": "Si Réel > CNS = Secteur immo solide = Haussier.",
    "natural gas": "Si Réel > CNS = Offre abondante = Prix Gaz baisse.",
    "consumer credit": "Si Réel > CNS = Les gens consomment = Haussier.",
    "fomc": "Catalyseur maximal. Volatilité extrême.",
    "fed": "Discours membre Fed. Chaque mot peut bouger le marché.",
    "cpi": "Inflation. Si Réel > CNS = Pas de baisse de taux = Baissier.",
    "gdp": "Croissance PIB. Si Réel > CNS = Économie forte = Haussier.",
}

def main():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
    except: return

    today_ny = datetime.now(NY_TZ).strftime("%Y-%m-%d")
    now_p = datetime.now(PARIS_TZ)
    
    lines = [f"🚀 *US30 Update — {now_p.strftime('%d/%m/%Y')}*", "_Mise à jour en direct toutes les 30 min_", ""]
    lines.append("📊 *RÉSULTATS ET CALENDRIER*")

    for e in data:
        # On filtre sur les événements USD du jour
        if e.get("country") == "USD" and str(e.get("date", ""))[:10] == today_ny:
            name = e.get("title", "Event")
            time_raw = e.get("time", "")
            actual = str(e.get("actual", "")).strip()
            forecast = str(e.get("forecast", "")).strip()
            impact = e.get("impact", "")
            
            emoji = "🔴" if impact == "High" else "🟡"
            
            # Affichage de l'heure brute (ex: 8:30am) pour éviter les erreurs
            time_display = time_raw if time_raw else "---"
            
            lines.append(f"{emoji} `{time_display}` | {name}")
            
            # Affichage du Réel si disponible, sinon du CNS
            if actual and actual.lower() not in ["none", "null", ""]:
                lines.append(f"   ┗ ✅ *Réel: {actual}* (cns: {forecast})")
            elif forecast:
                lines.append(f"   ┗ (cns: {forecast})")
            
            # Ajout de l'explication courte
            for kw, expl in EVENT_EXPLAINERS.items():
                if kw in name.lower():
                    lines.append(f"   >> _{expl}_")
                    break
    
    full_message = "\n".join(lines) + "\n\n🗞 *Clair Tiktok* : [Guerre / Géopolitique](https://www.tiktok.com/@clair.officiel)\n🔗 [joncosoluce.fr](https://joncosoluce.fr/)"
    
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        t_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(t_url, json={
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": full_message, 
            "parse_mode": "Markdown", 
            "disable_web_page_preview": True
        })

if __name__ == "__main__":
    main()
