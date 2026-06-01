import os
import requests
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_CHAT = os.environ['TELEGRAM_CHAT_ID']
SERPAPI_KEY = os.environ['SERPAPI_KEY']

PARIS_TZ = pytz.timezone('Europe/Paris')
TODAY = datetime.now(PARIS_TZ)
TODAY_STR = TODAY.strftime('%d/%m/%Y')


def fetch_tennis_google():
    matches = []
    try:
        r = requests.get(
            'https://serpapi.com/search',
            params={
                'q': 'tennis',
                'hl': 'fr',
                'gl': 'fr',
                'api_key': SERPAPI_KEY,
            },
            timeout=20
        )
        print('SerpApi: ' + str(r.status_code))
        data = r.json()
        sports = data.get('sports_results', {})
        print('sports_results keys: ' + str(list(sports.keys())))
        games = sports.get('games', [])
        print('games: ' + str(len(games)))
        for game in games:
            teams = game.get('teams', [])
            if len(teams) >= 2:
                p1 = teams[0].get('name', '?')
                p2 = teams[1].get('name', '?')
                s1 = str(teams[0].get('score', ''))
                s2 = str(teams[1].get('score', ''))
                score = s1 + ' - ' + s2 if s1 or s2 else ''
                status = game.get('status', '')
                tournament = game.get('tournament', game.get('league', 'Tennis'))
                matches.append({
                    'p1': p1, 'p2': p2,
                    'score': score,
                    'status': status,
                    'tournament': tournament,
                })
    except Exception as e:
        print('SerpApi error: ' + str(e))
    return matches


def build_message(matches):
    lines = ['Tennis du jour ' + TODAY_STR, '']
    if not matches:
        lines.append('Aucun match trouve.')
        lines.append('Programme: https://www.rolandgarros.com/fr-fr/tableau')
        return chr(10).join(lines)
    current_tour = None
    for m in matches:
        tour = m.get('tournament', 'Tennis')
        if tour != current_tour:
            current_tour = tour
            lines.append('')
            lines.append('--- ' + tour + ' ---')
        p1 = m.get('p1', '?')
        p2 = m.get('p2', '?')
        score = m.get('score', '')
        status = m.get('status', '')
        score_str = ' (' + score + ')' if score else ''
        status_str = ' [' + status + ']' if status else ''
        lines.append(p1 + ' vs ' + p2 + score_str + status_str)
    return chr(10).join(lines)


def send_telegram(text):
    url = 'https://api.telegram.org/bot' + TELEGRAM_TOKEN + '/sendMessage'
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        r = requests.post(url, data={'chat_id': TELEGRAM_CHAT, 'text': chunk})
        r.raise_for_status()
    print('Telegram OK')


if __name__ == '__main__':
    print('Matchs du ' + TODAY_STR + '...')
    matches = fetch_tennis_google()
    print('Total matchs: ' + str(len(matches)))
    msg = build_message(matches)
    print(msg)
    send_telegram(msg)
    print('Termine')
