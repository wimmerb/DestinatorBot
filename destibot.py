import string, random, json, requests, time

#In Datei auslagern
#Eastereggs mit Gewichten?
#2 Bearbtungsmodi: Persons und Query
eastereggs = {'residenz': ('Nils', 'Niklas', 'Marius'), 'collector' : ('Maxi', 'Jakob', 'Matthias', 'Jonas'), 'hw25' : ('Simon', 'Fabi', 'Flo', 'Bene')}

isFirstIteration = True
latestDealtUpdate = 0



def extract_choices (msg):
    #... anderer Vorschlag: nur nach Kommas trennen lassen
    #sicherstellen dass wir nen String haben
    #Problem: zerstoert Kontrollsequenz für Emojis
    list = None
    if ',' in msg:
        list = msg.split(',')
    else:
        list = [a for a in msg.split() if a != '']
    list = replace_eastereggs(list)
    return list

def replace_eastereggs (list):
    for key in eastereggs.keys():
        while key in list:
            pos = list.index(key)
            list[pos:pos+1] = eastereggs[key]
    return list

def choose (choice_list):
    return random.choice(choice_list)

def fetchLatestUpdate ():
    return


def task ():
    dice_text = u'🎲'
    telegram_api_url = "https://api.telegram.org"
    with open('config.json') as f:
        config = json.load(f)
    bot_token = config["bot_token"]
    get_updates = "getUpdates"
    send_message = "sendMessage"
    basic_bot_url = f"{telegram_api_url}/{bot_token}"
    req = requests.get(f"{basic_bot_url}/{get_updates}")
    res = req.json()["result"]
    res = res[len(res)-1]
    currentUpdate = res["update_id"]
    global isFirstIteration
    global latestDealtUpdate
    if currentUpdate > latestDealtUpdate:
        chatid, text = res["message"]["from"]["id"], res["message"]["text"]
        #failt bei leerer Liste
        choicetext = choose(extract_choices(text))
        print(choicetext)
        #fstring refactor
        requests.get(f"{basic_bot_url}/{send_message}?chat_id="+str(chatid)+"&text=" + dice_text)
        time.sleep(0.3)
        requests.get(f"{basic_bot_url}/{send_message}?chat_id="+str(chatid)+"&text=" + dice_text+dice_text)
        time.sleep(0.3)
        requests.get(f"{basic_bot_url}/{send_message}?chat_id="+str(chatid)+"&text=" + dice_text+dice_text+dice_text)
        time.sleep(0.3)
        requests.get(f"{basic_bot_url}/{send_message}?chat_id="+str(chatid)+"&text=" + choicetext)
        print(f"{basic_bot_url}/{send_message}?chat_id="+str(chatid)+"&text=" + choicetext)
        isFirstIteration = False
        latestDealtUpdate = currentUpdate
    return

if __name__ == "__main__":
    while(True):
        task()
        time.sleep(0.3)



