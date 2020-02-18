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

class Animation_Reply(Reply):
    send_message = "sendAnimation"
    with open("gif_ids.json") as f:
        gif_id_lookup = json.load(f)
    def __init__(self, animation_key):
        self.animation_key = animation_key
        return
    def give_payload(self):
        id = self.gif_id_lookup[self.animation_key]
        return f"&animation={id}"

class Reply_Keyboard(Reply):
    def __init__(self, keyboard):
        self.val = {'keyboard': self.resize(keyboard)}

    def give_command(self):
        return f"&reply_markup={json.dumps(self.val)}"

    def resize(self, x):
        if not len(x) > 0:
            return [[]]
        if len(x) != 2:
            l = x[0]
            nr = len(l)
            if nr % 2 is 0 and nr % 3 is not 0:
                return self.reshape(l, 2)
            else:
                return self.reshape(l, 3)
        l = x[1]
        if not l:
            return [x[0]]
        nr = len(l)
        if nr % 2 is 0 and nr % 3 is not 0:
            ret = self.reshape(l, 2)
            ret[0:0] = [x[0]]
            return ret
            # mache 2er-Chunks
        else:
            ret = self.reshape(l, 3)
            ret[0:0] = [x[0]]
            return ret
            # mache 3er-Chunks

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
