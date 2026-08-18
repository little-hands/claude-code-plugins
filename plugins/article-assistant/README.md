# article-assistant

記事執筆を伴走サポートする編集者プラグイン。

## 機能

抽象的なアイデアの状態から、対話を通じて記事を完成まで導きます。ブログ以外にも、さまざまな記事のアシストが可能です。

**執筆プロセス:**

1. アイデアの深掘り（なぜ書きたいのか、背景の気持ちを質問で引き出す）
2. 記事の切り口のブレスト（どう膨らませると面白いか、複数案を提示）
3. 記事の狙いの整理（誰に読んで欲しいか・どう思って欲しいか・何を特に伝えたいか）
4. 構成づくり（ユーザー主導。編集者はフィードバックで改善を支援）
5. セクションごとの本文生成と修正サイクル

各ステップでユーザーの確認を取ってから次へ進むため、AI が勝手に書き進めることはありません。

**含まれるスキル:**

- `article-assistant`: 記事執筆の編集者アシスタント

## 前提条件

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI が利用可能であること

## インストール

ターミナルで `claude` を起動し、以下のコマンドを実行してください。

```
/plugin marketplace add little-hands/claude-code-plugins
/plugin install article-assistant@little-hands
```

> **プラグインが見つからない場合:** マーケットプレイスが登録済みでもプラグインが見つからない場合は、マーケットプレイスの更新が必要です。
>
> 1. `/plugin` を実行
> 2. **Marketplaces** タブを選択
> 3. **little-hands** を選択
> 4. **Update** を選択
>
> 更新後、再度 `/plugin install article-assistant@little-hands` を実行してください。

### 自動更新の設定（推奨）

プラグインを常に最新の状態に保つため、マーケットプレイスの自動更新を有効にしてください。

1. `/plugin` を実行
2. **Marketplaces** タブを選択
3. **little-hands** を選択
4. **Enable auto-update** を選択

## 使い方

このプラグインのスキルは明示的にスラッシュコマンドで呼び出して使います（会話中に自動で発動しません）。

| コマンド | 用途 |
|----------|------|
| `/article-assistant` | 記事を書きたくなったら最初に呼ぶ。アイデアの深掘りから本文生成まで編集者として伴走 |

同名の他のコマンドがある場合は、名前空間付きの `/article-assistant:article-assistant` で呼び出してください。

書きたいテーマが漠然としていても構いません。「アイデアがない」と伝えれば、頭の中の気持ちを吐き出すところから一緒に始めます。

## スキル

- [article-assistant/SKILL.md](./skills/article-assistant/SKILL.md)

## ライセンス

MIT
