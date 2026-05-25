import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT_ID"]

PARIS_TZ  = pytz.timezone("Europe/Paris")
TODAY     = datetime.now(PARIS_TZ)
TODAY_STR = TODAY.strftime("%d/%m/%Y")
DATE_URL  = TODAY.strftime("%Y-%m-%d")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Scrape livescore.com tennis ───────────────────────────────────────────────
def fetch_livescore() -> list[dict]:
    """Scrape les matchs ATP/WTA du jour sur livescore.com"""
    url = f"https://www.livescore.com/en/tennis/"
    matches = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")

        # Cherche les blocs de matchs
        for row in soup.select("[class*='match']")[:40]:
            text = row.get_text(separator=" | ", strip=True)
            if " vs " in text.lower() or "v." in text.lower():
                matches.append({"raw": text})
    except Exception as e:
        print(f"Livescore error: {e}")
    return matches


# ── Scrape Unibet pour les cotes ──────────────────────────────────────────────
def fetch_unibet_odds() -> dict:
    """Retourne {nom_joueur_lower: cote} depuis Unibet"""
    url = "https://www.unibet.fr/betting/sports/tennis"
    odds = {}
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        for btn in soup.select("[data-test-id*='odds'], [class*='odds'], [class*='price']"):
            parent = btn.find_parent()
            if parent:
                name  = parent.get_text(strip=True)
                price = btn.get_text(strip=True).replace(",", ".")
                try:
                    odds[name.lower()[:30]] = float(price)
                except:
                    pass
    except Exception as e:
        print(f"Unibet error: {e}")
    return odds


# ── Source principale : Tennis Abstract / ATP API JSON ────────────────────────
def fetch_atp_schedule() -> list[dict]:
    """Essaie l'API JSON de l'ATP Tour"""
    matches = []
    url = f"https://www.atptour.com/en/scores/current/french-open/520/schedule-scores"
    try:
        r = requests.get(url, headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"}, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "lxml")
            for row in soup.select("tr.match-row, .match-ctr"):
                players = [p.get_text(strip=True) for p in row.select(".player-name, .name")]
                time_el = row.select_one(".time, .match-time")
                time_str = time_el.get_text(strip=True) if time_el else "?"
                court_el = row.select_one(".court, .stadium")
                court = court_el.get_text(strip=True) if court_el else ""
                if len(players) >= 2:
                    matches.append({
                        "p1": players[0], "p2": players[1],
                        "time": time_str, "court": court,
                        "tournament": "Roland Garros 2026"
                    })
    except Exception as e:
        print(f"ATP error: {e}")
    return matches


def fetch_all_matches() -> list[dict]:
    """Agrège depuis plusieurs sources"""
    matches = fetch_atp_schedule()
    
    # Fallback : BBC Sport tennis
    if not matches:
        try:
            r = requests.get(
                "https://www.bbc.com/sport/tennis/scores-fixtures",
                headers=HEADERS, timeout=15
            )
            soup = BeautifulSoup(r.text, "lxml")
            for fixture in soup.select("[class*='fixture'], [class*='match']")[:20]:
                teams = fixture.select("[class*='team'], [class*='player']")
                if len(teams) >= 2:
                    matches.append({
                        "p1": teams[0].get_text(strip=True),
                        "p2": teams[1].get_text(strip=True),
                        "time": "?", "court": "",
                        "tournament": fixture.find_parent(
                            lambda t: t.get("class") and any("competition" in c for c in t.get("class", []))
                        ) and "ATP/WTA" or "ATP/WTA"
                    })
        except Exception as e:
            print(f"BBC error: {e}")

    # Fallback 2 : ESPN JSON
    if not matches:
        for tour in ["atp", "wta"]:
            try:
                r = requests.get(
                    f"https://site.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard",
                    headers=HEADERS, timeout=10
                )
                if r.status_code == 200:
                    for ev in r.json().get("events", []):
                        comp = ev.get("competitions", [{}])[0]
                        competitors = comp.get("competitors", [])
                        if len(competitors) >= 2:
                            p1 = competitors[0].get("athlete", {}).get("displayName", "?")
                            p2 = competitors[1].get("athlete", {}).get("displayName", "?")
                            date_s = ev.get("date", "")
                            try:
                                dt   = datetime.fromisoformat(date_s.replace("Z", "+00:00"))
                                heure = dt.astimezone(PARIS_TZ).strftime("%H:%M")
                            except:
                                heure = "?"
                            status = ev.get("status", {}).get("type", {}).get("description", "")
                            matches.append({
                                "p1": p1, "p2": p2,
                                "time": heure,
                                "court": "",
                                "tournament": tour.upper(),
                                "status": status,
                            })
            except Exception as e:
                print(f"ESPN {tour} error: {e}")

    return matches


# ── Fetch cotes Winamax (JSON public) ────────────────────────────────────────
def fetch_winamax_odds() -> dict:
    """Essaie l'API Winamax pour récupérer des cotes tennis"""
    odds = {}
    try:
        r = requests.get(
            "https://www.winamax.fr/apiv1/sports/21/competitions?inPlay=false",
            headers={**HEADERS, "Referer": "https://www.winamax.fr/"},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            for comp in data.get("competitions", [])[:5]:
                comp_id = comp.get("competitionId")
                if not comp_id:
                    continue
                r2 = requests.get(
                    f"https://www.winamax.fr/apiv1/sports/21/competitions/{comp_id}/matches",
                    headers={**HEADERS, "Referer": "https://www.winamax.fr/"},
                    timeout=10
                )
                if r2.status_code == 200:
                    for m in r2.json().get("matches", []):
                        for team_key, odd_key in [("team1Name","odds1"), ("team2Name","odds2")]:
                            name = m.get(team_key, "").lower()
                            cote = m.get(odd_key)
                            if name and cote:
                                odds[name] = cote
    except Exception as e:
        print(f"Winamax error: {e}")
    return odds


# ── Build Telegram message ────────────────────────────────────────────────────
def build_message(matches: list[dict], odds: dict) -> str:
    lines = [f"🎾 *Tennis du jour — {TODAY_STR}*\n"]

    if not matches:
        lines.append("😴 Aucun match trouvé pour aujourd'hui.")
        lines.append("\n_Vérifiez le programme sur atptour.com ou wtatennis.com_")
        return "\n".join(lines)

    current_tournament = None
    for m in matches:
        tournament = m.get("tournament", "ATP/WTA")
        if tournament != current_tournament:
            current_tournament = tournament
            lines.append(f"\n🏆 *{tournament}*")

        p1, p2   = m.get("p1", "?"), m.get("p2", "?")
        heure    = m.get("time", "?")
        court    = f" — {m['court']}" if m.get("court") else ""
        status   = m.get("status", "")

        # Cote
        cote_p1 = odds.get(p1.lower()) or odds.get(p1.split()[-1].lower())
        cote_p2 = odds.get(p2.lower()) or odds.get(p2.split()[-1].lower())

        if cote_p1 and cote_p2:
            if cote_p1 <= cote_p2:
                cote_str = f" | 💰 *{p1}* @ {cote_p1:.2f}"
            else:
                cote_str = f" | 💰 *{p2}* @ {cote_p2:.2f}"
        else:
            cote_str = ""

        icon = "🔴" if status == "In Progress" else "🕐"
        lines.append(f"{icon} {heure}{court} | {p1} vs {p2}{cote_str}")

    lines.append(f"\n_Source: ATP/ESPN · Cotes: Winamax_")
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

    matches = fetch_all_matches()
    odds    = fetch_winamax_odds()

    print(f"Matchs: {len(matches)} | Cotes: {len(odds)}")

    message = build_message(matches, odds)
    print(message)
    send_telegram(message)
    print("🏁 Terminé")            try:
                name        = ev.get("name", "")
                status      = ev.get("status", {}).get("type", {}).get("description", "")
                tournament  = ev.get("competitions", [{}])[0].get("venue", {}).get("fullName", "")
                competitors = ev.get("competitions", [{}])[0].get("competitors", [])
                
                if len(competitors) < 2:
                    continue
                
                p1 = competitors[0].get("athlete", {}).get("displayName", "?")
                p2 = competitors[1].get("athlete", {}).get("displayName", "?")
                
                # Heure
                date_str = ev.get("date", "")
                try:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    heure = dt.astimezone(PARIS_TZ).strftime("%H:%M")
                except:
                    heure = "?"

                # Cote depuis odds map
                cote_p1 = odds.get(p1.lower(), None)
                cote_p2 = odds.get(p2.lower(), None)
                
                if cote_p1 and cote_p2:
                    favori = p1 if cote_p1 <= cote_p2 else p2
                    cote   = min(cote_p1, cote_p2)
                    cote_str = f" | 💰 Favori: *{favori}* @ {cote:.2f}"
                elif cote_p1:
                    cote_str = f" | 💰 {p1} @ {cote_p1:.2f}"
                elif cote_p2:
                    cote_str = f" | 💰 {p2} @ {cote_p2:.2f}"
                else:
                    cote_str = ""

                status_icon = "🔴" if "In Progress" in status else "🕐"
                out.append(f"{status_icon} {heure} | {p1} vs {p2}{cote_str}")
            except Exception as e:
                print(f"Format error: {e}")
                continue
        return out

    lines += format_tour(atp_events, "🏆 ATP")
    lines += format_tour(wta_events, "🏆 WTA")
    lines.append("\n_Source: ESPN · Cotes: Betclic_")
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
    
    atp_events = fetch_espn_matches("atp")
    wta_events = fetch_espn_matches("wta")
    odds       = fetch_betclic_odds()
    
    print(f"ATP: {len(atp_events)} matchs | WTA: {len(wta_events)} matchs | Cotes: {len(odds)}")
    
    message = build_message(atp_events, wta_events, odds)
    print(message)
    
    send_telegram(message)
    print("🏁 Terminé")
