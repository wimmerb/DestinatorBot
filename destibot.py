import string
import random
import json
import requests
import time
import re
import math
from itertools import chain


# do_category
# sticker bei confused/beim auswählen
# user kann query saven
# number ranges
# mehr Kategorien, größere Auswahl innerhalb
# feedback
# Immer außerhalb von Query oder help: Buttons für Go, Category, Help bereithalten

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
        if len(x) != 2:
            return x
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


three_dices = [u'🎲', u'🎲🎲', u'🎲🎲🎲']
destiny = [Reply(x) for x in three_dices] + \
    [Reply_Keyboard("Bow to your destiny!", [["🙇", "🔄"]])]

confused = Reply_Keyboard(
    "I'm not sure what you are saying 🤔 Can you use some /help?", [["👍", "👎"]])
suggest_help = Reply_Keyboard(
    "Ok, sure! Try to press this: /help", [["/help", "👎"]])


def send_choice(choice):
    return destiny + [Reply(choice)]


def send_help(state):
    state['phase'] = 'expecting_help'
    return [confused]


def do_go(state, message, info):
    phase = state.get('phase', 'unknown')
    if (phase == 'expecting_go' or phase == 'was_go') and state['choices'] != []:
        choice = choose(state['choices'])
        state['phase'] = 'was_go'
        return send_choice(choice)
    else:
        return send_help(state)


def do_abort(state, message, info):
    phase = state.get('phase', 'unknown')
    state['phase'] = 'abort'
    if phase == 'was_go':
        return [Remove_Keyboard("What's up next?")]
    return [Remove_Keyboard("Ok, let's try again!")]


def do_again(state, message, info):
    if 'choices' in state and state['choices'] != []:
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
        state['expecting_help'] = False
        return [Remove_Keyboard("Ok, sure!")]
    else:
        return send_help(state)


def do_start(state, message, info):
    state['phase'] = 'start'
    welcome = """Hey there!
This is your destinator!
Can I help you find your destiny today?
If you are unsure what to do, you can try /help"""
    return [Remove_Keyboard(welcome)]


def do_help(state, message, info):
    state['phase'] = 'help'
    suggestions = [Reply(x) for x in info['suggestions']]
    welcome = Remove_Keyboard(info['welcome'])
    return [welcome] + suggestions


def do_query(state, message, info, init_choices=[]):
    state['phase'] = 'expecting_go'
    state['choices'] = []
    query = info.get('query', "Ready to find your destiny?")
    choice_text = info.get('choice_text', "Give me some choices:")
    state['query'] = query
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
    if len(items) <= 1 and phase != 'expecting_go':
        return do_query(state, message, {}, init_choices=items)
    elif phase == 'expecting_go':
        state['choices'] += [message]
        return []
    state['choices'] = items
    state['phase'] = 'was_go'
    choice = choose(items)
    return send_choice(choice)


modes_to_functions = {
    "yes": do_yes,
    "no": do_no,
    "start": do_start,
    "help": do_help,
    "persons": do_persons,
    "query": do_query,
    "go": do_go,
    "abort": do_abort,
    "again": do_again
}


def process_message(message, chatid):
    global states
    # found "bug": wenn man einfach nur einmal ohne Kontext "jo" eingibt -> er landet bei do_yes
    if chatid not in states:
        states[chatid] = {}
    state = states[chatid]
    for name, info in modes.items():
        patterns = info["patterns"]
        # findet noch keine Verwendung
        ignore_case = info.get("ignore_case", True)
        flags = 0
        if ignore_case:
            # (mehrere) Flags setzen mit bitwise or
            flags |= re.IGNORECASE
        for pattern in patterns:
            # checke alle Patterns nach match
            if re.fullmatch(pattern, message, flags):
                # handler für gematchtes Pattern raussuchen
                handler = modes_to_functions[info['mode']]
                # state: gespeichert zu chatid, enthält 'expecting_go', 'expecting_help', 'choices'
                # message: gesendeter Text
                # info: patterns, mode, choices
                response = handler(state, message, info)
                return response
    response = do_default(state, message)
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
        print(
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
    print(update_request_url)
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
    while True:
        task()
        time.sleep(0.3)
