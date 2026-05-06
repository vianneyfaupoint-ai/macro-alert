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
    "producer price": "Inflation producteurs. Precurseur du CPI a venir",
    "fomc": "Decision taux Fed. Catalyseur maximal. Volatilite extreme garantie",
    "interest rate": "Decision taux Fed. Catalyseur maximal. Volatilite extreme garantie",
    "fed": "Discours membre Fed. Chaque mot peut bouger le marche",
    "powell": "Discours Powell. Forte volatilite pendant et apres",
    "warsh": "Nouveau president Fed. Ses premiers mots donnent le cap monetaire",
    "ism": "Activite eco. Dessus 50 = expansion = haussier. Dessous 50 = contraction = baissier",
    "pmi": "Activite eco. Dessus 50 = expansion = haussier. Dessous 50 = contraction = baissier",
    "gdp": "Croissance US. Bon chiffre = economie solide = haussier pour les actions",
    "retail sales": "Consommation menages. Moteur principal de l economie US",
    "consumer confidence": "Moral menages. Indicateur avance de la consommation a venir",
    "michigan": "Moral menages. Indicateur avance de la consommation a venir",
    "durable goods": "Commandes industrielles. Mesure l investissement des entreprises",
    "beige book": "Rapport Fed sur l economie reelle. Donne le ton du prochain FOMC",
    "fomc member": "Discours membre Fed. Peut signaler un changement de politique",
    "trade balance": "Balance commerciale. Deficit eleve = dollar sous pression",
    "new home sales": "Immobilier neuf. Tres sensible aux taux d interet",
    "building permits": "Permis construire. Indicateur avance du secteur immobilier",
}


def get_explainer(event_name):
    name_lower = event_name.lower()
    for keyword, explanation in EVENT_EXPLAINERS.items():
        if keyword in name_lower:
            return explanation
    return None


def get_events_forexfactory_cdn():
    urls = [
        "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
        "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            data = resp.json()
            today_str = datetime.now(NY_TZ).strftime("%Y-%m-%d")
            events = []
            for e in data:
                if e.get("country") != "USD":
                    continue
                if e.get("date", "")[:10] != today_str:
                    continue
                events.append({
                    "time_ny": e.get("time", ""),
                    "name": e.get("title", ""),
                    "high_impact": e.get("impact", "") == "High",
                    "forecast": e.get("forecast", "") or "",
                    "previous": e.get("previous", "") or "",
                    "actual": e.get("actual", "") or "",
                })
            return events
        except Exception as ex:
            print(f"CDN error ({url}): {ex}")
    return None


def get_events_scrape():
    try:
        from bs4 import BeautifulSoup
        url = "https://www.forexfactory.com/calendar"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        events = []
        current_time = None
        for row in soup.select("tr.calendar__row"):
            try:
                time_cell = row.select_one("td.calendar__time")
                if time_cell:
                    t = time_cell.get_text(strip=True)
                    if t and ":" in t:
                        current_time = t
                currency_cell = row.select_one("td.calendar__currency")
                if not currency_cell or currency_cell.get_text(strip=True) != "USD":
                    continue
                impact_cell = row.select_one("td.calendar__impact span")
                if not impact_cell:
                    continue
                impact_class = " ".join(impact_cell.get("class", []))
                if "high" not in impact_class and "medium" not in impact_class:
                    continue
                event_cell = row.select_one("span.calendar__event-title")
                if not event_cell:
                    continue
                name = event_cell.get_text(strip=True)
                fc = row.select_one("td.calendar__forecast")
                pr = row.select_one("td.calendar__previous")
                events.append({
                    "time_ny": current_time or "",
                    "name": name,
                    "high_impact": "high" in impact_class,
                    "forecast": fc.get_text(strip=True) if fc else "",
                    "previous": pr.get_text(strip=True) if pr else "",
                    "actual": "",
                })
            except Exception:
                continue
        return events
    except Exception as ex:
        print(f"Scraping error: {ex}")
        return None


def get_events():
    print("Source 1: ForexFactory CDN...")
    events = get_events_forexfactory_cdn()
    if events is not None:
        print(f"OK {len(events)} events USD")
        return events
    print("Source 2: ForexFactory scraping...")
    events = get_events_scrape()
    if events is not None:
        print(f"OK {len(events)} events USD")
        return events
    print("Aucune source disponible")
    return []


def convert_ny_to_paris(time_str):
    if not time_str:
        return "?"
    try:
        now_ny = datetime.now(NY_TZ)
        t_clean = time_str.lower().replace(" ", "")
        if "am" in t_clean or "pm" in t_clean:
            t = datetime.strptime(t_clean, "%I:%M%p")
        elif ":" in t_clean:
            t = datetime.strptime(t_clean, "%H:%M")
        else:
            return time_str
        dt_ny = now_ny.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        return dt_ny.astimezone(PARIS_TZ).strftime("%Hh%M")
    except Exception:
        return time_str


def build_message(events):
    now = datetime.now(PARIS_TZ)
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = ["jan", "fev", "mars", "avr", "mai", "juin",
            "juil", "aout", "sep", "oct", "nov", "dec"]
    date_str = f"{jours[now.weekday()]} {now.day} {mois[now.month-1]} {now.year}"

    high = [e for e in events if e["high_impact"]]
    medium = [e for e in events if not e["high_impact"]]

    lines = [
        f"US30 Briefing - {date_str}",
        "Heure Paris",
        "",
    ]

    if not events:
        lines += [
            "Aucun event macro majeur aujourd'hui",
            "Seance pilotee par la geopolitique",
            "Surveiller : Iran - Detroit - Petrole - Trump",
        ]
    else:
        if high:
            lines.append("--- FORT IMPACT ---")
            for e in high:
                paris = convert_ny_to_paris(e["time_ny"])
                lines.append(f"{paris} | {e['name']}")
                details = []
                if e["forecast"]:
                    details.append(f"Cns: {e['forecast']}")
                if e["previous"]:
                    details.append(f"Prec: {e['previous']}")
                if e["actual"]:
                    details.append(f"Reel: {e['actual']}")
                if details:
                    lines.append("  " + " | ".join(details))
                explainer = get_explainer(e["name"])
                if explainer:
                    lines.append(f"  >> {explainer}")
                lines.append("")

        if medium:
            lines.append("--- IMPACT MOYEN ---")
            for e in medium:
                paris = convert_ny_to_paris(e["time_ny"])
                cns = f" (cns: {e['forecast']})" if e["forecast"] else ""
                lines.append(f"{paris} | {e['name']}{cns}")
                explainer = get_explainer(e["name"])
                if explainer:
                    lines.append(f"  >> {explainer}")
            lines.append("")
     lines += [       
# AJOUT DES LIENS ICI
        "🗞 *Flux Live* : [Guerre / Géopolitique](https://news.google.com/search?q=guerre) · [Trump News](https://news.google.com/search?q=Trump)",
        "",
    ]
    
    return "\n".join(lines)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise Exception(f"Telegram error: {data}")
    print(f"Message envoye ({len(message)} chars)")


def main():
    print(f"Macro Alert - {datetime.now(PARIS_TZ).strftime('%d/%m/%Y %H:%M')}")
    events = get_events()
    message = build_message(events)
    print(message)
    send_telegram(message)
    print("Done")


if __name__ == "__main__":
    main()

    msg = "\n".join(lines)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True})

if __name__ == "__main__":
    main()
