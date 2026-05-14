import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# Configuration via les secrets GitHub
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_macro_data():
    url = "https://www.investing.com/economic-calendar/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'lxml')
        events = []
        
        # On cherche les lignes du calendrier
        table = soup.find('table', id='economicCalendarData')
        rows = table.find_all('tr', class_='js-event-item')
        
        for row in rows:
            # On filtre pour n'avoir que les USA (drapeau américain) et Impact Fort (3 étoiles)
            flag = row.find('td', class_='flagCur')
            impact = row.find('td', class_='sentiment')
            
            if flag and "United States" in flag.get('title', '') and impact:
                stars = impact.find_all('i', class_='grayFullBullishIcon')
                if len(stars) >= 3:  # Impact Fort uniquement
                    time = row.get('data-event-datetime')
                    name = row.find('td', class_='event').text.strip()
                    events.append(f"🕒 {time[11:16]} | 🔥 **{name}**")
        
        return events
    except Exception as e:
        return [f"Erreur lors de la récupération : {e}"]

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    paris_tz = pytz.timezone('Europe/Paris')
    now = datetime.now(paris_tz).strftime("%d/%m/%Y %H:%M")
    
    data = get_macro_data()
    
    if data:
        header = f"🚀 *ALERTE MACRO US30*\n📅 {now}\n\n*Événements US à fort impact :*\n"
        full_message = header + "\n".join(data)
    else:
        full_message = f"📅 {now}\n✅ RAS : Aucun événement majeur aujourd'hui."
        
    send_to_telegram(full_message)
