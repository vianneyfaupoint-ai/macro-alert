import os
import requests
import json
from datetime import datetime, timezone
import pytz

# ── Config ───────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT_ID"]

PARIS_TZ = pytz.timezone("Europe/Paris")
TODAY    = datetime.now(PARIS_TZ)
TODAY_STR = TODAY.strftime("%d/%m/%Y")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# ── Fetch matches ESPN (ATP + WTA) ───────────────────────────────────────────
def fetch_espn_matches(tour: str) -> list[dict]:
    """tour = 'atp' ou 'wta'"""
    url = f"https://site.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("events", [])
    except Exception as e:
        print(f"ESPN {tour} error: {e}")
        return []


# ── Fetch odds Betclic (tennis) ──────────────────────────────────────────────
def fetch_betclic_odds() -> dict:
    """Retourne un dict {joueur_lower: cote} depuis l'API Betclic"""
    url = "https://www.betclic.fr/api/v2/sports/tennis/matches?offset=0&limit=50"
    odds_map = {}
    try:
        r = requests.get(url, headers={**HEADERS, "Referer": "https://www.betclic.fr/"}, timeout=10)
        r.raise_for_status()
        data = r.json()
        matches = data.get("matches", data.get("data", []))
        for m in matches:
            for mkt in m.get("markets", []):
                for sel in mkt.get("selections", []):
                    name  = sel.get("name", "").lower()
                    price = sel.get("price", 0)
                    if name and price:
                        odds_map[name] = price
    except Exception as e:
        print(f"Betclic error: {e}")
    return odds_map


# ── Format message ────────────────────────────────────────────────────────────
def build_message(atp_events: list, wta_events: list, odds: dict) -> str:
    lines = [f"🎾 *Tennis du jour — {TODAY_STR}*\n"]

    def format_tour(events: list, label: str) -> list[str]:
        if not events:
            return [f"\n*{label}*\n_Aucun match trouvé_"]
        
        out = [f"\n*{label}*"]
        for ev in events:
            try:
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
