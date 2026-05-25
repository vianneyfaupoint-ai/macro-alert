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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ── Source ESPN JSON (ATP + WTA) ──────────────────────────────────────────────
def fetch_espn(tour: str) -> list[dict]:
    matches = []
    try:
        r = requests.get(
            f"https://site.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard",
            headers=HEADERS, timeout=15
        )
        if r.status_code != 200:
            print(f"ESPN {tour}: HTTP {r.status_code}")
            return []
        for ev in r.json().get("events", []):
            comp = ev.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            p1 = competitors[0].get("athlete", {}).get("displayName", "?")
            p2 = competitors[1].get("athlete", {}).get("displayName", "?")
            date_s = ev.get("date", "")
            try:
                dt    = datetime.fromisoformat(date_s.replace("Z", "+00:00"))
                heure = dt.astimezone(PARIS_TZ).strftime("%H:%M")
            except Exception:
                heure = "?"
            status = ev.get("status", {}).get("type", {}).get("description", "")
            name   = ev.get("name", "")
            matches.append({
                "p1": p1, "p2": p2,
                "time": heure,
                "tournament": tour.upper(),
                "status": status,
                "name": name,
            })
    except Exception as e:
        print(f"ESPN {tour} error: {e}")
    return matches


# ── Source BBC Sport (fallback) ───────────────────────────────────────────────
def fetch_bbc() -> list[dict]:
    matches = []
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
