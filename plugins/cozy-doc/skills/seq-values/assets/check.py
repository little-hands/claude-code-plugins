#!/usr/bin/env python3
"""生成した成果物の機械チェック。html / md のどちらも受ける。

    python3 assets/check.py /tmp/seq-YYYYMMDD-HHMM-slug.html
    python3 assets/check.py /tmp/seq-YYYYMMDD-HHMM-slug.md

共通で unreplaced=0 と RESULT=ok を確認し、
badges の並びを図の矢印番号と突き合わせる。
steps の fail が 0 なら失敗系が入っていない（原則 3 違反）。
src_missing が 0 でなければ、出どころ（ファイル・関数）を書いていない
実値ブロックがある。
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

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


BADGE = re.compile(r'class="badge">(.*?)</div>', re.S)
# 直後が < だと中身ではなく閉じタグなので、文字が来ることを要求する
SRC_FILLED = re.compile(r'class="src"[^>]*>\s*[^<\s]')


def check_html(text):
    parser = TagBalance()
    parser.feed(text)

    badges = BADGE.findall(text)
    # .steps コンテナを数えないよう、step の直後で区切る
    steps = re.findall(r'class="step(?:\s+[^"]*)?"', text)
    fails = [s for s in steps if "is-fail" in s]

    # 出どころ（p.src）は全 .step に要る。欠けている矢印番号まで出す
    # （件数だけだと、直す側がもう一度探すことになる）
    blocks = re.split(r'<[a-zA-Z][\w-]*\s+class="step(?:\s+[^"]*)?"', text)[1:]
    missing = [
        (BADGE.search(b).group(1).strip() if BADGE.search(b) else "?")
        for b in blocks
        if not SRC_FILLED.search(b)
    ]

    print("tag_errors=%d %s" % (len(parser.errors), parser.errors[:5]))
    print("unclosed=%s" % parser.stack)
    print("badges=%s" % badges)
    print("steps=%d (fail=%d)" % (len(steps), len(fails)))
    print("src_missing=%d %s" % (len(missing), missing))

    return (not parser.errors and not parser.stack and not missing), len(steps)


def check_md(text):
    lines = text.splitlines()
    # 実値ブロックは h2 見出し「## N. 説明」。番号が矢印と対応する。
    # ドットの後のスペースは必須にしない（「## 1.説明」で無言の 0 件になるのを避ける）
    HEAD = re.compile(r"^##\s+(\d[0-9a-z]*)\.")
    heads = [l for l in lines if HEAD.match(l)]
    badges = [HEAD.match(l).group(1) for l in heads]
    # 失敗系は見出しの ⚠️ で数える（md にはクラス属性が無いため、
    # 見た目にも出る目印を構造の代わりに使う）。
    # U+FE0F（異体字セレクタ）の有無で取りこぼさないよう U+26A0 だけを見る
    fails = [l for l in heads if "⚠" in l]

    # コードフェンスの閉じ忘れは md で最も壊れやすい。開始・終了の総数が偶数か見る
    fences = [l for l in lines if l.lstrip().startswith("```")]
    fence_ok = len(fences) % 2 == 0
    has_mermaid = any(l.lstrip().startswith("```mermaid") for l in lines)

    # 出どころは見出しの次の非空行。md にはクラス属性が無いので、
    # インラインコードで始まるかどうかを目印にする。
    # コードフェンス（```）も ` で始まるため、先に弾く
    # （弾かないと「見出しの直後が実値のフェンス」を出どころと誤認する）
    missing = []
    for i, line in enumerate(lines):
        m = HEAD.match(line)
        if not m:
            continue
        following = (l.strip() for l in lines[i + 1:])
        first = next((l for l in following if l), "")
        if first.startswith("```") or not first.startswith("`"):
            missing.append(m.group(1))

    print("fences=%d (balanced=%s)" % (len(fences), fence_ok))
    print("mermaid_block=%s" % has_mermaid)
    print("badges=%s" % badges)
    print("steps=%d (fail=%d)" % (len(heads), len(fails)))
    print("src_missing=%d %s" % (len(missing), missing))
    return (fence_ok and has_mermaid and not missing), len(heads)


def main(path):
    text = open(path, encoding="utf-8").read()

    # 「未置換」はこのスキル自身の template.html にあるプレースホルダーだけを指す。
    # 生成物が扱うドメインの値（`{{source_text}}`・`{{style_guide}}` のような、
    # 対象システムの実プロンプトのスロット名）は `{{...}}` の見た目をしているが
    # 別物 — 全部を拾う素朴な正規表現だと、これらを本文に書いた時点で誤検知する
    # （このスキル自身の実例で 2026-09-10 に踏んだ）。
    # template.html 側のプレースホルダーは全大文字スネークケースで統一されている
    # ので、そこから拾った名前だけを対象にする。
    # template.html が読めない・壊れている環境でもこのチェック自体は落とさない
    # （この判定だけ効かなくなる。プレースホルダー名の集合が分からない以上、
    # それ以外の代替は無い）。存在しない・権限が無い（OSError）だけでなく、
    # エンコーディングが壊れている（UnicodeDecodeError は ValueError 系統で
    # OSError には含まれない）場合も同じ扱いにする
    template_path = Path(__file__).parent / "template.html"
    try:
        known_names = set(re.findall(r"\{\{(\w+)\}\}", template_path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError):
        known_names = set()
    unreplaced = [m for m in re.findall(r"\{\{\w+\}\}", text) if m[2:-2] in known_names]
    print("unreplaced=%d %s" % (len(unreplaced), sorted(set(unreplaced))))

    if path.lower().endswith(".md"):
        body_ok, steps = check_md(text)
    else:
        body_ok, steps = check_html(text)

    # 実値ブロックが 1 つも無い成果物はこのスキルの出力として成立しない。
    # 記法の揺れで拾えていないだけの場合もここで気づける
    if steps == 0:
        print("no_steps=1  # 実値ブロックが 0 件。記法（html: .step / md: '## N.'）を確認する")

    ok = not unreplaced and body_ok and steps > 0
    print("RESULT=%s" % ("ok" if ok else "NG"))
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: check.py <html|md>")
    sys.exit(main(sys.argv[1]))
