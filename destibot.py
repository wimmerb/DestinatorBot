import string, random, json, requests, time

eastereggs = {'residenz': ('Nils', 'Niklas', 'Marius'), 'collector' : ('Maxi', 'Jakob', 'Matthias', 'Jonas'), 'hw25' : ('Simon', 'Fabi', 'Flo', 'Bene')}

isFirstIteration = True
latestDealtUpdate = 0

diceText = u'🎲'

def extract_choices (msg):
    #... anderer Vorschlag: nur nach Kommas trennen lassen
    #sicherstellen dass wir nen String haben
    #Problem: zerstoert Kontrollsequenz für Emojis
    list = None
    if ',' in msg:
        list = msg.split(',')
    else:
        list = [a for a in msg.split(' ') if a != '']
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
    req = requests.get("https://api.telegram.org/bot986451403:AAHwcdSHWFNj1xaVvLjboFf2n8l0Wei5Qlo/getUpdates")
    res = req.json()["result"]
    res = res[len(res)-1]
    currentUpdate = res["update_id"]
    global isFirstIteration
    global latestDealtUpdate
    if currentUpdate > latestDealtUpdate:
        chatid, text = res["message"]["from"]["id"], res["message"]["text"]
        choicetext = choose(extract_choices(text))
        print(choicetext)
        requests.get("https://api.telegram.org/bot986451403:AAHwcdSHWFNj1xaVvLjboFf2n8l0Wei5Qlo/sendMessage?chat_id="+str(chatid)+"&text=" + diceText)
        time.sleep(0.3)
        requests.get("https://api.telegram.org/bot986451403:AAHwcdSHWFNj1xaVvLjboFf2n8l0Wei5Qlo/sendMessage?chat_id="+str(chatid)+"&text=" + diceText+diceText)
        time.sleep(0.3)
        requests.get("https://api.telegram.org/bot986451403:AAHwcdSHWFNj1xaVvLjboFf2n8l0Wei5Qlo/sendMessage?chat_id="+str(chatid)+"&text=" + diceText+diceText+diceText)
        time.sleep(0.3)
        requests.get("https://api.telegram.org/bot986451403:AAHwcdSHWFNj1xaVvLjboFf2n8l0Wei5Qlo/sendMessage?chat_id="+str(chatid)+"&text=" + choicetext)
        print("https://api.telegram.org/bot986451403:AAHwcdSHWFNj1xaVvLjboFf2n8l0Wei5Qlo/sendMessage?chat_id="+str(chatid)+"&text=" + choicetext)
        isFirstIteration = False
        latestDealtUpdate = currentUpdate
    return

if __name__ == "__main__":
    while(True):
        task()
        time.sleep(0.3)



