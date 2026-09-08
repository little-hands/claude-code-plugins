"""diff-guide の HTML を機械で検査する。

    python3 <Base directory>/assets/check.py <出力した .html>        # 成果物モード（既定）
    python3 <Base directory>/assets/check.py --template <template>   # テンプレート自身の検査

成果物モードは「プレースホルダが残っていたら NG」、テンプレートモードは
「残っているのが正常」で、SKILL.md が名指しするクラスの実在も突き合わせる。
"""

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

VOID = {"meta", "link", "br", "img", "hr", "input", "source"}


class Checker(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []
        self.pre_with_div = 0
        self.in_pre = 0

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        if tag == "pre":
            self.in_pre += 1
        if tag == "div" and self.in_pre:
            self.pre_with_div += 1
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag == "pre":
            self.in_pre -= 1
        if not self.stack:
            self.errors.append(f"閉じタグが余っている: </{tag}>")
            return
        if self.stack[-1] != tag:
            self.errors.append(f"入れ子の不一致: <{self.stack[-1]}> の中で </{tag}>")
        else:
            self.stack.pop()


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--template"]
    is_template = "--template" in sys.argv
    if not args:
        print("usage: check.py [--template] <html>")
        return 2

    path = Path(args[0])
    html = path.read_text(encoding="utf-8")

    checker = Checker()
    checker.feed(html)

    ng = list(checker.errors)
    if checker.stack:
        ng.append(f"閉じ忘れ: {checker.stack}")
    if checker.pre_with_div:
        ng.append(f"<pre> の中に <div> が {checker.pre_with_div} 個（.lines を使う）")

    defined = set(re.findall(r"^\s*(--[a-z-]+):", html, re.M))
    used = set(re.findall(r"var\((--[a-z-]+)\)", html))
    if used - defined:
        ng.append(f"未定義の CSS 変数: {sorted(used - defined)}")

    placeholders = sorted(set(re.findall(r"\{\{[A-Z_0-9]+\}\}", html)))
    steps = len(re.findall(r'<section class="step"', html))
    lines_add = len(re.findall(r'class="line add"', html))
    lines_del = len(re.findall(r'class="line del"', html))

    if is_template:
        skill = (path.parent.parent / "SKILL.md").read_text(encoding="utf-8")
        named = set(re.findall(r"`\.([a-z][a-z-]*(?:\.[a-z-]+)?)`", skill))
        for cls in sorted(named):
            head = cls.split(".")[0]
            if head in {"md", "html", "py", "sh", "jsonl", "claude", "venv"}:
                continue
            if f".{head}" not in html:
                ng.append(f"SKILL.md が名指しするクラスがテンプレに無い: .{cls}")
        print(f"placeholders={len(placeholders)}: {' '.join(placeholders)}")
    else:
        if placeholders:
            ng.append(f"未置換のプレースホルダ: {' '.join(placeholders)}")
        if steps == 0:
            ng.append("no_steps=1（section.step が 1 つも無い — 記法がずれている）")

    print(f"steps={steps} lines(add={lines_add} del={lines_del}) css_vars={len(defined)}")

    if ng:
        print("RESULT=ng")
        for error in ng:
            print(f"  - {error}")
        return 1
    print("RESULT=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
