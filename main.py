import telebot
import json
import os
from datetime import datetime, timedelta
from environs import Env
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import io

env = Env()
env.read_env()

API_TOKEN = env("BOT_TOKEN")
ADMINS: list[int] = [1064331548, 1274378031]

SCHEDULES_FILE = 'schedules.json'
USERS_DATA_FILE = 'users_data.json'

bot = telebot.TeleBot(API_TOKEN)

def load_data(file):
    if not os.path.exists(file):
        return {}
    with open(file, 'r') as f:
        return json.load(f)

def save_data(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

schedules = load_data(SCHEDULES_FILE)
users_data = load_data(USERS_DATA_FILE)

def save_user_info(user_id, first_name, username, university, degree, group):
    users_data[user_id] = {
        'first_name': first_name,
        'username': username,
        'university': university,
        'degree': degree,
        'group': group
    }
    save_data(USERS_DATA_FILE, users_data)

@bot.message_handler(commands=['start'])
def start(message):
    schedules = load_data(SCHEDULES_FILE)
    users_data = load_data(USERS_DATA_FILE)
    user_name = message.from_user.first_name
    user_id = str(message.chat.id)
    if user_id in users_data:
        bot.send_message(message.chat.id, f"Welcome back, {user_name}! Use /schedule to view your group's schedule or type / to see available options.", reply_markup=telebot.types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, f"Welcome {user_name}! Please select your university.")
        show_universities(message)

@bot.message_handler(commands=['schedule'])
def get_schedule(message):
    user_id = str(message.chat.id)
    if user_id not in users_data:
        bot.send_message(message.chat.id, "You are not registered yet. Use /start to register.")
        return
    
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
        
        bot.send_message(message.chat.id, schedule_message, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, f"Schedule for *{today}*:\n\nUniversity: *{university}*\nDegree: *{degree}*\nGroup: *{group}*\nLessons: No lessons scheduled for today.", parse_mode="Markdown")

@bot.message_handler(commands=["change_group"])
def change_group(message):
    user_name = message.from_user.first_name
    bot.send_message(message.chat.id, f"Hey {user_name}! Please select your university.")
    show_universities(message)

@bot.message_handler(commands=['addschedule'])
def request_university_degree(message):
    user_id = message.chat.id
    if user_id not in ADMINS:
        bot.send_message(user_id, "You don't have permission to add a schedule.")
        return
    bot.send_message(user_id, "Please enter the university name:")
    bot.register_next_step_handler(message, handle_university_name)

def handle_university_name(message):
    university = message.text
    bot.send_message(message.chat.id, "Please enter the degree:")
    bot.register_next_step_handler(message, handle_degree, university)

def handle_degree(message, university):
    degree = message.text
    bot.send_message(message.chat.id, "Please upload the Excel file containing the schedule.")
    bot.register_next_step_handler(message, process_excel_file, university, degree)

def process_excel_file(message, university, degree):
    if message.content_type != 'document':
        bot.send_message(message.chat.id, "Please upload a valid Excel file.")
        return
    
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    with open('temp_schedule.xlsx', 'wb') as new_file:
        new_file.write(downloaded_file)
    
    schedule_json = parse_excel_to_json('temp_schedule.xlsx')

    bot.send_message(message.chat.id, "If you approve, reply with 'approve'. To reject, reply with 'reject'.")
    
    bot.register_next_step_handler(message, handle_approval, university, degree, schedule_json)

def handle_approval(message, university, degree, schedule_json):
    if message.text.lower() == 'approve':
        if university not in schedules:
            schedules[university] = {"degrees": {}}
        if degree not in schedules[university]["degrees"]:
            schedules[university]["degrees"][degree] = {"groups": {}}

        for group, days in schedule_json.items():
            schedules[university]["degrees"][degree]["groups"][group] = days
        
        save_data(SCHEDULES_FILE, schedules)
        bot.send_message(message.chat.id, "The schedule has been successfully added.")
    else:
        bot.send_message(message.chat.id, "The schedule was not added.")

def parse_excel_to_json(file_path):
    excel_data = pd.read_excel(file_path, sheet_name=None)
    sheet_data = excel_data['Лист1']  # Assuming sheet name is 'Лист1'
    
    def clean_text(text):
        """Removes leading and trailing whitespace and newlines."""
        return text.strip() if isinstance(text, str) else text

    parsed_schedule = {}
    for index, row in sheet_data.iterrows():
        group = clean_text(row['Groups'])
        time_slot = clean_text(row['Time'])
        
        if pd.notna(group) and pd.notna(time_slot):
            if group not in parsed_schedule:
                parsed_schedule[group] = {}
            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                lesson_info = row[day]
                if pd.notna(lesson_info):
                    if day not in parsed_schedule[group]:
                        parsed_schedule[group][day] = {}
                    # Split and clean each lesson entry
                    cleaned_lesson_info = [clean_text(info) for info in lesson_info.split(',')]
                    parsed_schedule[group][day][time_slot] = cleaned_lesson_info

    return parsed_schedule


def show_universities(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2, resize_keyboard=True)
    universities = list(schedules.keys())
    buttons = [telebot.types.KeyboardButton(university) for university in universities]
    
    markup.add(*buttons)
    bot.send_message(message.chat.id, "Select your university:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_university_selection)

def handle_university_selection(message):
    selected_university = message.text
    if selected_university in schedules:
        user_data = {"university": selected_university}
        show_degrees(message, selected_university, user_data)
    else:
        bot.send_message(message.chat.id, "Invalid university. Please select again.")
        show_universities(message)

def show_degrees(message, university, user_data):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2, resize_keyboard=True)
    degrees = list(schedules[university]["degrees"].keys())
    buttons = [telebot.types.KeyboardButton(degree) for degree in degrees]
    markup.add(*buttons)

    bot.send_message(message.chat.id, "Select your degree:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_degree_selection, user_data)

def handle_degree_selection(message, user_data):
    selected_degree = message.text
    university = user_data["university"]
    if selected_degree in schedules[university]["degrees"]:
        user_data["degree"] = selected_degree
        show_groups(message, university, selected_degree, user_data)
    else:
        bot.send_message(message.chat.id, "Invalid degree. Please select again.")
        show_degrees(message, university, user_data)

def show_groups(message, university, degree, user_data):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2, resize_keyboard=True)
    groups = list(schedules[university]["degrees"][degree]["groups"].keys())
    buttons = [telebot.types.KeyboardButton(group) for group in groups]
    markup.add(*buttons)

    bot.send_message(message.chat.id, "Select your group:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_group_selection, user_data)

def handle_group_selection(message, user_data):
    selected_group = message.text
    university = user_data["university"]
    degree = user_data["degree"]
    if selected_group in schedules[university]["degrees"][degree]["groups"]:
        user_data["group"] = selected_group
        bot.send_message(message.chat.id, f"You selected {selected_group}. Registration complete!")
        save_user_info(
            user_id=str(message.chat.id),
            first_name=message.chat.first_name,
            username=message.chat.username,
            university=user_data["university"],
            degree=user_data["degree"],
            group=user_data["group"]
        )
        bot.send_message(message.chat.id, f"Now, use /schedule to view your group's schedule or type / to see available options.")
    else:
        bot.send_message(message.chat.id, "Invalid group. Please select again.")
        show_groups(message, university, degree, user_data)

@bot.message_handler(commands=['weekly'])
def get_weekly_schedule(message):
    user_id = str(message.chat.id)
    
    if user_id not in users_data:
        bot.send_message(message.chat.id, "You are not registered yet. Use /start to register.")
        return
    
    user_info = users_data[user_id]
    university = user_info['university']
    degree = user_info['degree']
    group = user_info['group']
    
    weekly_schedule = {}
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        day_schedule = schedules.get(university, {}).get("degrees", {}).get(degree, {}).get("groups", {}).get(group, {}).get(day, {})
        weekly_schedule[day] = day_schedule

    image_data = generate_weekly_schedule_image(weekly_schedule, university, degree, group)
    bot.send_photo(message.chat.id, image_data)

def generate_weekly_schedule_image(weekly_schedule, university, degree, group):
    cell_width = 250
    cell_height = 120
    header_height = 100
    num_days = 5
    num_slots = 6

    image_width = (num_days + 1) * cell_width
    image_height = (num_slots + 1) * cell_height + header_height
    
    img = Image.new('RGB', (image_width, image_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 20)
        header_font = ImageFont.truetype("arial.ttf", 30)
    except IOError:
        font = ImageFont.load_default()
        header_font = ImageFont.load_default()

    # Draw header
    header_text = f"University: {university} | Degree: {degree} | Group: {group}"
    header_text_bbox = draw.textbbox((0, 0), header_text, font=header_font)
    header_text_width = header_text_bbox[2] - header_text_bbox[0]
    draw.text(
        ((image_width - header_text_width) / 2, 20),
        header_text, font=header_font, fill=(0, 0, 0)
    )
    
    # Draw table
    table_top = header_height
    for i in range(num_days + 2):
        for j in range(num_slots + 1):
            top_left = (i * cell_width, table_top + j * cell_height)
            bottom_right = ((i + 1) * cell_width, table_top + (j + 1) * cell_height)
            draw.rectangle([top_left, bottom_right], outline=(0, 0, 0), width=2)

    # Fill in days
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    for i, day in enumerate(days):
        draw_centered_text(draw, day, ((i + 1) * cell_width, table_top, (i + 2) * cell_width, table_top + cell_height), font)

    # Fill in time slots
    time_slots = ['9:10-10:20', '10:30-11:50', '12:00-13:20', '14:20-15:40', '15:50-17:10', '17:20-18:40']
    for j, time_slot in enumerate(time_slots):
        draw_centered_text(draw, time_slot, (0, table_top + (j + 1) * cell_height, cell_width, table_top + (j + 2) * cell_height), font)
        
        for i, day in enumerate(days):
            lessons = weekly_schedule.get(day, {}).get(time_slot, [])
            if lessons:
                cell_rect = ((i + 1) * cell_width, table_top + (j + 1) * cell_height, (i + 2) * cell_width, table_top + (j + 2) * cell_height)
                draw_wrapped_text(draw, lessons, cell_rect, font)

    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format='PNG')
    img_byte_array.seek(0)
    
    return img_byte_array

def draw_centered_text(draw, text, rect, font, fill=(0, 0, 0)):
    x1, y1, x2, y2 = rect
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (x2 - x1 - text_width) / 2 + x1
    y = (y2 - y1 - text_height) / 2 + y1
    draw.text((x, y), text, font=font, fill=fill)

def draw_wrapped_text(draw, lessons, rect, font, fill=(0, 0, 0)):
    x1, y1, x2, y2 = rect
    max_width = x2 - x1
    
    lines = []
    current_line = []
    
    for word in lessons:        
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]

        word = "" if "none" in word else word
        if text_width <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))

    line_height = draw.textbbox((0, 0), 'A', font=font)[3]
    total_text_height = len(lines) * line_height
    y = y1 + (y2 - y1 - total_text_height) / 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = x1 + (max_width - text_width) / 2
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height


bot.polling()
