import string
import random
import json
import requests
import time
import re
import math
from itertools import chain



# /again, 2tes go
# do_category
# sticker bei confused/beim auswählen
# user kann query saven
# number ranges
# pattern über ganzen string matchen
# mehr Kategorien, größere Auswahl innerhalb
# feedback
# resize

class Reply_Keyboard_Entity:
    def __init__(self, x):
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
        if nr%3 is 0:
            ret = self.reshape(l, 3)
            ret.append(x[1])
            return ret
            #mache 3er-Chunks
        if nr%2 is 0:
            ret = self.reshape(l, 2)
            ret.append(x[1])
            return ret
            #mache 2er-Chunks
        if nr%3 is 1:
            ret = self.reshape(l, 3)
            ret[-1] += x[1]
            return ret
            #append x[1] ans letzte
        if nr%3 is 2:
            ret = self.reshape(l, 3)
            ret.append(x[1])
            return ret
            #halb fertig machen
            
    def reshape(self, l, size):
        ret = [[] for x in range(math.ceil(len(l)/size))]
        for i in range(len(l)):
            ret[math.floor(i/size)].append(l[i])
        return ret



class Reply_Keyboard_None(Reply_Keyboard_Entity):
    def __init__(self):
        self.val = None

    def give_command(self):
        remove_keyboard = {"remove_keyboard": True}
        return f"&reply_markup={json.dumps(remove_keyboard)}"


class Reply_Keyboard_Ignore(Reply_Keyboard_Entity):
    def __init__(self):
        self.val = None

    def give_command(self):
        return f""


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


three_dices = [u'🎲', u'🎲🎲', u'🎲🎲🎲', "Bow to your destiny!"]

confused = Reply_Keyboard_Entity([["👍", "👎"]]), [
    "I'm not sure what you are saying 🤔 Can you use some /help?"]
helpkeyboard = Reply_Keyboard_Entity([["/help", "👎"]])


def do_go(state, message, info):
    expecting_go = state.get('expecting_go', False)
    expecting_help = state.get('expecting_help', False)
    if expecting_go and state['choices'] != []:
        choice = choose(state['choices'])
        state['expecting_go'] = False
        return Reply_Keyboard_None(), three_dices + [choice]
    else:
        state['expecting_help'] = True
        state['expecting_go'] = False
        return confused


def do_abort(state, message, info):
    state['expecting_help'] = False
    state['expecting_go'] = False
    return Reply_Keyboard_None(), ["Ok, let's try again!"]


def do_yes(state, message, info):
    expecting_go = state.get('expecting_go', False)
    expecting_help = state.get('expecting_help', False)
    if expecting_help:
        state['expecting_help'] = True
        return helpkeyboard, ["Ok, sure! Try to press this: /help"]
    else:
        state['expecting_help'] = True
        state['expecting_go'] = False
        return confused


def do_no(state, message, info):
    expecting_go = state.get('expecting_go', False)
    expecting_help = state.get('expecting_help', False)
    if expecting_help:
        state['expecting_help'] = False
        return Reply_Keyboard_None(), ["Ok, sure!"]
    else:
        state['expecting_help'] = True
        state['expecting_go'] = False
        return confused


def do_start(state, message, info):
    welcome = """Hey there!
This is your destinator!
Can I help you find your destiny today?
If you are unsure what to do, you can try /help"""
    return Reply_Keyboard_None(), [welcome]


def do_help(state, message, info):
    state['expecting_help'] = False
    state['expecting_go'] = False
    suggestions = info['suggestions']
    welcome = info['welcome']
    return Reply_Keyboard_None(), [welcome] + suggestions


def do_query(state, message, info):
    state['expecting_go'] = True
    state['expecting_help'] = False
    state['choices'] = []
    query = info.get('query', "Ready to find your destiny?")
    choice_text = info.get('choice_text', "Give me some choices:")
    state['query'] = query
    state['choice_text'] = choice_text
    return Reply_Keyboard_Entity([list(info.get('choices', [])),['🎲', '❌']]), [choice_text]# + [query]



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
    expecting_go = state.get('expecting_go', False)
    if len(items) <= 1 and not expecting_go:
        return do_query(state, message, {})
    if expecting_go:
        state['choices'] += [message]
        return Reply_Keyboard_Ignore(), []
    choice = choose(items)
    return Reply_Keyboard_None(), three_dices + [choice]


modes_to_functions = {
    "yes": do_yes,
    "no": do_no,
    "start": do_start,
    "help": do_help,
    "persons": do_persons,
    "query": do_query,
    "go": do_go,
    "abort": do_abort
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
    if "message" not in update or "from" not in update["message"]:
        # Not sure what to do here
        return
    chatid = update["message"]["from"]["id"]
    # möglich: mehr als nur Textnachrichten handlen z.B. Kette von Sticker-Nachrichten als Eingabe
    if "text" not in update["message"]:
        keyboard, responses = confused
    else:
        text = update["message"]["text"]
        keyboard, responses = process_message(text, chatid)
    for i in range(len(responses)):
        reply_keyboard_markup = keyboard.give_command()
        response = responses[i]
        requests.get(
            f"{basic_bot_url}/{send_message}?chat_id={chatid}&text={response}{reply_keyboard_markup}")
        print(
            f"{basic_bot_url}/{send_message}?chat_id={chatid}&text={response}{reply_keyboard_markup}")
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
