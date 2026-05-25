import anthropic
import os
import requests
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT_ID"]

TODAY = datetime.now().strftime("%d/%m/%Y")

# ── Claude search prompt ─────────────────────────────────────────────────────
PROMPT = f"""
Tu es un assistant tennis expert. Nous sommes le {TODAY}.

Recherche sur le web les matchs de tennis ATP et WTA programmés AUJOURD'HUI ({TODAY}).

Pour chaque match trouvé, fournis :
- Tournoi (nom + surface + catégorie ex: ATP 1000 / WTA 1000 / Grand Chelem)
- Joueur 1 vs Joueur 2 (avec classement ATP/WTA si disponible)
- Tour (1er tour, QF, SF, Finale…)
- Heure indicative (heure française si possible)
- Cote indicative du favori (ex: 1.45 pour Djokovic) — cherche sur Betclic, Unibet ou Winamax

Formate la réponse en sections claires par tournoi, avec des emojis pour la lisibilité.
Termine par un court "⭐ Match du jour" avec le match le plus intéressant selon toi et pourquoi.

Si aucun match majeur aujourd'hui (day off), dis-le clairement.
"""

# ── Run Claude with web search ───────────────────────────────────────────────
def get_tennis_briefing() -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": PROMPT}],
    )

    # Collect all text blocks from the response
    text_parts = [block.text for block in response.content if hasattr(block, "text")]
    return "\n".join(text_parts).strip()


# ── Send Telegram ────────────────────────────────────────────────────────────
def send_telegram(body: str):
    # Telegram limite à 4096 chars par message
    header  = f"🎾 *Tennis du jour — {TODAY}*\n\n"
    message = header + body

    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for chunk in chunks:
        url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT, "text": chunk, "parse_mode": "Markdown"}
        r = requests.post(url, data=data)
        r.raise_for_status()
    print("✅ Telegram envoyé")


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🔍 Recherche des matchs du {TODAY}…")
    briefing = get_tennis_briefing()
    print(briefing)

    send_telegram(briefing)
    print("🏁 Terminé")
