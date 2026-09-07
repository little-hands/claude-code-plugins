#!/usr/bin/env python3
"""生成した成果物の機械チェック。html / md のどちらも受ける。

    python3 assets/check.py /tmp/seq-YYYYMMDD-HHMM-slug.html
    python3 assets/check.py /tmp/seq-YYYYMMDD-HHMM-slug.md

共通で unreplaced=0 と RESULT=ok を確認し、
badges の並びを図の矢印番号と突き合わせる。
steps の fail が 0 なら失敗系が入っていない（原則 3 違反）。
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


def check_html(text):
    parser = TagBalance()
    parser.feed(text)
    badges = re.findall(r'class="badge">(.*?)</div>', text, re.S)
    # .steps コンテナを数えないよう、step の直後で区切る
    steps = re.findall(r'class="step(?:\s+[^"]*)?"', text)
    fails = [s for s in steps if "is-fail" in s]

    print("tag_errors=%d %s" % (len(parser.errors), parser.errors[:5]))
    print("unclosed=%s" % parser.stack)
    print("badges=%s" % badges)
    print("steps=%d (fail=%d)" % (len(steps), len(fails)))
    return not parser.errors and not parser.stack


def check_md(text):
    lines = text.splitlines()
    # 実値ブロックは h2 見出し「## N. 説明」。番号が矢印と対応する。
    # 末尾が ⚠️ のものを失敗系として数える（md にはクラス属性が無いため、
    # 見た目にも出る目印を構造の代わりに使う）
    heads = [l for l in lines if re.match(r"^##\s+\S+\.\s", l)]
    badges = [re.match(r"^##\s+(\S+)\.\s", l).group(1) for l in heads]
    fails = [l for l in heads if l.rstrip().endswith("⚠️")]

    # コードフェンスの閉じ忘れは md で最も壊れやすい。開始・終了の総数が偶数か見る
    fences = [l for l in lines if l.lstrip().startswith("```")]
    fence_ok = len(fences) % 2 == 0
    has_mermaid = any(l.lstrip().startswith("```mermaid") for l in lines)

    print("fences=%d (balanced=%s)" % (len(fences), fence_ok))
    print("mermaid_block=%s" % has_mermaid)
    print("badges=%s" % badges)
    print("steps=%d (fail=%d)" % (len(heads), len(fails)))
    return fence_ok and has_mermaid


def main(path):
    text = open(path, encoding="utf-8").read()
    unreplaced = re.findall(r"\{\{\w+\}\}", text)
    print("unreplaced=%d %s" % (len(unreplaced), sorted(set(unreplaced))))

    if path.lower().endswith(".md"):
        body_ok = check_md(text)
    else:
        body_ok = check_html(text)

    ok = not unreplaced and body_ok
    print("RESULT=%s" % ("ok" if ok else "NG"))
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: check.py <html|md>")
    sys.exit(main(sys.argv[1]))
