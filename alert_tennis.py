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
    print("Termine")            for sport in data.get("sports", []):
                for league in sport.get("leagues", []):
                    for ev in league.get("events", []):
                        competitors = ev.get("competitors", [])
                        if len(competitors) < 2:
                            continue
                        p1 = competitors[0].get("displayName", "?")
                        p2 = competitors[1].get("displayName", "?")
                        status = ev.get("status", "")
                        matches.append({
                            "p1": p1, "p2": p2,
                            "time": "?",
                            "tournament": league.get("name", "Tennis"),
                            "status": status,
                        })
        except Exception as e:
            print(f"ESPN error {url[-30:]}: {e}")
    return matches


# ── Scraping livescore.biz (simple HTML) ──────────────────────────────────────
def fetch_livescore_biz() -> list[dict]:
    matches = []
    try:
        r = requests.get(
            "https://www.livescore.biz/tennis/",
            headers=HEADERS, timeout=15
        )
        print(f"livescore.biz: HTTP {r.status_code} - {len(r.text)} chars")
        soup = BeautifulSoup(r.text, "lxml")
        for row in soup.select(".event, .match, [class*='match-row']")[:30]:
            text = row.get_text(" | ", strip=True)
            if len(text) > 5:
                matches.append({"raw": text, "tournament": "Tennis"})
    except Exception as e:
        print(f"livescore.biz error: {e}")
    return matches


# ── Scraping tennis24.com ─────────────────────────────────────────────────────
def fetch_tennis24() -> list[dict]:
    matches = []
    try:
        r = requests.get(
            "https://www.tennis24.com/",
            headers=HEADERS, timeout=15
        )
        print(f"tennis24: HTTP {r.status_code} - {len(r.text)} chars")
        soup = BeautifulSoup(r.text, "lxml")

        current_tournament = "Tennis"
        for el in soup.select(".sportName.tennis > div")[:50]:
            classes = el.get("class", [])

            # Entête tournoi
            if "event__header" in classes:
                t = el.get_text(strip=True)
                if t:
                    current_tournament = t

            # Ligne de match
            elif any("event__match" in c for c in classes):
                players = el.select(".event__participant")
                time_el = el.select_one(".event__time")
                if len(players) >= 2:
                    p1    = players[0].get_text(strip=True)
                    p2    = players[1].get_text(strip=True)
                    heure = time_el.get_text(strip=True) if time_el else "?"
                    matches.append({
                        "p1": p1, "p2": p2,
                        "time": heure,
                        "tournament": current_tournament,
                        "status": "",
                    })
    except Exception as e:
        print(f"tennis24 error: {e}")
    return matches


# ── Scraping scores.tennis (API JSON publique) ────────────────────────────────
def fetch_scores_tennis() -> list[dict]:
    matches = []
    date_fmt = TODAY.strftime("%Y-%m-%d")
    urls = [
        f"https://scores.tennis/live",
        f"https://www.tennislive.net/atp/",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            print(f"{url}: HTTP {r.status_code}")
            if r.status_code == 200 and len(r.text) > 500:
                soup = BeautifulSoup(r.text, "lxml")
                # Cherche pattern "Joueur1 vs Joueur2"
                for row in soup.find_all(["tr", "div", "li"])[:60]:
                    text = row.get_text(" ", strip=True)
                    if " - " in text and len(text) < 100:
                        parts = text.split(" - ")
                        if len(parts) == 2 and len(parts[0]) > 3 and len(parts[1]) > 3:
                            matches.append({
                                "p1": parts[0].strip(),
                                "p2": parts[1].strip(),
                                "time": "?",
                                "tournament": "Roland Garros",
                                "status": "",
                            })
                if matches:
                    break
        except Exception as e:
            print(f"{url} error: {e}")
    return matches


# ── Cotes Winamax ─────────────────────────────────────────────────────────────
def fetch_winamax_odds() -> dict:
    odds = {}
    try:
        r = requests.get(
            "https://www.winamax.fr/apiv1/sports/21/competitions?inPlay=false",
            headers={**HEADERS, "Referer": "https://www.winamax.fr/"},
            timeout=10
        )
        print(f"Winamax: HTTP {r.status_code}")
        if r.status_code != 200:
            return odds
        for comp in r.json().get("competitions", [])[:8]:
            comp_id = comp.get("competitionId")
            if not comp_id:
                continue
            r2 = requests.get(
                f"https://www.winamax.fr/apiv1/sports/21/competitions/{comp_id}/matches",
                headers={**HEADERS, "Referer": "https://www.winamax.fr/"},
                timeout=10
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


# ── Build message ─────────────────────────────────────────────────────────────
def build_message(matches: list[dict], odds: dict) -> str:
    lines = [f"🎾 *Tennis du jour — {TODAY_STR}*\n"]

    if not matches:
        lines.append("😴 Aucun match trouvé automatiquement.")
        lines.append("🔗 [Programme Roland Garros](https://www.rolandgarros.com/fr-fr/tableau)")
        return "\n".join(lines)

    current_tour = None
    seen = set()
    for m in matches:
        # Dédoublonnage
        key = f"{m.get('p1','')}-{m.get('p2','')}"
        if key in seen:
            continue
        seen.add(key)

        tour = m.get("tournament", "Tennis")
        if tour != current_tour:
            current_tour = tour
            lines.append(f"\n🏆 *{tour}*")

        # Match avec raw text (fallback)
        if "raw" in m:
            lines.append(f"🕐 {m['raw'][:80]}")
            continue

        p1     = m.get("p1", "?")
        p2     = m.get("p2", "?")
        heure  = m.get("time", "?")
        status = m.get("status", "")

        cote_p1 = odds.get(p1.lower()) or odds.get(p1.split()[-1].lower())
        cote_p2 = odds.get(p2.lower()) or odds.get(p2.split()[-1].lower())

        if cote_p1 and cote_p2:
            favori   = p1 if cote_p1 <= cote_p2 else p2
            best     = min(cote_p1, cote_p2)
            cote_str = f" | 💰 *{favori}* @ {best:.2f}"
        else:
            cote_str = ""

        icon = "🔴" if "Progress" in status else "🕐"
        lines.append(f"{icon} {heure} | {p1} vs {p2}{cote_str}")

    lines.append("\n_Source: ESPN · tennis24 · Cotes: Winamax_")
    return "\n".join(lines)


# ── Send Telegram ─────────────────────────────────────────────────────────────
def send_telegram(text: str):
    url    = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        r = requests.post(url, data={
            "chat_id":    TELEGRAM_CHAT,
            "text":       chunk,
            "parse_mode": "Markdown"
        })
        r.raise_for_status()
    print("✅ Telegram envoyé")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🔍 Récupération des matchs du {TODAY_STR}…")

    matches = fetch_espn_all()
    print(f"ESPN: {len(matches)} matchs")

    if not matches:
        print("Fallback tennis24…")
        matches = fetch_tennis24()
        print(f"tennis24: {len(matches)} matchs")

    if not matches:
        print("Fallback livescore.biz…")
        matches = fetch_livescore_biz()
        print(f"livescore.biz: {len(matches)} matchs")

    odds = fetch_winamax_odds()
    print(f"Cotes: {len(odds)}")

    message = build_message(matches, odds)
    print(message)
    send_telegram(message)
    print("🏁 Terminé")            headers=HEADERS, timeout=15
        )
        soup = BeautifulSoup(r.text, "lxml")
        for fixture in soup.select("[class*='fixture'], [class*='match']")[:20]:
            teams = fixture.select("[class*='team'], [class*='player']")
            if len(teams) >= 2:
                matches.append({
                    "p1": teams[0].get_text(strip=True),
                    "p2": teams[1].get_text(strip=True),
                    "time": "?",
                    "tournament": "ATP/WTA",
                    "status": "",
                })
    except Exception as e:
        print(f"BBC error: {e}")
    return matches


# ── Cotes Winamax ─────────────────────────────────────────────────────────────
def fetch_winamax_odds() -> dict:
    odds = {}
    try:
        r = requests.get(
            "https://www.winamax.fr/apiv1/sports/21/competitions?inPlay=false",
            headers={**HEADERS, "Referer": "https://www.winamax.fr/"},
            timeout=10
        )
        if r.status_code != 200:
            print(f"Winamax: HTTP {r.status_code}")
            return odds
        for comp in r.json().get("competitions", [])[:5]:
            comp_id = comp.get("competitionId")
            if not comp_id:
                continue
            r2 = requests.get(
                f"https://www.winamax.fr/apiv1/sports/21/competitions/{comp_id}/matches",
                headers={**HEADERS, "Referer": "https://www.winamax.fr/"},
                timeout=10
            )
            if r2.status_code != 200:
                continue
            for m in r2.json().get("matches", []):
                for team_key, odd_key in [("team1Name", "odds1"), ("team2Name", "odds2")]:
                    name = m.get(team_key, "").lower()
                    cote = m.get(odd_key)
                    if name and cote:
                        odds[name] = cote
    except Exception as e:
        print(f"Winamax error: {e}")
    return odds


# ── Build message ─────────────────────────────────────────────────────────────
def build_message(matches: list[dict], odds: dict) -> str:
    lines = [f"🎾 *Tennis du jour — {TODAY_STR}*\n"]

    if not matches:
        lines.append("😴 Aucun match trouvé pour aujourd'hui.")
        lines.append("_Vérifiez sur atptour.com ou wtatennis.com_")
        return "\n".join(lines)

    current_tour = None
    for m in matches:
        tour = m.get("tournament", "ATP/WTA")
        if tour != current_tour:
            current_tour = tour
            lines.append(f"\n🏆 *{tour}*")

        p1     = m.get("p1", "?")
        p2     = m.get("p2", "?")
        heure  = m.get("time", "?")
        status = m.get("status", "")

        cote_p1 = odds.get(p1.lower()) or odds.get(p1.split()[-1].lower())
        cote_p2 = odds.get(p2.lower()) or odds.get(p2.split()[-1].lower())

        if cote_p1 and cote_p2:
            if cote_p1 <= cote_p2:
                cote_str = f" | 💰 *{p1}* @ {cote_p1:.2f}"
            else:
                cote_str = f" | 💰 *{p2}* @ {cote_p2:.2f}"
        else:
            cote_str = ""

        icon = "🔴" if "Progress" in status else "🕐"
        lines.append(f"{icon} {heure} | {p1} vs {p2}{cote_str}")

    lines.append("\n_Source: ESPN · Cotes: Winamax_")
    return "\n".join(lines)


# ── Send Telegram ─────────────────────────────────────────────────────────────
def send_telegram(text: str):
    url    = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        r = requests.post(url, data={
            "chat_id":    TELEGRAM_CHAT,
            "text":       chunk,
            "parse_mode": "Markdown"
        })
        r.raise_for_status()
    print("✅ Telegram envoyé")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🔍 Récupération des matchs du {TODAY_STR}…")

    matches = []
    for tour in ["atp", "wta"]:
        matches += fetch_espn(tour)

    if not matches:
        print("ESPN vide, fallback BBC…")
        matches = fetch_bbc()

    odds = fetch_winamax_odds()

    print(f"Matchs: {len(matches)} | Cotes: {len(odds)}")

    message = build_message(matches, odds)
    print(message)
    send_telegram(message)
    print("🏁 Terminé")
