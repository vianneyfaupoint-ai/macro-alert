async def take_screenshot():
    async with async_playwright() as p:
        try:
            # Arguments obligatoires pour tourner sur un serveur Linux (GitHub)
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1280, "height": 1000})
            
            # On va sur Forex Factory
            await page.goto("https://www.forexfactory.com/calendar?day=today", wait_until="networkidle", timeout=60000)
            
            # On attend le tableau
            await page.wait_for_selector(".calendar__table", timeout=30000)
            
            # On prend la photo
            element = await page.query_selector(".calendar__table")
            await element.screenshot(path="calendar.png")
            await browser.close()
            return True
        except Exception as e:
            print(f"Erreur screenshot détaillée: {e}")
            return False
