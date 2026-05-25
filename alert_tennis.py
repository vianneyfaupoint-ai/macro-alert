import os
import requests
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_CHAT = os.environ['TELEGRAM_CHAT_ID']
PARIS_TZ = pytz.timezone('Europe/Paris')
TODAY = datetime.now(PARIS_TZ)
TODAY_STR = TODAY.strftime('%d/%m/%Y')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'fr-FR,fr;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


def fetch_google_tennis():
    matches = []
    try:
        from bs4 import BeautifulSoup
        r = requests.get(
            'https://www.google.com/search?q=tennis+roland+garros+scores+aujourd+hui&hl=fr&gl=FR',
            headers=HEADERS, timeout=15)
        print('Google: ' + str(r.status_code) + ' (' + str(len(r.text)) + ' chars)')
        soup = BeautifulSoup(r.text, 'lxml')
        for row in soup.find_all('div', class_=True):
            text = row.get_text(' ', strip=True)
            if ' vs ' in text.lower() or (' - ' in text and len(text) < 80):
                if any(c.isdigit() for c in text):
                    matches.append(text)
    except Exception as e:
        print('Google error: ' + str(e))
    return matches


def fetch_serpapi():
    matches = []
    try:
        from bs4 import BeautifulSoup
        queries = [
            'https://www.google.com/search?q=roland+garros+2026+scores+du+jour&hl=fr&gl=FR',
            'https://www.google.com/search?q=ATP+WTA+tennis+matchs+aujourd+hui+25+mai+2026&hl=fr&gl=FR',
        ]
        for url in queries:
            r = requests.get(url, headers=HEADERS, timeout=15)
            print('Google search: ' + str(r.status_code))
            soup = BeautifulSoup(r.text, 'lxml')
            for el in soup.select('[data-ved], .BNeawe, .r0bn4c, .rQMQod'):
                text = el.get_text(' ', strip=True)
                if len(text) > 5 and len(text) < 120:
                    matches.append(text)
            if matches:
                break
    except Exception as e:
        print('Serpapi error: ' + str(e))
    return matches


def fetch_livescore():
    matches = []
    try:
        from bs4 import BeautifulSoup
        r = requests.get('https://www.livescore.com/en/tennis/', headers=HEADERS, timeout=15)
        print('livescore: ' + str(r.status_code) + ' (' + str(len(r.text)) + ' chars)')
        soup = BeautifulSoup(r.text, 'lxml')
        current = 'Tennis'
        for el in soup.find_all(['div', 'span', 'a']):
            cls = ' '.join(el.get('class', []))
            text = el.get_text(strip=True)
            if not text or len(text) > 100:
                continue
            if 'tournament' in cls.lower() or 'competition' in cls.lower():
                current = text
            elif 'participant' in cls.lower() or 'name' in cls.lower():
                if len(text) > 2:
                    matches.append({'name': text, 'tournament': current})
    except Exception as e:
        print('livescore error: ' + str(e))
    pairs = []
    i = 0
    while i < len(matches) - 1:
        pairs.append({
            'p1': matches[i]['name'],
            'p2': matches[i+1]['name'],
            'tournament': matches[i]['tournament'],
            'time': '?',
        })
        i += 2
    return pairs


def fetch_tennis24():
    from bs4 import BeautifulSoup
    matches = []
    try:
        r = requests.get('https://www.tennis24.com/', headers=HEADERS, timeout=15)
        print('tennis24: ' + str(r.status_code) + ' (' + str(len(r.text)) + ' chars)')
        soup = BeautifulSoup(r.text, 'lxml')
        current = 'Tennis'
        for el in soup.select('.sportName.tennis > div')[:80]:
            cls = el.get('class', [])
            if 'event__header' in cls:
                t = el.get_text(strip=True)
                if t:
                    current = t
            elif any('event__match' in c for c in cls):
                players = el.select('.event__participant')
                time_el = el.select_one('.event__time')
                score_el = el.select_one('.event__scores')
                if len(players) >= 2:
                    score = score_el.get_text(strip=True) if score_el else ''
                    matches.append({
                        'p1': players[0].get_text(strip=True),
                        'p2': players[1].get_text(strip=True),
                        'time': time_el.get_text(strip=True) if time_el else '?',
                        'score': score,
                        'tournament': current,
                    })
    except Exception as e:
        print('tennis24 error: ' + str(e))
    return matches


def build_message(matches):
    titre = 'Tennis du jour ' + TODAY_STR
    lines = [titre, '']
    if not matches:
        lines.append('Aucun match trouve.')
        lines.append('Programme: https://www.rolandgarros.com/fr-fr/tableau')
        return chr(10).join(lines)
    current_tour = None
    seen = set()
    for m in matches:
        if isinstance(m, str):
            lines.append(m)
            continue
        key = m.get('p1', '') + '-' + m.get('p2', '')
        if key in seen:
            continue
        seen.add(key)
        tour = m.get('tournament', 'Tennis')
        if tour != current_tour:
            current_tour = tour
            lines.append('')
            lines.append('--- ' + tour + ' ---')
        p1 = m.get('p1', '?')
        p2 = m.get('p2', '?')
        heure = m.get('time', '?')
        score = m.get('score', '')
        score_str = ' (' + score + ')' if score else ''
        lines.append(heure + ' | ' + p1 + ' vs ' + p2 + score_str)
    return chr(10).join(lines)


def send_telegram(text):
    url = 'https://api.telegram.org/bot' + TELEGRAM_TOKEN + '/sendMessage'
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        r = requests.post(url, data={'chat_id': TELEGRAM_CHAT, 'text': chunk})
        r.raise_for_status()
    print('Telegram OK')


if __name__ == '__main__':
    print('Matchs du ' + TODAY_STR + '...')
    matches = fetch_tennis24()
    print('tennis24: ' + str(len(matches)))
    if not matches:
        matches = fetch_livescore()
        print('livescore: ' + str(len(matches)))
    print('Total: ' + str(len(matches)))
    msg = build_message(matches)
    print(msg)
    send_telegram(msg)
    print('Termine')
