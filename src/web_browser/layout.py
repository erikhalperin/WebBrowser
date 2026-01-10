import tkinter


HSTEP, VSTEP = 13, 18


class Text:
    def __init__(self, text):
        self.text = text


class Tag:
    def __init__(self, tag):
        self.tag = tag


class Layout:
    def __init__(self, tokens: list[Text|Tag], width: int):
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
        self.browser_width = width
        for tok in tokens:
            self.token(tok)

    def token(self, tok):
        if isinstance(tok, Text):
            for w in tok.text.split():
                self.word(w)

        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4

    def word(self, word: str):
        font = tkinter.font.Font(
            size=self.size,
            weight=self.weight,
            slant=self.style,
        )
        w = font.measure(word)
        if self.cursor_x + w > self.browser_width - HSTEP:
            self.cursor_y += font.metrics("linespace") * 1.25
            self.cursor_x = HSTEP
        self.display_list.append((self.cursor_x, self.cursor_y, word, font))
        self.cursor_x += w + font.measure(" ")


def lex(body: str) -> list[Text|Tag]:
    out = []
    buffer = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
            if buffer: out.append(Text(buffer))
            buffer = ""
        elif c == ">":
            in_tag = False
            out.append(Tag(buffer))
            buffer = ""
        else:
            buffer += c
    if not in_tag and buffer:
        out.append(Text(buffer))
    return out


def layout(tokens: list[Text|Tag], browser_width: int) -> list[tuple[int, int, str]]:
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    weight = "normal"
    style = "roman"

    for tok in tokens:
        if isinstance(tok, Text):
            for word in tok.text.split():
                font = tkinter.font.Font(
                    size=16,
                    weight=weight,
                    slant=style,
                )
                w = font.measure(word)
                if cursor_x + w > browser_width - HSTEP:
                    cursor_y += font.metrics("linespace") * 1.25
                    cursor_x = HSTEP
                display_list.append((cursor_x, cursor_y, word, font))
                cursor_x += w + font.measure(" ")
        elif tok.tag == "i":
            style = "italic"
        elif tok.tag == "/i":
            style = "roman"
        elif tok.tag == "b":
            weight = "bold"
        elif tok.tag == "/b":
            weight = "normal"

    return display_list