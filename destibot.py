import string
import random
import json
import requests
import time
import re
import logging
import sys
from functools import reduce
from itertools import chain
from urllib3.exceptions import HTTPError
from bot_util import *


# mehr Kategorien, größere Auswahl innerhalb
# feedback
# Immer außerhalb von Query oder help: Buttons für Go, Category, Help bereithalten
# persönliche Eingaben speichern

# Modes
STANDARD = 0
PRO = 1


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


three_dices = u'🤔🤔🤔'
thinking = Random_Sticker_Reply(u'🤔')
destiny = [thinking] + \
    [Text_Reply_Keyboard("Bow to your destiny!", [["🙇", "🔄"]])]

confused = Text_Reply_Keyboard(
    "I'm not sure what you are saying 🤔 Can you use some /help?", [["👍", "👎"]])
suggest_help = Text_Reply_Keyboard(
    "Ok, sure! Try to press this: /help", [["/help", "👎"]])
default_suggestions = [[u'Start new game!', u'/categories', u'/help']]


def send_choice(choice):
    return destiny + [Text_Reply(choice)]


def send_help(state):
    state['phase'] = 'expecting_help'
    return [confused]


def do_go(state, message, info):
    phase = state.get('phase', 'unknown')
    if (phase == 'expecting_go'):
        if state['choices'] != []:
            choice = choose(state['choices'])
            state['phase'] = 'was_go'
            return send_choice(choice)
        else:
            state['phase'] = 'expecting_help'
            return [confused]
    else:
        print(str(info))
        return do_query(state, message, info, has_buttons=False)


def do_abort(state, message, info):
    phase = state.get('phase', 'unknown')
    state['phase'] = 'default'
    if phase == 'was_go':
        return [Text_Reply_Keyboard("What's up next?", default_suggestions)]
    return [Text_Reply_Keyboard("Ok, let's try again!", default_suggestions)]


def do_again(state, message, info):
    if 'choices' in state and state['choices'] != [] and 'phase' in state and state['phase'] == 'was_go':
        choice = choose(state['choices'])
        return send_choice(choice)
    else:
        return send_help(state)


def do_yes(state, message, info):
    phase = state.get('phase', 'unknown')
    state['phase'] = 'yes'
    if phase == 'expecting_help':
        state['phase'] = 'expecting_help'
        return [suggest_help]
    elif phase == 'proposed_game':
        return do_query(state, message, info, init_choices=state['choices'], has_buttons=False)
    else:
        return send_help(state)


def do_no(state, message, info):
    phase = state.get('phase', 'unknown')
    state['phase'] = 'no'
    if phase == 'expecting_help' or phase == 'proposed_game':
        state['phase'] = 'default'
        return [Text_Reply_Keyboard("Ok, sure!", default_suggestions)]
    else:
        return send_help(state)


def do_start(state, message, info):
    state['phase'] = 'default'
    welcome = info['welcome']
    return [Text_Reply_Keyboard(welcome, default_suggestions)]


def do_help(state, message, info):
    state['phase'] = 'default'
    suggestion_text = '\n'.join(info['suggestions'])
    suggestions = [Text_Reply(suggestion_text)]
    welcome = Text_Reply_Keyboard(info['welcome'], [info['suggestions']])
    gif = Animation_Reply()
    return [welcome] + suggestions + [gif]


def propose_game(state, message, info):
    state['choices'] = [message]
    state['phase'] = 'proposed_game'
    proposal = f"Start a new game with this item: '{message}'?"
    keyboard = Text_Reply_Keyboard(
        proposal, [["👍", "👎", "/help"]])
    return [keyboard]


def do_query(state, message, info, init_choices=None, has_buttons=True):
    init_choices = init_choices if init_choices else []
    state['choices'] = init_choices

    choice_text = f"Send me some {'' if init_choices == [] else 'more '}choices{' (text or buttons)' if has_buttons else ''}:"
    state['phase'] = 'expecting_go'
    state['choice_text'] = choice_text
    keyboard = Text_Reply_Keyboard(
        choice_text, [['go', 'abort'], list(info.get('choices', []))])
    initial_choices = list(map(Text_Reply, init_choices))
    return [keyboard] + initial_choices


def do_persons(state, message, info):
    # do default
    return do_default(state, message)
    # hidden code
    """
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
    return three_dices + [choice]"""


def do_default_game(state, message, info):
    return do_query(state, message, {}, has_buttons=False)


def do_default(state, message):
    items = extract_choices(message)
    phase = state.get('phase', 'unknown')
    if phase == 'expecting_go':
        state['choices'] += [message]
        return []
    elif phase == 'proposed_save':
        return save_list(state, message)
    elif len(items) <= 1 or state['mode'] < PRO:
        return propose_game(state, message, {})
    state['choices'] = items
    state['phase'] = 'was_go'
    choice = choose(items)
    return send_choice(choice)


def do_category(state, message, info):
    categories = []
    for name, info in modes.items():
        if info.get('mode', '') == 'query':
            categories.append(name)
    if state['mode'] >= PRO and 'lists' in state and state['lists']:
        categories.append('/mylists')
    return [Text_Reply_Keyboard(
        "Here's a list of possible categories to choose from...", [categories + [u'❌']])]


def propose_save(state):
    state['phase'] = "proposed_save"
    msg = "Saving current list... Propose a name:"
    suggestions = [[u'❌', u'/help']]
    return [Text_Reply_Keyboard(msg, suggestions)]


def save_list(state, name):
    suggestions = default_suggestions
    if 'choices' not in state or state['choices'] == []:
        msg = "You proposed a save, but I do not remember anything you said..."
        state['phase'] = 'save_failed'
    else:
        if 'lists' not in state:
            state['lists'] = {}
        save_name = name.split()[0].lstrip('/')
        # Should we protect against overwriting?
        state['lists'][save_name] = state['choices']
        state['phase'] = 'saved_list'
        msg = f"Saved list! Find it with /{save_name}"
    return [Text_Reply_Keyboard(msg, suggestions)]


def do_save(state, message, info):
    match = re.match("/save (.*)", message)
    if match == None:
        # no name for list given, so ask for one
        return propose_save(state)
    else:
        arg = match.groups()[0]
        return save_list(state, arg)


def do_show_lists(state, message, info):
    if 'lists' not in state or state['lists'] == []:
        msg = "You do not have any lists! Try /save to create one."
    else:
        msg = "Your lists:\n" + "\n".join('/' + s for s in state['lists'])
    return [Text_Reply_Keyboard(msg, default_suggestions)]


def do_promode(state, message, info):
    state['phase'] = 'default'
    if state['mode'] == PRO:
        state['mode'] = STANDARD
        return [Text_Reply_Keyboard(info['goodbye'], default_suggestions)]
    state['mode'] = PRO
    suggestion_text = '\n'.join(info['suggestions'])
    suggestions = [Text_Reply(suggestion_text)]
    welcome = Text_Reply_Keyboard(info['welcome'], [info['suggestions']])
    return [welcome] + suggestions


def do_number_range(state, message, info):
    suggestions = default_suggestions
    regex = "(-?[0-9]+)[-–:](-?[0-9]+)$"
    match = re.match(regex, message)
    a, b = match.groups()
    r = list(range(int(a), int(b) + 1))
    if r == []:
        return [Text_Reply_Keyboard('You gave me nothing to choose from. Do you need /help?', [["/help", "👎"]])]
    state['phase'] = 'was_go'
    state['choices'] = list(map(str, r))
    choice = str(choose(r))
    return send_choice(choice)


modes_to_functions = {
    "yes": do_yes,
    "no": do_no,
    "start": do_start,
    "help": do_help,
    "persons": do_persons,
    "query": do_query,
    "easteregg_query": do_query,
    "go": do_go,
    "abort": do_abort,
    "again": do_again,
    "categories": do_category,
    "save": do_save,
    "default_game": do_default_game,
    "promode": do_promode,
    "showlists": do_show_lists,
    "number_range": do_number_range
}


def process_message(message, chatid):
    global states
    # found "bug": wenn man einfach nur einmal ohne Kontext "jo" eingibt -> er landet bei do_yes
    if chatid not in states:
        state = {}
        state['mode'] = STANDARD
        states[chatid] = state
    state = states[chatid]
    for name, info in modes.items():
        patterns = info["patterns"]
        ignore_case = info.get("ignore_case", True)
        flags = 0
        if ignore_case:
            # (mehrere) Flags setzen mit bitwise or
            flags |= re.IGNORECASE
        for pattern in patterns:
            # checke alle Patterns nach match
            if re.match(pattern, message, flags):
                # handler für gematchtes Pattern raussuchen
                handler = modes_to_functions[info['mode']]
                # state: gespeichert zu chatid, enthält 'expecting_go', 'expecting_help', 'choices'
                # message: gesendeter Text
                # info: patterns, mode, choices
                response = handler(state, message, info)
                print(f"Message: {message}")
                print(f"Phase: {state.get('phase', 'NULLPHASE')}\n")
                return response
    # No specific mode was identified, so check if any custom list was asked for
    if 'lists' in state and message.startswith('/'):
        msg = message.strip().lstrip('/')
        for name, choices in state['lists'].items():
            if name == msg:
                info = {'choices': choices}
                return do_query(state, message, info, [])
    response = do_default(state, message)
    print(f"Message: {message}")
    print(f"Phase: {state.get('phase', 'NULLPHASE')}\n")
    return response


def process_sticker(sticker, chatid):
    print(json.dumps(sticker))
    return []


def handle_update(update, basic_bot_url):
    send_message = "sendMessage"
    if "message" not in update or "from" not in update["message"]:
        # Not sure what to do here
        return
    chatid = str(update["message"]["from"]["id"])
    if "text" in update["message"]:
        text = update["message"]["text"]
        responses = process_message(text, chatid)
    elif "sticker" in update["message"]:
        sticker = update["message"]["sticker"]
        responses = process_sticker(sticker, chatid)
    else:
        responses = confused
    for i, response in enumerate(responses):
        requests.get(response.get_http_reply(basic_bot_url, chatid))
        print(response.get_http_reply(basic_bot_url, chatid))
        if i < (len(responses) - 1):
            time.sleep(0.3)


def task():
    global latest_update_served
    telegram_api_url = "https://api.telegram.org"
    bot_token = config["bot_token"]
    get_updates = "getUpdates"
    basic_bot_url = f"{telegram_api_url}/bot{bot_token}"
    update_request_url = f"{basic_bot_url}/{get_updates}?offset={latest_update_served+1}"
    req = requests.get(update_request_url)
    res = req.json()
    if res["ok"] != True:
        return
    res = res["result"]
    for update in res:
        update_id = update["update_id"]
        if update_id > latest_update_served:
            print(update)
            latest_update_served = update_id
            handle_update(update, basic_bot_url)



if __name__ == "__main__":
    logging.basicConfig(filename='destibot.log', level=logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler())
    with open('db.json', 'r') as f:
        states = json.load(f)
    try:
        while True:
            try:
                task()
                time.sleep(0.3)
            except HTTPError:
                logging.exception("Network error!")
            except KeyboardInterrupt:
                logging.exception("Keyboard interrupt. Shutting down!")
                sys.exit(0)
            except Exception:
                logging.exception("Unknown error!")
    finally:
        with open('db.json', 'w') as f:
            db_handle = f
            json.dump(states, db_handle, default=str)
