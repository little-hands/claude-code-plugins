#!/usr/bin/env bash
# プラグインの構造・レジストリ整合性・安全性を検証する。CI と手元の両方で同じ結果になることを重視し、
# GNU 依存（grep -P 等）と bash 4 依存（空配列展開）を避けている。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGINS_ROOT="$REPO_ROOT/plugins"
ERRORS=0

error() {
  echo "ERROR: $1" >&2
  ERRORS=$((ERRORS + 1))
}

info() {
  echo "INFO: $1"
}

# bash 3.2（macOS 標準）は set -u 下で空配列の展開が unbound variable になるため、
# 配列展開は常にこのイディオムを通す
expand() {
  local name="$1"
  eval "printf '%s\n' \"\${${name}[@]+\"\${${name}[@]}\"}\""
}

########################################
# 1. 構造検証
########################################
info "=== 構造検証 ==="

plugin_dirs=()
for d in "$PLUGINS_ROOT"/*/; do
  [ -d "$d" ] || continue
  plugin_dirs+=("$d")
done

if [ ${#plugin_dirs[@]} -eq 0 ]; then
  error "plugins/ 配下にプラグインが見つかりません"
fi

while IFS= read -r plugin_dir; do
  [ -z "$plugin_dir" ] && continue
  plugin_name="$(basename "$plugin_dir")"
  info "検証中: $plugin_name"

  plugin_json="$plugin_dir/.claude-plugin/plugin.json"
  if [ ! -f "$plugin_json" ]; then
    error "$plugin_name: .claude-plugin/plugin.json が存在しません"
    continue
  fi

  if ! jq empty "$plugin_json" 2>/dev/null; then
    error "$plugin_name: plugin.json が不正な JSON です"
    continue
  fi

  for field in name description; do
    value="$(jq -r ".$field // empty" "$plugin_json")"
    if [ -z "$value" ]; then
      error "$plugin_name: plugin.json に必須フィールド '$field' がありません"
    fi
  done

  # version は意図的に持たない。相対パスソース × git ホストのマーケットプレイスでは
  # commit SHA が自動的にバージョンになり、push がそのまま利用者へ配布される。
  # version を書くとその文字列に固定され、バンプするまで配布されなくなる。
  # 参考: https://code.claude.com/docs/en/plugins-reference#version-management
  if [ -n "$(jq -r '.version // empty' "$plugin_json")" ]; then
    error "$plugin_name: plugin.json に version があります。このリポジトリでは version を持たず commit SHA による自動更新に任せます"
  fi

  # ディレクトリ名と plugin.json の name を一致させる（marketplace.json との突合がこれを前提にしている）
  pj_name="$(jq -r '.name // empty' "$plugin_json")"
  if [ -n "$pj_name" ] && [ "$pj_name" != "$plugin_name" ]; then
    error "$plugin_name: ディレクトリ名と plugin.json の name ($pj_name) が不一致"
  fi

  # ライセンスは MIT で統一する（公開リポジトリのため）
  pj_license="$(jq -r '.license // empty' "$plugin_json")"
  if [ "$pj_license" != "MIT" ]; then
    error "$plugin_name: plugin.json の license が MIT ではありません (${pj_license:-未設定})"
  fi

  skills_dir="$plugin_dir/skills"
  if [ ! -d "$skills_dir" ]; then
    error "$plugin_name: skills/ ディレクトリが存在しません"
  elif [ "$(find "$skills_dir" -name "SKILL.md" | wc -l | tr -d ' ')" -eq 0 ]; then
    error "$plugin_name: skills/ 配下に SKILL.md が見つかりません"
  fi

  if [ ! -f "$plugin_dir/README.md" ]; then
    error "$plugin_name: README.md が存在しません"
  fi
done < <(expand plugin_dirs)

########################################
# 2. レジストリ整合性
########################################
info ""
info "=== レジストリ整合性 ==="

marketplace="$REPO_ROOT/.claude-plugin/marketplace.json"

if ! jq empty "$marketplace" 2>/dev/null; then
  error "marketplace.json が不正な JSON です"
else
  while IFS= read -r plugin_dir; do
    [ -z "$plugin_dir" ] && continue
    plugin_name="$(basename "$plugin_dir")"

    entry="$(jq -r --arg name "$plugin_name" '.plugins[] | select(.name == $name) | .name' "$marketplace")"
    if [ -z "$entry" ]; then
      error "$plugin_name: marketplace.json に登録されていません"
      continue
    fi

    mp_version="$(jq -r --arg name "$plugin_name" '.plugins[] | select(.name == $name) | .version // empty' "$marketplace")"
    if [ -n "$mp_version" ]; then
      error "$plugin_name: marketplace.json に version があります。commit SHA による自動更新に任せるため削除してください"
    fi

    mp_source="$(jq -r --arg name "$plugin_name" '.plugins[] | select(.name == $name) | .source' "$marketplace")"
    if [ "$mp_source" != "./plugins/$plugin_name" ]; then
      error "$plugin_name: marketplace.json の source ($mp_source) が ./plugins/$plugin_name ではありません"
    fi
  done < <(expand plugin_dirs)

  # marketplace.json に登録されたプラグインが plugins/ 配下に存在するか
  while IFS= read -r name; do
    [ -z "$name" ] && continue
    if [ ! -d "$PLUGINS_ROOT/$name" ]; then
      error "marketplace.json に登録された '$name' が plugins/ に存在しません"
    fi
  done < <(jq -r '.plugins[].name' "$marketplace")
fi

# ルート README.md にプラグインが記載されているか
info "README.md のプラグイン一覧を確認中..."
root_readme="$REPO_ROOT/README.md"
if [ -f "$root_readme" ]; then
  while IFS= read -r plugin_dir; do
    [ -z "$plugin_dir" ] && continue
    plugin_name="$(basename "$plugin_dir")"
    if ! grep -q "$plugin_name" "$root_readme"; then
      error "$plugin_name: ルート README.md に記載されていません"
    fi
  done < <(expand plugin_dirs)
else
  error "ルート README.md が存在しません"
fi

########################################
# 3. プロンプトインジェクション検出
########################################
info ""
info "=== プロンプトインジェクション検出 ==="

injection_targets=()
while IFS= read -r f; do
  [ -z "$f" ] && continue
  injection_targets+=("$f")
done < <(find "$PLUGINS_ROOT" \( -name "SKILL.md" -o \( -path "*/references/*" -name "*.md" \) \) 2>/dev/null)

# grep の終了コードは 0=一致あり / 1=一致なし / 2以上=実行エラー。
# 2以上を握り潰すと「チェックしたつもりで実は動いていない」状態になるため、明示的にエラーとして扱う
scan() {
  local label="$1" pattern="$2" target="$3"
  shift 3
  local rel_path="${target#"$REPO_ROOT"/}"
  local output status
  output="$(grep -n -E ${1+"$@"} -e "$pattern" "$target" 2>&1)" && status=0 || status=$?

  if [ "$status" -ge 2 ]; then
    error "検査の実行に失敗しました [$label]: $rel_path: $output"
    return
  fi
  [ "$status" -eq 1 ] && return

  while IFS= read -r match; do
    [ -z "$match" ] && continue
    error "プロンプトインジェクション検出 [$label]: $rel_path: $match"
  done <<< "$output"
}

check_pattern() {
  local label="$1" pattern="$2"
  while IFS= read -r target; do
    [ -z "$target" ] && continue
    scan "$label" "$pattern" "$target" -i
  done < <(expand injection_targets)
}

# 3-1. システムプロンプト上書き系
check_pattern "システムプロンプト上書き" \
  "(ignore (previous|all previous) instructions|disregard previous|forget everything|you are now|act as if|pretend you are|your new instructions are|override previous|system prompt)"

# 3-2. 権限エスカレーション系
check_pattern "権限エスカレーション" \
  "(bypass security|disable safety|remove restrictions|unlock capabilities)"

# 3-3. データ窃取系
check_pattern "データ窃取" \
  "(exfiltrate|upload to https?://)"

check_pattern "データ窃取/外部送信" \
  '(curl|wget|fetch|http\.post).*https?://[^/]*(\.ru|\.cn|\.tk|\.xyz|pastebin|ngrok|requestbin|webhook\.site)'

check_pattern "環境変数窃取" \
  '(\$ENV|\$\{?[A-Z_]+\}?).*(curl|fetch|http|wget|send|post)'

# 3-4. 隠蔽系
check_pattern "隠蔽" \
  "(do not mention|hide this|keep secret|don't tell the user|dont tell the user)"

# 不可視文字・RTL override。grep -P は BSD grep（macOS 標準）にないため、
# 対象コードポイントの UTF-8 バイト列を直接パターンに埋めて POSIX grep で照合する
# ZWSP U+200B / ZWNJ U+200C / ZWJ U+200D / WJ U+2060 / BOM U+FEFF
INVISIBLE_PATTERN=$'\xe2\x80\x8b|\xe2\x80\x8c|\xe2\x80\x8d|\xe2\x81\xa0|\xef\xbb\xbf'
# LRE U+202A / RLE U+202B / PDF U+202C / LRO U+202D / RLO U+202E
# LRI U+2066 / RLI U+2067 / FSI U+2068 / PDI U+2069
RTL_PATTERN=$'\xe2\x80\xaa|\xe2\x80\xab|\xe2\x80\xac|\xe2\x80\xad|\xe2\x80\xae|\xe2\x81\xa6|\xe2\x81\xa7|\xe2\x81\xa8|\xe2\x81\xa9'

while IFS= read -r target; do
  [ -z "$target" ] && continue
  # バイト列として照合するためロケールを C に固定する
  LC_ALL=C scan "不可視文字" "$INVISIBLE_PATTERN" "$target"
  LC_ALL=C scan "RTL override" "$RTL_PATTERN" "$target"
done < <(expand injection_targets)

# 3-5. 悪意のあるコード実行系
check_pattern "悪意のあるコード実行" \
  '(eval\(|exec\(|rm -rf /[^a-z]|base64 -d.*\|.*sh|base64 --decode.*\|.*bash)'

########################################
# 4. セキュリティチェック
########################################
info ""
info "=== セキュリティチェック ==="

while IFS= read -r f; do
  [ -z "$f" ] && continue
  error "機密ファイルが含まれています: ${f#"$REPO_ROOT"/}"
done < <(find "$PLUGINS_ROOT" -type f \( -name "*.pem" -o -name "*.key" -o -name "*.crt" -o -name ".env" -o -name "*.env" \) 2>/dev/null)

while IFS= read -r target; do
  [ -z "$target" ] && continue
  scan "秘密情報の可能性" \
    '(api[_-]?key|api[_-]?secret|access[_-]?token|secret[_-]?key|private[_-]?key|password)[[:space:]]*[:=][[:space:]]*["'"'"'][A-Za-z0-9+/=_-]{16,}' \
    "$target"
done < <(find "$PLUGINS_ROOT" -type f \( -name "*.md" -o -name "*.json" \) 2>/dev/null)

########################################
# 結果
########################################
echo ""
if [ "$ERRORS" -gt 0 ]; then
  echo "FAILED: $ERRORS 件のエラーが検出されました"
  exit 1
else
  echo "PASSED: 全ての検証に合格しました"
  exit 0
fi
