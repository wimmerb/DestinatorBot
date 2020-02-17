import json
import math
import random


class Reply:

    send_message = None

    def give_command(self):
        return ""

    def get_http_reply(self, basic_bot_url, chatid):
        command = self.give_command()
        payload = self.give_payload()
        return f"{basic_bot_url}/{self.send_message}?chat_id={chatid}{payload}{command}"


class Text_Reply(Reply):

    send_message = "sendMessage"

    def __init__(self, text):
        self.text = text

    def give_payload(self):
        return f"&text={self.text}"


class Sticker_Reply(Reply):

    send_message = "sendSticker"

    def __init__(self, sticker_id):
        self.sticker_id = sticker_id

    def give_payload(self):
        return f"&sticker={self.sticker_id}"


class Random_Sticker_Reply(Sticker_Reply):

    with open("stickers.json") as f:
        sticker_db = json.load(f)

    def __init__(self, emoji):
        self.emoji = emoji

    def give_payload(self):
        stickers = [
            sticker for sticker in self.sticker_db if sticker['emoji'] == self.emoji]
        self.sticker = random.choice(stickers)
        self.sticker_id = self.sticker['file_id']
        return super().give_payload()


class Reply_Keyboard(Reply):
    def __init__(self, keyboard):
        self.val = {'keyboard': self.resize(keyboard)}

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


class Remove_Keyboard(Reply):

    def give_command(self):
        remove_keyboard = {"remove_keyboard": True}
        return f"&reply_markup={json.dumps(remove_keyboard)}"


class Text_Reply_Keyboard(Text_Reply, Reply_Keyboard):
    def __init__(self, text, keyboard):
        self.text = text
        self.val = {'keyboard': self.resize(keyboard)}


class Text_Remove_Keyboard(Text_Reply, Remove_Keyboard):
    pass


class Random_Sticker_Reply_Keyboard(Random_Sticker_Reply, Reply_Keyboard):
    def __init__(self, emoji, keyboard):
        Random_Sticker_Reply.__init__(self, emoji)
        Reply_Keyboard.__init__(self, keyboard)