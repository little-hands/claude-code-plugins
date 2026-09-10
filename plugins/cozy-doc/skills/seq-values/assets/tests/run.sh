#!/usr/bin/env bash
# check.py 自身のテスト。期待する判定を固定する。
#
#   bash plugins/cozy-doc/skills/seq-values/assets/tests/run.sh
#
# 正しい入力だけを与えても、チェックの見落としは見つからない。
# ここに置くのは「通ってはいけない入力」が中心。
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
check="$here/../check.py"

pass=0
fail=0

# 期待する src_missing と RESULT を突き合わせる
expect() {
  local file="$1" want_missing="$2" want_result="$3" note="$4"
  local out missing result
  out="$(python3 "$check" "$here/$file" 2>&1)"
  missing="$(printf '%s\n' "$out" | sed -n 's/^src_missing=//p')"
  result="$(printf '%s\n' "$out" | sed -n 's/^RESULT=//p')"
  if [[ "$missing" == "$want_missing" && "$result" == "$want_result" ]]; then
    pass=$((pass + 1))
    printf 'ok   %-22s src_missing=%s RESULT=%s  # %s\n' "$file" "$missing" "$result" "$note"
  else
    fail=$((fail + 1))
    printf 'FAIL %-22s src_missing=%s RESULT=%s（期待 %s / %s）  # %s\n' \
      "$file" "$missing" "$result" "$want_missing" "$want_result" "$note"
  fi
}

expect ok.md            0 ok "出どころあり"
expect no-src-fence.md  2 NG "見出しの直後がコードフェンス。バッククォート始まりでも出どころではない"
expect no-src-empty.html 1 NG "空の <p class=\"src\"></p> は未記載として数える"

printf 'pass=%d fail=%d\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]]
