# タイトル

リード。

```mermaid
sequenceDiagram
    participant A as 客
    participant B as サーバー
    A->>B: 1. 開く
    B-->>A: 2. 返す
```

## 2. 円価格を返す

```python
to_jpy(Decimal("29.99"), "USD")
```

## 4c. 取り扱いのない通貨 ⚠️

```python
RateUnavailable("BRL")
```
