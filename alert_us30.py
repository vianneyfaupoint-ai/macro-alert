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

async def take_screenshot():
    print("🎬 Démarrage du navigateur...")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            print("🌐 Navigation vers Forex Factory...")
            await page.goto("https://www.forexfactory.com/calendar?day=today", timeout=60000)
            
            await page.wait_for_selector(".calendar__table", timeout=30000)
            print("📸 Capture d'écran en cours...")
            element = await page.query_selector(".calendar__table")
            await element.screenshot(path="calendar.png")
            await browser.close()
            print("✅ Screenshot réussi et sauvegardé.")
            return True
        except Exception as e:
            print(f"❌ Erreur Screenshot : {e}")
            return False

def get_macro_text():
    print("📡 Récupération des données API...")
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        today_ny = datetime.now(NY_TZ).strftime("%Y-%m-%d")
        lines = [f"🚀 *US30 Update — {datetime.now(PARIS_TZ).strftime('%d/%m/%Y')}*", ""]
        
        found = False
        for e in data:
            if e.get("country") == "USD" and str(e.get("date", ""))[:10] == today_ny:
                found = True
                name = e.get("title", "Event")
                actual = str(e.get("actual", "")).strip()
                forecast = str(e.get("forecast", "")).strip()
                lines.append(f"🔹 *{name}*")
                if actual and actual.lower() not in ["none", "null", ""]:
                    lines.append(f"   ┗ ✅ *RÉEL : {actual}*")
                elif forecast:
                    lines.append(f"   ┗ (cns: {forecast})")
        
        if not found: lines.append("📅 Aucun événement USD aujourd'hui.")
        return "\n".join(lines)
    except Exception as e:
        print(f"❌ Erreur API : {e}")
        return "Erreur lors de la récupération des données."

async def main(*args, **kwargs):
    print("🚀 Début du script principal...")
    text = get_macro_text()
    photo_success = await take_screenshot()
    
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Erreur : TOKEN ou CHAT_ID manquant dans les secrets GitHub !")
        return

    try:
        if photo_success and os.path.exists("calendar.png"):
            print("📤 Envoi de la PHOTO à Telegram...")
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            with open("calendar.png", "rb") as photo:
                res = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": text, "parse_mode": "Markdown"}, files={"photo": photo})
                print(f"Statut Telegram : {res.status_code} - {res.text}")
        else:
            print("📤 Envoi du TEXTE seul (car photo échouée)...")
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            res = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
            print(f"Statut Telegram : {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi Telegram : {e}")

if __name__ == "__main__":
    asyncio.run(main())
