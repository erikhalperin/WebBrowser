import copy
import socket
import ssl
import sys
import tkinter

from lru_dict import LRUDict
from url import URL

WIDTH, HEIGHT = 800, 600


class Browser:
    def __init__(self):
        self.socket_dict = LRUDict()

        self.window = tkinter.Tk()
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
        self.canvas.create_rectangle(10, 20, 400, 300)
        self.canvas.create_oval(100, 100, 150, 150)
        self.canvas.create_text(200, 150, text="Hi!")
        text = lex(body)
        for c in text:
            self.canvas.create_text(100, 100, text=c)


def send_request(s: socket, path: str, host: str):
    req = "GET {} HTTP/1.0\r\n".format(path)
    req += "Host: {}\r\n".format(host)
    req += "Connection: keep-alive\r\n"
    req += "User-Agent: erik\r\n"
    req += "\r\n"
    s.send(req.encode("utf8"))


def lex(body: str) -> str:
    in_tag = False
    text = ""
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            text += c
    return text


if __name__ == "__main__":
    b = Browser()

    b.load(URL("https://browser.engineering/http.html"))
    tkinter.mainloop()