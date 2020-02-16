import string
import random
import json
import requests
import time
import re
import math
import logging
import sys
from functools import reduce
from itertools import chain
from urllib3.exceptions import HTTPError


# sticker bei confused/beim auswählen
# user kann query saven
# number ranges
# mehr Kategorien, größere Auswahl innerhalb
# feedback
# Immer außerhalb von Query oder help: Buttons für Go, Category, Help bereithalten
# persönliche Eingaben speichern

class Reply:
    def __init__(self, text):
        self.text = text

    def give_command(self):
        return ""


class Reply_Keyboard(Reply):
    def __init__(self, text, x):
        self.text = text
        self.val = {'keyboard': self.resize(x)}

    def give_command(self):
        return f"&reply_markup={json.dumps(self.val)}"

    def resize(self, x):
        if len(x) != 2 and len(x) > 0:
            return self.reshape(x[0], 3)
        l = x[0]
        if not l:
            return [x[1]]
        nr = len(l)
        if nr % 3 is 0:
            ret = self.reshape(l, 3)
            ret.append(x[1])
            return ret
            # mache 3er-Chunks
        if nr % 2 is 0:
            ret = self.reshape(l, 2)
            ret.append(x[1])
            return ret
            # mache 2er-Chunks
        if nr % 3 is 1:
            ret = self.reshape(l, 3)
            ret[-1] += x[1]
            return ret
            # append x[1] ans letzte
        if nr % 3 is 2:
            ret = self.reshape(l, 3)
            ret.append(x[1])
            return ret
            # halb fertig machen

    def reshape(self, l, size):
        ret = [[] for x in range(math.ceil(len(l)/size))]
        for i in range(len(l)):
            ret[math.floor(i/size)].append(l[i])
        return ret


class Remove_Keyboard(Reply_Keyboard):
    def __init__(self, text):
        self.text = text

    def give_command(self):
        remove_keyboard = {"remove_keyboard": True}
        return f"&reply_markup={json.dumps(remove_keyboard)}"


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


three_dices = ["hmm...."]  # u'🤔🤔🤔']
destiny = [Reply(x) for x in three_dices] + \
    [Reply_Keyboard("Bow to your destiny!", [["🙇", "🔄"]])]

confused = Reply_Keyboard(
    "I'm not sure what you are saying 🤔 Can you use some /help?", [["👍", "👎"]])
suggest_help = Reply_Keyboard(
    "Ok, sure! Try to press this: /help", [["/help", "👎"]])
default_suggestions = [[u'/default_game', u'/categories', u'/help']]


def send_choice(choice):
    return destiny + [Reply(choice)]


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
        return do_query(state, message, info)


def do_abort(state, message, info):
    phase = state.get('phase', 'unknown')
    state['phase'] = 'default'
    if phase == 'was_go':
        return [Reply_Keyboard("What's up next?", default_suggestions)]
    return [Reply_Keyboard("Ok, let's try again!", default_suggestions)]


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
    else:
        return send_help(state)


def do_no(state, message, info):
    phase = state.get('phase', 'unknown')
    state['phase'] = 'no'
    if phase == 'expecting_help':
        state['phase'] = 'default'
        return [Reply_Keyboard("Ok, sure!", default_suggestions)]
    else:
        return send_help(state)


def do_start(state, message, info):
    state['phase'] = 'default'
    welcome = info['welcome']
    return [Reply_Keyboard(welcome, default_suggestions)]


def do_help(state, message, info):
    state['phase'] = 'default'
    suggestion_text = '\n'.join(info['suggestions'])
    suggestions = [Reply(suggestion_text)]
    welcome = Reply_Keyboard(info['welcome'], [info['suggestions']])
    return [welcome] + suggestions


def do_query(state, message, info, init_choices=[]):
    state['choices'] = []

    choice_text = f"{'Game started: s' if init_choices==[] else 'S'}end me some messages with choices (text or buttons):"
    state['phase'] = 'expecting_go'
    state['choice_text'] = choice_text
    keyboard = Reply_Keyboard(
        choice_text, [list(info.get('choices', [])), ['🎲', '❌']])
    initial_choices = list(map(Reply, init_choices))
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


def do_default(state, message):
    items = extract_choices(message)
    phase = state.get('phase', 'unknown')
    if phase == 'expecting_go':
        state['choices'] += [message]
        return []
    elif phase == 'proposed_save':
        return save_list(state, message)
    elif len(items) <= 1:
        return do_query(state, message, {}, init_choices=items)
    state['choices'] = items
    state['phase'] = 'was_go'
    choice = choose(items)
    return send_choice(choice)


def do_category(state, message, info):
    categories = []
    for name, info in modes.items():
        if info.get('mode', '') == 'query':
            categories.append(name)
    return [Reply_Keyboard(
        "Here's a list of possible categories to choose from...", [categories])]


def propose_save(state):
    state['phase'] = "proposed_save"
    msg = "Saving current list... Propose a name:"
    suggestions = [[u'❌', u'/help']]
    return [Reply_Keyboard(msg, suggestions)]


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
    return [Reply_Keyboard(msg, suggestions)]


def do_save(state, message, info):
    match = re.match("/save (.*)", message)
    if match == None:
        # no name for list given, so ask for one
        return propose_save(state)
    else:
        arg = match.groups()[0]
        return save_list(state, arg)


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
    "save": do_save
}


def process_message(message, chatid):
    global states
    # found "bug": wenn man einfach nur einmal ohne Kontext "jo" eingibt -> er landet bei do_yes
    if chatid not in states:
        states[chatid] = {}
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


def handle_update(update, basic_bot_url):
    send_message = "sendMessage"
    if "message" not in update or "from" not in update["message"] or "text" not in update["message"]:
        # Not sure what to do here
        return
    chatid = update["message"]["from"]["id"]
    # möglich: mehr als nur Textnachrichten handlen z.B. Kette von Sticker-Nachrichten als Eingabe
    if "text" not in update["message"]:
        responses = confused
    else:
        text = update["message"]["text"]
        responses = process_message(text, chatid)
        time.sleep(0.3)
    for i, response in enumerate(responses):
        reply_keyboard_markup = response.give_command()
        requests.get(
            f"{basic_bot_url}/{send_message}?chat_id={chatid}&text={response.text}{reply_keyboard_markup}")
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
            latest_update_served = update_id
            handle_update(update, basic_bot_url)


if __name__ == "__main__":
    logging.basicConfig(filename='destibot.log', level=logging.INFO)
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
