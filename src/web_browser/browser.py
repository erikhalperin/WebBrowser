import copy
import socket
import ssl
import tkinter
import tkinter.font
from typing import Any, Literal

from lru_dict import LRUDict
from url import URL

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100


class Browser:
    def __init__(self):
        self.display_list = []
        self.socket_dict = LRUDict()
        self.scroll = 0
        self.window = tkinter.Tk()
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.scrollwheel)
        self.font1 = tkinter.font.Font(family="Times", size=16)
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack()

    def request(self, url: URL, redirect_count: int) -> str:
        s = self.socket_dict.get((url.scheme, url.host, url.port), None)
        if s is None:
            s = socket.socket(
                family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
            )
            s.connect((url.host, url.port))
            if url.scheme == "https":
                ctx = ssl.create_default_context()
                s = ctx.wrap_socket(s, server_hostname=url.host)

        self.socket_dict[(url.scheme, url.host, url.port)] = s
        send_request(s, url.path, url.host)

        response = s.makefile("rb")
        statusline = response.readline()
        version, status, explanation = statusline.decode("utf-8").strip().split(" ", 2)
        status = int(status)
        print(version, status, explanation)

        response_headers = {}
        while True:
            line = response.readline().decode("utf-8")
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        print(response_headers)

        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        if 300 <= status < 400:
            if redirect_count >= 5:
                return "Too many redirects\n"

            if "location" not in response_headers:
                raise ValueError(
                    f"Redirect response (status {status}) missing 'location' header. "
                    f"Headers received: {response_headers}"
                )

            if response_headers.get("location").startswith("/"):
                new_url = copy.deepcopy(url)
                new_url.path = response_headers.get("location")
            else:
                new_url = URL(response_headers.get("location"))

            return self.request(new_url, redirect_count + 1)

        content_length = int(response_headers.get("content-length", 0))
        content = response.read(content_length)
        return content.decode("utf-8")

    def load(self, url: URL):
        body = self.request(url, 0)
        tokens: list[Text|Tag] = lex(body)
        self.display_list = Layout(tokens).display_list
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c, f in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c, anchor='nw', font=f)

    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()

    def scrollup(self, e):
        self.scroll -= SCROLL_STEP
        self.draw()

    def scrollwheel(self, e):
        if e.delta < 0:
            self.scroll += SCROLL_STEP
        else:
            self.scroll -= SCROLL_STEP
        self.draw()

def layout(tokens: list[Text|Tag]) -> list[tuple[int, int, str]]:
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
                if cursor_x + w > WIDTH - HSTEP:
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


def send_request(s: socket, path: str, host: str):
    req = "GET {} HTTP/1.0\r\n".format(path)
    req += "Host: {}\r\n".format(host)
    req += "Connection: keep-alive\r\n"
    req += "User-Agent: erik\r\n"
    req += "\r\n"
    s.send(req.encode("utf8"))


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


class Text:
    def __init__(self, text):
        self.text = text


class Tag:
    def __init__(self, tag):
        self.tag = tag


class Layout:
    def __init__(self, tokens: list[Text|Tag]):
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
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
        if self.cursor_x + w > WIDTH - HSTEP:
            self.cursor_y += font.metrics("linespace") * 1.25
            self.cursor_x = HSTEP
        self.display_list.append((self.cursor_x, self.cursor_y, word, font))
        self.cursor_x += w + font.measure(" ")


if __name__ == "__main__":
    b = Browser()

    #b.load(URL("https://browser.engineering/examples/xiyouji.html"))
    b.load(URL("https://browser.engineering/graphics.html"))
    tkinter.mainloop()