import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

PARIS_TZ = ZoneInfo("Europe/Paris")
NY_TZ = ZoneInfo("America/New_York")

EVENT_EXPLAINERS = {
    "non-farm": "Si Réel > CNS = US30 monte fort.",
    "nfp": "Si Réel > CNS = US30 monte fort.",
    "jobless claims": "Si Réel > CNS = Mauvais signe éco = Baissier.",
    "unemployment": "Si Réel > CNS = Ralentissement éco = Baissier.",
    "labor costs": "Si Réel > CNS = Risque inflation = Mauvais pour US30.",
    "productivity": "Si Réel > CNS = Efficacité éco = Haussier.",
    "construction spending": "Si Réel > CNS = Secteur immo solide = Haussier.",
    "natural gas": "Si Réel > CNS = Offre abondante = Prix Gaz baisse.",
    "consumer credit": "Si Réel > CNS = Les gens consomment = Haussier.",
    "fomc": "Catalyseur maximal. Volatilité extrême.",
    "fed": "Discours membre Fed. Chaque mot peut bouger le marché.",
}

def main():
    # Source de données directe
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
    except: return

    today_ny = datetime.now(NY_TZ).strftime("%Y-%m-%d")
    now_p = datetime.now(PARIS_TZ)
    
    lines = [f"🚀 *US30 Update — {now_p.strftime('%d/%m/%Y')}*", "_Mise à jour en direct_", ""]
    lines.append("📊 *RÉSULTATS ET CALENDRIER*")

    for e in data:
        # On ne prend que le USD d'aujourd'hui
        if e.get("country") == "USD" and str(e.get("date", ""))[:10] == today_ny:
            name = e.get("title", "Event")
            time_raw = e.get("time", "")
            actual = str(e.get("actual", "")).strip()
            forecast = str(e.get("forecast", "")).strip()
            
            # Emoji d'impact
            emoji = "🔴" if e.get("impact") == "High" else "🟡"
            
            # Formatage de la ligne
            time_display = time_raw if time_raw else "---"
            
            # Affichage CRITIQUE du Réel
            if actual and actual.lower() != "none":
                val_display = f"✅ *Réel: {actual}* (cns: {forecast})"
            else:
                val_display = f"(cns: {forecast})" if forecast else ""

            lines.append(f"{emoji} `{time_display}` | {name}")
            if val_display:
                lines.append(f"   ┗ {val_display}")
            
            # Explication
            for kw, expl in EVENT_EXPLAINERS.items():
                if kw in name.lower():
                    lines.append(f"   >> _{expl}_")
                    break
    
    full_message = "\n".join(lines) + "\n\n🗞 *Clair Tiktok* : [Guerre / Géopolitique](https://www.tiktok.com/@clair.officiel)\n🔗 [joncosoluce.fr](https://joncosoluce.fr/)"
    
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        t_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(t_url, json={"chat_id": TELEGRAM_CHAT_ID, "text": full_message, "parse_mode": "Markdown", "disable_web_page_preview": True})

if __name__ == "__main__":
    main()
