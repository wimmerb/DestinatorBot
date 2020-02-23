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
gif_text = "Here's a GIF explaining how it works:"
help_gif_response = [Text_Reply(gif_text), Animation_Reply("interactive_mode")]


def send_choice(choice):
    return destiny + [choice]


def send_help(state):
    state['phase'] = 'expecting_help'
    return [confused]


def is_phase_in(*phases):
    def check(state):
        phase = state.get('phase', 'unknown')
        return phase in phases
    return check


expecting_go = is_phase_in('expecting_go')


def do_go(state, message, info):
    if expecting_go(state):
        if state['choices'] != []:
            choice = choose(state['choices'])
            state['phase'] = 'was_go'
            return send_choice(choice)
        else:
            return send_help(state)
    else:
        return do_query(state, message, info, has_buttons=False)


def do_abort(state, message, info):
    phase = state.get('phase', 'unknown')
    state['phase'] = 'default'
    if phase == 'was_go':
        return [Text_Reply_Keyboard("What's up next?", default_suggestions)]
    return [Text_Reply_Keyboard("Ok, let's try again!", default_suggestions)]


expecting_bow = is_phase_in('was_go')


def do_bow(state, message, info):
    state['phase'] = 'default'
    return [Text_Reply_Keyboard("What's up next?", default_suggestions)]


expecting_again = expecting_bow


def do_again(state, message, info):
    if 'choices' in state and state['choices'] != [] and expecting_again(state):
        choice = choose(state['choices'])
        return send_choice(choice)
    else:
        return send_help(state)


expecting_yes = is_phase_in('expecting_help', 'proposed_game')


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


expecting_no = expecting_yes


def do_no(state, message, info):
    if expecting_no(state):
        state['phase'] = 'default'
        return [Text_Reply_Keyboard("Ok, sure!", default_suggestions)]
    else:
        state['phase'] = 'no'
        return send_help(state)


def do_start(state, message, info):
    state['phase'] = 'default'
    welcome = info['welcome']
    return [Text_Reply_Keyboard(welcome, default_suggestions)] + help_gif_response


def do_help(state, message, info):
    state['phase'] = 'default'
    suggestion_text = '\n'.join(info['suggestions'])
    suggestions = [Text_Reply(suggestion_text)]
    welcome = Text_Reply_Keyboard(info['welcome'], [info['suggestions']])
    return help_gif_response + [welcome] + suggestions


def propose_game(state, choice, info):
    state['choices'] = [choice]
    state['phase'] = 'proposed_game'
    proposal = f"Start a new game with this item?"
    keyboard = Text_Reply_Keyboard(
        proposal, [["👍", "👎", "/help"]])
    return [keyboard, choice]


def do_query(state, message, info, init_choices=None, has_buttons=True):
    init_choices = init_choices if init_choices else []
    state['choices'] = init_choices

    choice_text = f"Send me some {'' if init_choices == [] else 'more '}choices{' (text or buttons)' if has_buttons else ''}:"
    state['phase'] = 'expecting_go'
    state['choice_text'] = choice_text
    keyboard = Text_Reply_Keyboard(
        choice_text, [['go', 'abort'], list(info.get('choices', []))])
    return [keyboard] + init_choices


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


def do_default_game(state, message, info):
    return do_query(state, message, {}, has_buttons=False)


def do_category(state, message, info):
    categories = []
    for name, info in modes.items():
        if info.get('mode', '') == 'query':
            categories.append(name)
    if state['mode'] >= PRO and 'lists' in state and state['lists']:
        categories.append('/mylists')
    return [Text_Reply_Keyboard(
        "Here's a list of possible categories to choose from...", [[u'❌'] + categories])]


def propose_save(state):
    state['phase'] = "proposed_save"
    msg = "Saving current list... Propose a name:"
    suggestions = [[u'❌', u'/help']]
    return [Text_Reply_Keyboard(msg, suggestions)]


def get_choices(choices):
    result = []
    for choice in choices:
        if isinstance(choice, Text_Reply):
            result.append(choice.text)
        else:
            return None
    return result


def save_list(state, name):
    suggestions = default_suggestions
    if 'choices' not in state or state['choices'] == []:
        msg = "You proposed a save, but I do not remember anything you said..."
        state['phase'] = 'save_failed'
    else:
        if 'lists' not in state:
            state['lists'] = {}
        save_name = name.split()[0].lstrip('/')
        choices = get_choices(state['choices'])
        if choices == None:
            msg = "Cannot save lists with stickers!"
        else:
            # Should we protect against overwriting?
            state['lists'][save_name] = choices
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


def is_promode(state):
    return state['mode'] == PRO


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


number_emojis = [u'0️⃣',u'1️⃣',u'2️⃣',u'3️⃣',u'4️⃣',u'5️⃣',u'6️⃣',u'7️⃣',u'8️⃣',u'9️⃣']


def int_to_emoji_string(x):
    result = u""
    is_negative = False
    if x < 0:
        x = -x
        is_negative = True
    if x == 0:
        return u"0️⃣"
    while x > 0:
        r = x % 10
        result = number_emojis[r] + result
        x = x // 10
    if is_negative:
        return u"➖" + result
    return result


def do_number_range(state, message, info):
    suggestions = default_suggestions
    regex = "(-?[0-9]+)[-–:](-?[0-9]+)$"
    match = re.match(regex, message)
    a, b = match.groups()
    r = list(range(int(a), int(b) + 1))
    if r == []:
        return [Text_Reply_Keyboard('You gave me nothing to choose from. Do you need /help?', [["/help", "👎"]])]
    state['phase'] = 'was_go'
    choices = [Text_Reply(int_to_emoji_string(x)) for x in r]
    state['choices'] = choices
    choice = choose(choices)
    return send_choice(choice)


def do_default(state, message):
    items = extract_choices(message)
    phase = state.get('phase', 'unknown')
    if phase == 'expecting_go':
        state['choices'] += [Text_Reply(message)]
        return []
    elif phase == 'proposed_save':
        return save_list(state, message)
    elif len(items) <= 1 or state['mode'] < PRO:
        return propose_game(state, Text_Reply(message), {})
    choices = [Text_Reply(str(x)) for x in items]
    state['choices'] = choices
    state['phase'] = 'was_go'
    choice = choose(choices)
    return send_choice(choice)


def do_default_media(state, message):
    phase = state.get('phase', 'unknown')
    if phase == 'expecting_go':
        state['choices'] += [message]
        return []
    else:
        return propose_game(state, message, {})


modes_to_functions = {
    "yes": (do_yes, expecting_yes),
    "no": (do_no, expecting_no),
    "start": (do_start, None),
    "help": (do_help, None),
    "persons": (do_persons, lambda x: False),
    "query": (do_query, None),
    "easteregg_query": (do_query, None),
    "go": (do_go, expecting_go),
    "abort": (do_abort, None),
    "bow": (do_bow, expecting_bow),
    "again": (do_again, expecting_again),
    "categories": (do_category, None),
    "save": (do_save, None),
    "default_game": (do_default_game, None),
    "promode": (do_promode, None),
    "showlists": (do_show_lists, None),
    "number_range": (do_number_range, is_promode)
}


def process_message(message, state):
    # Iterate through all modes and see if they are activated by the message
    for name, info in modes.items():
        patterns = info["patterns"]
        # Set flags for regular expression matching
        ignore_case = info.get("ignore_case", True)
        flags = 0
        if ignore_case:
            flags |= re.IGNORECASE
        # Check if any patterns of the mode match the message
        for pattern in patterns:
            if re.match(pattern, message, flags):
                handler, activation = modes_to_functions[info['mode']]
                # If the pattern matches the message and the mode is activated in the current state,
                # call the mode's handler
                if activation == None or activation(state):
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


def process_sticker(sticker, state):
    message = Sticker_Reply(sticker['file_id'])
    return do_default_media(state, message)


def handle_update(update, basic_bot_url):
    global states
    send_message = "sendMessage"
    if "message" not in update or "from" not in update["message"]:
        # Not sure what to do here
        return
    chatid = str(update["message"]["from"]["id"])
    if chatid not in states:
        state = {}
        state['mode'] = STANDARD
        states[chatid] = state
    state = states[chatid]
    if "text" in update["message"]:
        text = update["message"]["text"]
        responses = process_message(text, state)
    elif "sticker" in update["message"]:
        sticker = update["message"]["sticker"]
        responses = process_sticker(sticker, state)
    else:
        responses = send_help(state)
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
