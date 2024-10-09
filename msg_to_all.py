import requests, os, json
from environs import Env
env = Env()
env.read_env()

BOT_TOKEN = env("BOT_TOKEN")

def load_data(file):
    with open(file, 'r') as f:
        return json.load(f)

message = "Hey everyone! Just a quick heads-up that we've made some updates to the timetable, so please take a moment to review your schedules. Thanks!"

photo_path = None

users_id = load_data("users_data.json").keys()

users_not_using_bot = []

def send_message(user_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': user_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    return requests.post(url, data=payload)

def send_photo(user_id, photo, caption):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto'
    payload = {
        'chat_id': user_id,
        'caption': caption,
        'parse_mode': 'Markdown'
    }
    with open(photo, 'rb') as file:
        files = {'photo': file}
        return requests.post(url, data=payload, files=files)

for user_id in users_id:
    try:
        if photo_path:
            response = send_photo(user_id, photo_path, message)
        else:
            response = send_message(user_id, message)
        
        if response.status_code == 200:
            print(f'Message has been sent to {user_id} successfully!')
        else:
            print(f'Error sending message: {response.status_code}, Couldn`t send message to: {user_id}')
            users_not_using_bot.append(user_id)
    except Exception as e:
        print(f'Error sending message: {e}, Couldn`t send message to: {user_id}')
        users_not_using_bot.append(user_id)

print(users_not_using_bot)