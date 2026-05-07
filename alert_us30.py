import os
import requests
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PARIS_TZ = ZoneInfo("Europe/Paris")
NY_TZ = ZoneInfo("America/New_York")

EVENT_EXPLAINERS = {
    "non-farm": "Si Réel > CNS = US30 monte fort.",
    "jobless claims": "Si Réel > CNS = Mauvais signe éco = Baissier.",
    "unemployment": "Si Réel > CNS = Ralentissement éco = Baissier.",
    "labor costs": "Si Réel > CNS = Risque inflation = Mauvais pour US30.",
    "productivity": "Si Réel > CNS = Efficacité éco = Haussier.",
    "construction spending": "Si Réel > CNS = Secteur immo solide = Haussier.",
    "natural gas": "Si Réel > CNS = Offre abondante = Prix Gaz baisse.",
    "consumer credit": "Si Réel > CNS = Les gens consomment = Haussier.",
}

async def take_screenshot():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1280, "height": 900})
            # On va sur le calendrier
            await page.goto("https://www.forexfactory.com/calendar?day=today", timeout=60000)
            await page.wait_for_selector(".calendar__table", timeout=30000)
            
            # On capture la zone du tableau
            element = await page.query_selector(".calendar__table")
            await element.screenshot(path="calendar.png")
            await browser.close()
            return True
        except Exception as e:
            print(f"Erreur screenshot: {e}")
            return False

def get_macro_text():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
    except Exception as e:
        return f"Erreur API: {e}"

    today_ny = datetime.now(NY_TZ).strftime("%Y-%m-%d")
    now_p = datetime.now(PARIS_TZ)
    lines = [f"🚀 *US30 Update — {now_p.strftime('%d/%m/%Y')}*", ""]

    found = False
    for e in data:
        if e.get("country") == "USD" and str(e.get("date", ""))[:10] == today_ny:
            found = True
            name = e.get("title", "Event")
            actual = str(e.get("actual", "")).strip()
            forecast = str(e.get("forecast", "")).strip()
            emoji = "🔴" if e.get("impact") == "High" else "🟡"
            
            lines.append(f"{emoji} *{name}*")
            if actual and actual.lower() not in ["none", "null", ""]:
                lines.append(f"   ┗ ✅ *RÉEL : {actual}*")
            elif forecast:
                lines.append(f"   ┗ (cns: {forecast})")
            
            for kw, expl in EVENT_EXPLAINERS.items():
                if kw in name.lower():
                    lines.append(f"   >> _{expl}_")
                    break
    
    if not found:
        lines.append("📅 Aucun événement USD aujourd'hui.")
        
    return "\n".join(lines)

async def run_all():
    # 1. Obtenir le texte
    text = get_macro_text()
    
    # 2. Prendre la photo
    photo_success = await take_screenshot()
    
    # 3. Envoyer à Telegram
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        if photo_success and os.path.exists("calendar.png"):
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            with open("calendar.png", "rb") as photo:
                requests.post(url, data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "caption": text,
                    "parse_mode": "Markdown"
                }, files={"photo": photo})
        else:
            # Backup si la photo rate
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown"
            })

if __name__ == "__main__":
    # Correction de l'erreur d'arguments
    asyncio.run(run_all())
