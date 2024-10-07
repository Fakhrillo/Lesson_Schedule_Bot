import json, time, requests, os
from datetime import datetime
from environs import Env
env = Env()
env.read_env()


def load_data(file):
    if not os.path.exists(file):
        return {}
    with open(file, 'r') as f:
        return json.load(f)
    

users_data = load_data('users_data.json')
schedules = load_data('schedules.json')
url = f'https://api.telegram.org/bot{env("BOT_TOKEN")}/sendMessage'

def send_message(chat_id, text, parse_mode="Markdown"):
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"Failed to send message to {chat_id}: {response.text}")
    else:
        print(f"Message sent to {chat_id}")


def get_schedule(user_id):
    user_info = users_data[user_id]
    university = user_info['university']
    degree = user_info['degree']
    group = user_info['group']
    today = datetime.now().strftime('%A')
    
    group_schedule = schedules.get(university, {}).get("degrees", {}).get(degree, {}).get("groups", {}).get(group, {}).get(today)
    
    if group_schedule:
        schedule_message = f"Schedule for *{today}*:\n\n"
        schedule_message += f"University: *{university}*\n"
        schedule_message += f"Degree: *{degree}*\n"
        schedule_message += f"Group: *{group}*\n\n"
        schedule_message += "*Lessons:*\n"
        
        for time_slot, lesson_info in group_schedule.items():
            schedule_message += f"*{time_slot}*\n"
            schedule_message += f"Subject: {lesson_info[0]}\n"
            if len(lesson_info) > 1:
                if lesson_info[2].strip().lower() == "none":
                    schedule_message += f"Teacher: {lesson_info[1].strip()}\n"
                else:
                    schedule_message += f"Teacher: {lesson_info[1].strip()} ({lesson_info[2].strip()})\n"

            schedule_message += "\n"
        
        return schedule_message
    else:
        return f"Schedule for *{today}*:\n\nUniversity: *{university}*\nDegree: *{degree}*\nGroup: *{group}*\nLessons: No lessons scheduled for today."


def check_notifications():
    while True:
        now = datetime.now().strftime('%H:%M')
        try:
            with open('schedule_times.json', 'r') as infile:
                data = json.load(infile)

            for user_id, notify_time in data.items():
                if notify_time == now:
                    message = get_schedule(user_id)
                    try:
                        send_message(user_id, message)
                    except:
                        pass
        except FileNotFoundError:
            pass

        time.sleep(60)

if __name__ == '__main__':
    check_notifications()
