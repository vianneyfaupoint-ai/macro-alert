import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT = os.environ["TELEGRAM_CHAT_ID"]
PARIS_TZ = pytz.timezone("Europe/Paris")
TODAY = datetime.now(PARIS_TZ)
TODAY_STR = TODAY.strftime("%d/%m/%Y")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"}


def fetch_espn(tour):
    matches = []
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard"
        r = requests.get(url, headers=HEADERS, timeout=15)
        print(f"ESPN {tour}: {r.status_code} ({len(r.text)} chars)")
        if r.status_code != 200:
            return []
        for ev in r.json().get("events", []):
            comp = ev.get("competitions", [{}])[0]
            cx = comp.get("competitors", [])
            if len(cx) < 2:
                continue
            p1 = cx[0].get("athlete", {}).get("displayName", "?")
            p2 = cx[1].get("athlete", {}).get("displayName", "?")
            try:
                dt = datetime.fromisoformat(ev.get("date", "").replace("Z", "+00:00"))
                heure = dt.astimezone(PARIS_TZ).strftime("%H:%M")
            except Exception:
                heure = "?"
            status = ev.get("status", {}).get("type", {}).get("description", "")
            tournament = ev.get("season", {}).get("displayName", tour.upper())
            matches.append({"p1": p1, "p2": p2, "time": heure, "tournament": tournament, "status": status})
    except Exception as e:
        print(f"ESPN {tour} error: {e}")
    return matches


def fetch_tennis24():
    matches = []
    try:
        r = requests.get("https://www.tennis24.com/", headers=HEADERS, timeout=15)
        print(f"tennis24: {r.status_code} ({len(r.text)} chars)")
        soup = BeautifulSoup(r.text, "lxml")
        current = "Tennis"
        for el in soup.select(".sportName.tennis > div")[:60]:
            cls = el.get("class", [])
            if "event__header" in cls:
                t = el.get_text(strip=True)
                if t:
                    current = t
            elif any("event__match" in c for c in cls):
                players = el.select(".event__participant")
                time_el = el.select_one(".event__time")
                if len(players) >= 2:
                    matches.append({
                        "p1": players[0].get_text(strip=True),
                        "p2": players[1].get_text(strip=True),
                        "time": time_el.get_text(strip=True) if time_el else "?",
                        "tournament": current,
                        "status": "",
                    })
    except Exception as e:
        print(f"tennis24 error: {e}")
    return matches


def fetch_winamax_odds():
    odds = {}
    try:
        r = requests.get(
            "https://www.winamax.fr/apiv1/sports/21/competitions?inPlay=false",
            headers={**HEADERS, "Referer": "https://www.winamax.fr/"},
            timeout=10,
        )
        print(f"Winamax: {r.status_code}")
        if r.status_code != 200:
            return odds
        for comp in r.json().get("competitions", [])[:8]:
            cid = comp.get("competitionId")
            if not cid:
                continue
            r2 = requests.get(
                f"https://www.winamax.fr/apiv1/sports/21/competitions/{cid}/matches",
                headers={**HEADERS, "Referer": "https://www.winamax.fr/"},
                timeout=10,
            )
            if r2.status_code != 200:
                continue
            for m in r2.json().get("matches", []):
                for tk, ok in [("team1Name", "odds1"), ("team2Name", "odds2")]:
                    name = m.get(tk, "").lower()
                    cote = m.get(ok)
                    if name and cote:
                        odds[name] = cote
    except Exception as e:
        print(f"Winamax error: {e}")
    return odds


def build_message(matches, odds):
    lines = [f"🎾 *Tennis du jour — {TODAY_STR}*\n"]
    if not matches:
        lines.append("😴 Aucun match trouvé.")
        lines.append("🔗 [Roland Garros programme](https://www.rolandgarros.com/fr-fr/tableau)")
        return "\n".join(lines)
    current_tour = None
    seen = set()
    for m in matches:
        key = f"{m.get('p1')}-{m.get('p2')}"
        if key in seen:
            continue
        seen.add(key)
        tour = m.get("tournament", "Tennis")
        if tour != current_tour:
            current_tour = tour
            lines.append(f"\n🏆 *{tour}*")
        p1 = m.get("p1", "?")
        p2 = m.get("p2", "?")
        heure = m.get("time", "?")
        status = m.get("status", "")
        c1 = odds.get(p1.lower()) or odds.get(p1.split()[-1].lower())
        c2 = odds.get(p2.lower()) or odds.get(p2.split()[-1].lower())
        if c1 and c2:
            fav = p1 if c1 <= c2 else p2
            best = min(c1, c2)
            cote_str = f" | 💰 *{fav}* @ {best:.2f}"
        else:
            cote_str = ""
        icon = "🔴" if "Progress" in status else "🕐"
        lines.append(f"{icon} {heure} | {p1} vs {p2}{cote_str}")
    lines.append("\n_Source: ESPN · tennis24 · Cotes: Winamax_")
    return "\n".join(lines)


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        r = requests.post(url, data={"chat_id": TELEGRAM_CHAT, "text": chunk, "parse_mode": "Markdown"})
        r.raise_for_status()
    print("Telegram OK")


if __name__ == "__main__":
    print(f"Matchs du {TODAY_STR}...")
    matches = fetch_espn("atp") + fetch_espn("wta")
    print(f"ESPN total: {len(matches)}")
    if not matches:
        matches = fetch_tennis24()
        print(f"tennis24 total: {len(matches)}")
    odds = fetch_winamax_odds()
    print(f"Cotes: {len(odds)}")
    msg = build_message(matches, odds)
    print(msg)
    send_telegram(msg)
    print("Termine")
