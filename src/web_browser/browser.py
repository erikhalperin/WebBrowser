import copy
import socket
import ssl
import tkinter
import tkinter.font
from lru_dict import LRUDict
from url import URL
from web_browser.html_parser import HTMLParser, print_tree
from web_browser.layout import Text, Layout, Element, VSTEP

WIDTH, HEIGHT = 800, 600
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
        parser = HTMLParser(body)
        print_tree(parser.parse())
        # tokens: list[Text | Element] = parser.parse() # here
        # self.display_list = Layout(tokens, WIDTH).display_list
        # self.draw()

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


def send_request(s: socket, path: str, host: str):
    req = "GET {} HTTP/1.0\r\n".format(path)
    req += "Host: {}\r\n".format(host)
    req += "Connection: keep-alive\r\n"
    req += "User-Agent: erik\r\n"
    req += "\r\n"
    s.send(req.encode("utf8"))


if __name__ == "__main__":
    b = Browser()

    # b.load(URL("https://browser.engineering/examples/xiyouji.html"))
    b.load(URL("https://browser.engineering/html.html"))
    # b.load(URL("https://browser.engineering/examples/example3-sizes.html"))
    #tkinter.mainloop()
