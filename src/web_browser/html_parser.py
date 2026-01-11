from typing import List


class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished: List[Text|Element] = []

    def parse(self) -> Text|Element:
        text = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if text: self.add_text(text)
                text = ""
            elif c == ">":
                in_tag = False
                self.add_tag(text)
                text = ""
            else:
                text += c
        if not in_tag and text:
            self.add_text(text)
        return self.finish()

    def add_text(self, text):
        if text.isspace(): return
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self, tag):
        if tag.startswith("!"): return
        if tag.startswith("/"):
            if len(self.unfinished) == 1: return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, parent)
            self.unfinished.append(node)

    def finish(self):
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()

class Text:
    def __init__(self, text: str, parent):
        self.text = text
        self.children: List[Text|Element] = []
        self.parent: Text|Element = parent

    def __repr__(self):
        return repr(self.text)


class Element:
    def __init__(self, tag: str, parent):
        self.tag = tag
        self.children: List[Text|Element] = []
        self.parent: Text|Element = parent

    def __repr__(self):
        return "<" + repr(self.tag) + ">"


def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)