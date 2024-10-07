import json
import time
import requests
import os
from datetime import datetime
from environs import Env
from requests.exceptions import RequestException

env = Env()
env.read_env()

users_data_file = 'users_data.json'
schedules_file = 'schedules.json'
schedule_times_file = 'schedule_times.json'
url = f'https://api.telegram.org/bot{env("BOT_TOKEN")}/sendMessage'

def load_data(file):
    if not os.path.exists(file):
        return {}
    with open(file, 'r') as f:
        return json.load(f)

users_data = load_data(users_data_file)
schedules = load_data(schedules_file)

def send_message(chat_id, text, parse_mode="Markdown", retries=3):
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    attempt = 0
    while attempt < retries:
        try:
            response = requests.post(url, json=payload, timeout=10)  # Added timeout to avoid hanging
            if response.status_code == 200:
                print(f"Message successfully sent to {chat_id}.")
                return True
            else:
                print(f"Failed to send message to {chat_id}. Response: {response.text}")
        except RequestException as e:
            print(f"Request error while sending message to {chat_id}: {e}")

        attempt += 1
        print(f"Retrying ({attempt}/{retries})...")
        time.sleep(2)  # Wait 2 seconds before retrying

    print(f"Failed to send message to {chat_id} after {retries} attempts.")
    return False

def get_schedule(user_id):
    user_info = users_data.get(str(user_id), {})
    if not user_info:
        return "User information not found."

    university = user_info.get('university', 'Unknown University')
    degree = user_info.get('degree', 'Unknown Degree')
    group = user_info.get('group', 'Unknown Group')
    today = datetime.now().strftime('%A')

    group_schedule = schedules.get(university, {}).get("degrees", {}).get(degree, {}).get("groups", {}).get(group, {}).get(today)
    
    if group_schedule:
        schedule_message = f"📅 Schedule for *{today}*:\n\n"
        schedule_message += f"🏫 University: *{university}*\n"
        schedule_message += f"🎓 Degree: *{degree}*\n"
        schedule_message += f"👥 Group: *{group}*\n\n"
        schedule_message += "*Lessons:*\n"
        
        for time_slot, lesson_info in group_schedule.items():
            schedule_message += f"🕒 *{time_slot}*\n"
            schedule_message += f"📘 Subject: {lesson_info[0]}\n"
            if len(lesson_info) > 1:
                teacher_name = lesson_info[1].strip()
                teacher_info = lesson_info[2].strip()
                if teacher_info.lower() != "none":
                    schedule_message += f"👤 Teacher: {teacher_name} ({teacher_info})\n"
                else:
                    schedule_message += f"👤 Teacher: {teacher_name}\n"
            schedule_message += "\n"

        return schedule_message
    else:
        return f"📅 Schedule for *{today}*:\n\n🏫 University: *{university}*\n🎓 Degree: *{degree}*\n👥 Group: *{group}*\n\nNo lessons scheduled for today."

def check_notifications():
    """Check and send notifications based on the schedule times."""
    print("Starting notification service...")
    while True:
        now = datetime.now().strftime('%H:%M')
        users_to_notify = []

        try:
            with open(schedule_times_file, 'r') as infile:
                data = json.load(infile)

            for user_id, notify_time in data.items():
                if notify_time == now:
                    users_to_notify.append(user_id)  # Collect users to notify.

            for user_id in users_to_notify:
                print(f"Sending schedule notification to user {user_id} at {now}.")
                message = get_schedule(user_id)
                send_message(user_id, message)

        except FileNotFoundError:
            print(f"File {schedule_times_file} not found.")
        except Exception as e:
            print(f"An error occurred while checking notifications: {e}")

        time.sleep(60)

if __name__ == '__main__':
    check_notifications()
