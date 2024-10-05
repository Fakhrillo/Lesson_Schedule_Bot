import telebot
import json
import os
from datetime import datetime
from environs import Env

env = Env()
env.read_env()

API_TOKEN = env("BOT_TOKEN")
ADMINS: list[int] = [1064331548]

SCHEDULES_FILE = 'schedules.json'
USERS_DATA_FILE = 'users_data.json'
PENDING_PROPOSALS_FILE = 'pending_proposals.json'

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
pending_proposals = load_data(PENDING_PROPOSALS_FILE)

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
        bot.send_message(message.chat.id, f"Welcome back, {user_name}! Use /schedule to view your group's schedule or /addschedule to propose a new one.")
    else:
        bot.send_message(message.chat.id, f"Welcome {user_name}! Please select your university.")
        show_universities(message)

def show_universities(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for university in schedules.keys():
        markup.add(university)
    markup.add("Not my university")
    bot.send_message(message.chat.id, "Select your university:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_university_selection)

def handle_university_selection(message):
    selected_university = message.text
    if selected_university == "Not my university":
        bot.send_message(message.chat.id, "Please enter the name of your university:")
        bot.register_next_step_handler(message, handle_new_university)
    elif selected_university in schedules:
        user_data = {"university": selected_university}
        show_degrees(message, selected_university, user_data)
    else:
        bot.send_message(message.chat.id, "Invalid university. Please select again.")
        show_universities(message)

def handle_new_university(message):
    new_university = message.text
    if new_university in schedules:
        bot.send_message(message.chat.id, "This university already exists. Please choose it from the list.")
        show_universities(message)
    else:
        schedules[new_university] = {"degrees": {}}
        save_data(SCHEDULES_FILE, schedules)
        bot.send_message(message.chat.id, f"University {new_university} added! Now, please select your degree.")
        user_data = {"university": new_university}
        show_degrees(message, new_university, user_data)

def show_degrees(message, university, user_data):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for degree in schedules[university]["degrees"].keys():
        markup.add(degree)
    markup.add("Not my degree")
    bot.send_message(message.chat.id, "Select your degree:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_degree_selection, user_data)

def handle_degree_selection(message, user_data):
    selected_degree = message.text
    university = user_data["university"]
    if selected_degree == "Not my degree":
        bot.send_message(message.chat.id, "Please enter the name of your degree:")
        bot.register_next_step_handler(message, handle_new_degree, user_data)
    elif selected_degree in schedules[university]["degrees"]:
        user_data["degree"] = selected_degree
        show_groups(message, university, selected_degree, user_data)
    else:
        bot.send_message(message.chat.id, "Invalid degree. Please select again.")
        show_degrees(message, university, user_data)

def handle_new_degree(message, user_data):
    new_degree = message.text
    university = user_data["university"]
    if new_degree in schedules[university]["degrees"]:
        bot.send_message(message.chat.id, "This degree already exists. Please choose it from the list.")
        show_degrees(message, university, user_data)
    else:
        schedules[university]["degrees"][new_degree] = {"groups": {}}
        save_data(SCHEDULES_FILE, schedules)
        bot.send_message(message.chat.id, f"Degree {new_degree} added! Now, please select your group.")
        user_data["degree"] = new_degree
        show_groups(message, university, new_degree, user_data)

def show_groups(message, university, degree, user_data):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for group in schedules[university]["degrees"][degree]["groups"].keys():
        markup.add(group)
    markup.add("Not my group")
    bot.send_message(message.chat.id, "Select your group:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_group_selection, user_data)

def handle_group_selection(message, user_data):
    selected_group = message.text
    university = user_data["university"]
    degree = user_data["degree"]
    if selected_group == "Not my group":
        bot.send_message(message.chat.id, "Please enter the name of your group:")
        bot.register_next_step_handler(message, handle_new_group, user_data)
    elif selected_group in schedules[university]["degrees"][degree]["groups"]:
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
        bot.send_message(message.chat.id, f"Now, use /schedule to view your group's schedule or /addschedule to propose a new one.")
    else:
        bot.send_message(message.chat.id, "Invalid group. Please select again.")
        show_groups(message, university, degree, user_data)

def handle_new_group(message, user_data):
    new_group = message.text
    university = user_data["university"]
    degree = user_data["degree"]
    if new_group in schedules[university]["degrees"][degree]["groups"]:
        bot.send_message(message.chat.id, "This group already exists. Please choose it from the list.")
        show_groups(message, university, degree, user_data)
    else:
        schedules[university]["degrees"][degree]["groups"][new_group] = {}
        save_data(SCHEDULES_FILE, schedules)
        user_data["group"] = new_group
        bot.send_message(message.chat.id, f"Group {new_group} added! Registration complete!")
        save_user_info(
            user_id=str(message.chat.id),
            first_name=message.chat.first_name,
            username=message.chat.username,
            university=user_data["university"],
            degree=user_data["degree"],
            group=user_data["group"]
        )
        bot.send_message(message.chat.id, f"Now, use /addschedule to propose a new schedule for your group.")

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
        lessons = '\n'.join(group_schedule)
        bot.send_message(message.chat.id, f"Schedule for *{today}*:\n\nUniversity: *{university}*\nDegree: *{degree}*\nGroup: *{group}*\nLessons:\n*{lessons}*", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, f"Schedule for *{today}*:\n\nUniversity: *{university}*\nDegree: *{degree}*\nGroup: *{group}*\nLessons: No lessons scheduled for today.", parse_mode="Markdown")

@bot.message_handler(commands=['addschedule'])
def propose_schedule(message):
    bot.send_message(message.chat.id, "Please send the schedule details in this format:\nUniversity:Degree:Group:Day:Lessons (comma separated).")
    bot.register_next_step_handler(message, handle_schedule_proposal)

def handle_schedule_proposal(message):
    try:
        user_id = str(message.chat.id)
        university, degree, group, day, lessons = message.text.split(':')
        lessons = lessons.split(',')
        if user_id in ADMINS:
            add_schedule(university, degree, group, day, lessons)
            bot.send_message(message.chat.id, f"Schedule added for {group} on {day}.")
        else:
            proposal_id = str(len(pending_proposals) + 1)
            pending_proposals[proposal_id] = {
                'proposer_id': user_id,
                'university': university,
                'degree': degree,
                'group': group,
                'day': day,
                'lessons': lessons
            }
            save_data(PENDING_PROPOSALS_FILE, pending_proposals)
            for admin_id in ADMINS:
                bot.send_message(admin_id, f"New schedule proposal from @{message.chat.username}:\nUniversity: {university}\nDegree: {degree}\nGroup: {group}\nDay: {day}\nLessons: {', '.join(lessons)}\nUse /approve {proposal_id} to approve or /reject {proposal_id} to reject.")
            bot.send_message(message.chat.id, "Your schedule proposal has been sent to the admins for approval.")
    except ValueError:
        bot.send_message(message.chat.id, "Invalid format. Please use the correct format: University:Degree:Group:Day:Lessons.")

@bot.message_handler(commands=['approve', 'reject'])
def handle_admin_action(message):
    command, proposal_id = message.text.split()
    proposal = pending_proposals.get(proposal_id)
    
    if not proposal:
        bot.send_message(message.chat.id, "Invalid proposal ID.")
        return
    
    if command == '/approve':
        add_schedule(proposal['university'], proposal['degree'], proposal['group'], proposal['day'], proposal['lessons'])
        bot.send_message(message.chat.id, f"Proposal {proposal_id} approved.")
        bot.send_message(proposal['proposer_id'], "Your schedule proposal has been approved.")
    elif command == '/reject':
        bot.send_message(message.chat.id, f"Proposal {proposal_id} rejected.")
        bot.send_message(proposal['proposer_id'], "Your schedule proposal has been rejected.")
    
    pending_proposals.pop(proposal_id)
    save_data(PENDING_PROPOSALS_FILE, pending_proposals)

def add_schedule(university, degree, group, day, lessons):
    if university not in schedules:
        schedules[university] = {"degrees": {}}
    if degree not in schedules[university]["degrees"]:
        schedules[university]["degrees"][degree] = {"groups": {}}
    if group not in schedules[university]["degrees"][degree]["groups"]:
        schedules[university]["degrees"][degree]["groups"][group] = {}
    
    schedules[university]["degrees"][degree]["groups"][group][day] = lessons
    save_data(SCHEDULES_FILE, schedules)

bot.polling()
