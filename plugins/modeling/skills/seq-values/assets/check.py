#!/usr/bin/env python3
"""生成した HTML の機械チェック。

    python3 assets/check.py /tmp/seq-YYYYMMDD-HHMM-slug.html

unreplaced=0 / tag_errors=0 / unclosed=[] を確認し、
badges の並びを図の矢印番号と突き合わせる。
"""
import re
import sys
from html.parser import HTMLParser

VOID = {"meta", "link", "br", "hr", "img", "input", "source"}


class TagBalance(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append("</%s> L%d" % (tag, self.getpos()[0]))
        else:
            self.stack.pop()


def main(path):
    html = open(path, encoding="utf-8").read()
    unreplaced = re.findall(r"\{\{\w+\}\}", html)
    parser = TagBalance()
    parser.feed(html)
    badges = re.findall(r'class="badge">(.*?)</div>', html, re.S)

    print("unreplaced=%d %s" % (len(unreplaced), sorted(set(unreplaced))))
    print("tag_errors=%d %s" % (len(parser.errors), parser.errors[:5]))
    print("unclosed=%s" % parser.stack)
    print("badges=%s" % badges)
    # .steps コンテナを数えないよう、step の直後で区切る
    steps = re.findall(r'class="step(?:\s+[^"]*)?"', html)
    fails = [s for s in steps if "is-fail" in s]
    print("steps=%d (fail=%d)" % (len(steps), len(fails)))

    ok = not unreplaced and not parser.errors and not parser.stack
    print("RESULT=%s" % ("ok" if ok else "NG"))
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: check.py <html>")
    sys.exit(main(sys.argv[1]))
