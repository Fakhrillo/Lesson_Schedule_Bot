import time, os, requests
import pandas as pd
from requests.exceptions import RequestException
from environs import Env

env = Env()
env.read_env()

url = f'https://api.telegram.org/bot{env("BOT_TOKEN")}/sendMessage'

# Constants for Google Sheets documents and file paths
COURSE_TIMETABLES = {
    '1-course': {
        'list1': (env("COURSE_1"), '0'),
        'list2': (env("COURSE_1"), '1187396123')
    },
    '2-course': {
        'list1': (env("COURSE_2"), '0'),
        'list2': (env("COURSE_2"), '1187396123'),
        'list3': (env("COURSE_2"), '554105149'),
        'list4': (env("COURSE_2"), '514459562')
    },
    '3-course': {
        'list1': (env("COURSE_3"), '0')
    }
}

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

def download_sheet(sheet_id, gid, list_name):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    response = requests.get(url)
    if response.status_code == 200:
        new_file = f"new_{list_name}.csv"
        with open(new_file, 'wb') as file:
            file.write(response.content)
        return new_file
    else:
        print(f"Failed to download the sheet for {list_name}.")
        return None


def check_for_sheet_changes():
    changes = ""
    for course, lists in COURSE_TIMETABLES.items():
        course_changed = False
        for list_name, (sheet_id, gid) in lists.items():
            new_file = download_sheet(sheet_id, gid, f"{course}_{list_name}")
            if new_file:
                existing_file = f"{course}_{list_name}.csv"
                if os.path.exists(existing_file):
                    try:
                        # Load both files into DataFrames
                        existing_df = pd.read_csv(existing_file)
                        new_df = pd.read_csv(new_file)

                        # Check if DataFrames are equal
                        if not existing_df.equals(new_df):
                            # Overwrite the existing file
                            os.remove(existing_file)
                            os.rename(new_file, existing_file)
                            course_changed = True
                        else:
                            os.remove(new_file)
                    except Exception as e:
                        print(f"Error while comparing files for {course} {list_name}: {e}")
                        os.remove(new_file)
                else:
                    # If no existing file, save the new file as the initial version
                    os.rename(new_file, existing_file)
                    course_changed = True

        if course_changed:
            changes += f"Changes in {course} timetable. "

    if changes:
        send_message(env("GROUP_ID"), f"*{changes}*")
    else:
        send_message(env("GROUP_ID"), f"No changes found")


while True:
    check_for_sheet_changes()
    time.sleep(18000)
