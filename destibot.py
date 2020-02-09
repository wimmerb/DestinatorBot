import string
import random
import json
import requests
import time
import re
from itertools import chain

latest_update_served = 0
with open("eastereggs.json") as f:
    modes = json.load(f)
with open('config.json') as f:
    config = json.load(f)
states = {}


def choose(choice_list):
    return random.choice(choice_list)


def extract_choices(msg):
    # ... anderer Vorschlag: nur nach Kommas trennen lassen
    # sicherstellen dass wir nen String haben
    # Problem: zerstoert Kontrollsequenz für Emojis
    l = None
    if ',' in msg:
        l = msg.split(',')
    else:
        l = [a for a in msg.split() if a != '']
    return l


three_dices = [u'🎲', u'🎲🎲', u'🎲🎲🎲']

confused = "I'm not sure what you are saying 🤔 Can you use some /help?"


def do_yes(state, message, info):
    expecting_go = state.get('expecting_go', False)
    expecting_help = state.get('expecting_help', False)
    if expecting_go:
        choice = choose(state['choices'])
        state['expecting_go'] = False
        return three_dices + [choice]
    elif expecting_help:
        state['expecting_help'] = False
        return ["Ok, sure! Try this to press this: /help"]
    else:
        state['expecting_help'] = True
        return [confused]


def do_no(state, message, info):
    expecting_go = state.get('expecting_go', False)
    expecting_help = state.get('expecting_help', False)
    if expecting_go:
        return ["Ok! You can add some more choices:"]
    elif expecting_help:
        state['expecting_help'] = False
        return ["Ok, sure!"]
    else:
        state['expecting_help'] = True
        return [confused]


def do_start(state, message, info):
    welcome = """Hey there!
This is your destinator!
Can I help you find your destiny today?
If you are unsure what to do, you can try /help"""
    return [welcome]


def do_help(state, message, info):
    state['expecting_help'] = False
    suggestions = info['suggestions']
    welcome = info['welcome']
    return [welcome] + suggestions


def do_query(state, message, info):
    state['expecting_go'] = True
    state['choices'] = list(info['choices'])
    query = info.get('query', "Ready to find your destiny?")
    choice_text = info.get('choice_text', "These are your choices:")
    state['query'] = query
    state['choice_text'] = choice_text
    return [choice_text] + state['choices'] + [query]


def do_persons(state, message, info):
    items = extract_choices(message)
    patterns = info['patterns']
    choices = info['choices']

    def replace(choice):
        for pattern in patterns:
            if re.match(pattern, choice):
                return choices
        return [choice]
    choices = list(chain(*map(replace, items)))
    choice = choose(choices)
    return three_dices + [choice]


def do_default(state, message):
    items = extract_choices(message)
    expecting_go = state.get('expecting_go', False)
    if expecting_go:
        state['choices'] += items
        return [state['choice_text']] + state['choices'] + [state['query']]
    choice = choose(items)
    return three_dices + [choice]


modes_to_functions = {
    "yes": do_yes,
    "no": do_no,
    "start": do_start,
    "help": do_help,
    "persons": do_persons,
    "query": do_query
}


def process_message(message, chatid):
    global states
    if chatid not in states:
        states[chatid] = {}
    state = states[chatid]
    for name, info in modes.items():
        patterns = info["patterns"]
        ignore_case = info.get("ignore_case", True)
        flags = 0
        if ignore_case:
            flags |= re.IGNORECASE
        for pattern in patterns:
            if re.match(pattern, message, flags):
                handler = modes_to_functions[info['mode']]
                response = handler(state, message, info)
                return response
    response = do_default(state, message)
    return response


def fetchLatestUpdate():
    return


def handle_update(update, basic_bot_url):
    send_message = "sendMessage"
    if "message" not in update or "from" not in update["message"]:
        # Not sure what to do here
        return
    chatid = update["message"]["from"]["id"]
    if "text" not in update["message"]:
        responses = [confused]
    else:
        text = update["message"]["text"]
        # failt bei leerer Liste
        responses = process_message(text, chatid)
    # fstring refactor
    for response in responses[:-1]:
        requests.get(
            f"{basic_bot_url}/{send_message}?chat_id={chatid}&text={response}")
        time.sleep(0.3)
    requests.get(
        f"{basic_bot_url}/{send_message}?chat_id={chatid}&text={responses[-1]}")


def task():
    global latest_update_served
    telegram_api_url = "https://api.telegram.org"
    bot_token = config["bot_token"]
    get_updates = "getUpdates"
    basic_bot_url = f"{telegram_api_url}/bot{bot_token}"
    update_request_url = f"{basic_bot_url}/{get_updates}?offset={latest_update_served+1}"
    req = requests.get(update_request_url)
    res = req.json()["result"]
    for update in res:
        update_id = update["update_id"]
        if update_id > latest_update_served:
            latest_update_served = update_id
            handle_update(update, basic_bot_url)


if __name__ == "__main__":
    while True:
        task()
        time.sleep(0.3)
