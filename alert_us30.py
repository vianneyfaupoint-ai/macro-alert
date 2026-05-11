import os
import requests
from datetime import datetime, timedelta

# Configuration Telegram
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def get_now_paris():
    # Calcul manuel de l'heure de Paris (UTC+2 en été)
    # C'est plus simple et ça évite les erreurs de modules manquants
    return datetime.utcnow() + timedelta(hours=2)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Erreur envoi Telegram : {e}")
        return False

def main():
    now = get_now_paris()
    heure_formattee = now.strftime("%H:%M:%S")
    
    print(f"Exécution du script à {heure_formattee} (Heure de Paris)")
    
    # Ton message d'alerte
    message = f"🚀 *US30 Macro Alert*\n\nIl est {heure_formattee}, le script est bien lancé !"
    
    if send_telegram_message(message):
        print("✅ Message envoyé avec succès !")
    else:
        print("❌ Échec de l'envoi.")

if __name__ == "__main__":
    main()
