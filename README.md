# claude-code-plugins

little-hands が作る Claude Code プラグイン集。

## プラグイン一覧

| プラグイン | 説明 |
|------------|------|
| [article-assistant](./plugins/article-assistant/) | 記事執筆を伴走サポートする編集者。アイデアの深掘り→切り口ブレスト→狙いの整理→構成→セクション生成まで対話でガイド |
| [modeling](./plugins/modeling/) | システムの振る舞いを解釈の余地なく説明するためのモデリング補助。`seq-values` スキルで「シーケンス図（mermaid）＋矢印ごとの実値」のスタンドアロン HTML を生成 |

## インストール

ターミナルで `claude` を起動し、以下のコマンドでマーケットプレイスを追加してください。

```
/plugin marketplace add little-hands/claude-code-plugins
```

次に、使いたいプラグインをインストールしてください。マーケットプレイスを追加しただけでは何も入りません。**必要なプラグインだけを1つずつ選んで入れる**形です。

```
/plugin install {plugin-name}@little-hands
```

> **プラグインが見つからない場合:** マーケットプレイスが登録済みでもプラグインが見つからない場合は、マーケットプレイスの更新が必要です。
>
> 1. `/plugin` を実行
> 2. **Marketplaces** タブを選択
> 3. **little-hands** を選択
> 4. **Update** を選択

### 自動更新の設定（推奨）

`/plugin` → **Marketplaces** → **little-hands** → **Enable auto-update** を選択すると、以降は更新が自動で適用されます。

## ライセンス

[MIT](./LICENSE)
