import os
import requests
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_CHAT = os.environ['TELEGRAM_CHAT_ID']
SERPAPI_KEY = os.environ['SERPAPI_KEY']
PARIS_TZ = pytz.timezone('Europe/Paris')
TODAY_STR = datetime.now(PARIS_TZ).strftime('%d/%m/%Y')

def fetch():
    r = requests.get('https://serpapi.com/search', params={
        'q': 'tennis',
        'hl': 'fr',
        'gl': 'fr',
        'api_key': SERPAPI_KEY,
    }, timeout=20)
    print('SerpApi: ' + str(r.status_code))
    data = r.json()
    games = data.get('sports_results', {}).get('games', [])
    print('Matchs: ' + str(len(games)))
    return games

def build(games):
    lines = ['Tennis du jour ' + TODAY_STR, '']
    if not games:
        lines.append('Aucun match trouve.')
        return chr(10).join(lines)
    current = None
    for g in games:
        teams = g.get('teams', [])
        if len(teams) < 2:
            continue
        tournament = g.get('tournament', g.get('league', 'Tennis'))
        if tournament != current:
            current = tournament
            lines.append('')
            lines.append('--- ' + tournament + ' ---')
        p1 = teams[0].get('name', '?')
        p2 = teams[1].get('name', '?')
        s1 = str(teams[0].get('score', ''))
        s2 = str(teams[1].get('score', ''))
        score = ' (' + s1 + '-' + s2 + ')' if s1 and s2 else ''
        status = g.get('status', '')
        st = ' [' + status + ']' if status else ''
        lines.append(p1 + ' vs ' + p2 + score + st)
    return chr(10).join(lines)

def send(text):
    url = 'https://api.telegram.org/bot' + TELEGRAM_TOKEN + '/sendMessage'
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        requests.post(url, data={'chat_id': TELEGRAM_CHAT, 'text': chunk}).raise_for_status()
    print('Telegram OK')

games = fetch()
msg = build(games)
print(msg)
send(msg)
