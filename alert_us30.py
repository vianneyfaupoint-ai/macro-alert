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

# Tes explications de départ
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
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1280, "height": 800})
        await page.goto("https://www.forexfactory.com/calendar?day=today")
        # On attend que le tableau soit chargé
        await page.wait_for_selector(".calendar__table")
        element = await page.query_selector(".calendar__table")
        await element.screenshot(path="calendar.png")
        await browser.close()

def get_macro_text():
    # Ton code de départ pour le texte
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
    except: return "Erreur API"

    today_ny = datetime.now(NY_TZ).strftime("%Y-%m-%d")
    now_p = datetime.now(PARIS_TZ)
    lines = [f"🚀 *US30 Update — {now_p.strftime('%d/%m/%Y')}*", ""]

    for e in data:
        if e.get("country") == "USD" and str(e.get("date", ""))[:10] == today_ny:
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
    return "\n".join(lines)

async def main():
    # 1. On récupère le texte de ton script de départ
    message_text = get_macro_text()
    
    # 2. On prend la capture d'écran en PLUS
    try:
        await take_screenshot()
        has_photo = True
    except:
        has_photo = False

    # 3. On envoie tout à Telegram
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        if has_photo:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            with open("calendar.png", "rb") as photo:
                requests.post(url, data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "caption": message_text,
                    "parse_mode": "Markdown"
                }, files={"photo": photo})
        else:
            # Si le screenshot rate, on envoie au moins le texte
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": message_text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    asyncio.run(main())
