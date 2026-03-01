# 勢力仕様 (Faction Specification)

## 概要
本ゲームには2つの勢力が存在し、プレイヤーはオンボーディング時に所属する勢力を選択する。
勢力はパイロットデータに紐付けられ、ショップの品揃えに影響を与える。

## 勢力一覧

### 地球連邦軍 (Earth Federation Forces)
- **コード**: `FEDERATION`
- **練習機**: RGM-79T GM Trainer (`gm_trainer`)
- **購入可能機体**: GM, Gundam（連邦軍系機体）

### ジオン公国軍 (Principality of Zeon)
- **コード**: `ZEON`
- **練習機**: MS-06T Zaku II Trainer (`zaku_ii_trainer`)
- **購入可能機体**: Zaku II, Dom, Gouf, Gelgoog（ジオン軍系機体）

## 練習機仕様
- 両勢力の練習機は**完全に同一のステータス**を持つ（初期格差なし）
- 練習機はショップには並ばない専用機体

| ステータス | 値 |
|---|---|
| HP | 700 |
| 装甲 | 40 |
| 機動性 | 1.0 |
| 索敵範囲 | 500.0 |
| ビーム耐性 | 0.0 |
| 実弾耐性 | 0.0 |
| 武装 | Trainer Rifle (威力80, 射程400, 命中60%) |

## ショップ制限
- `GET /api/shop/listings` は、ログインユーザーの勢力に一致する機体のみを返す
- 勢力が未設定（空文字）のパイロットには全機体が表示される（後方互換）
- 勢力が合致しない機体を `POST /api/shop/purchase/{item_id}` で購入しようとすると `403 Forbidden` が返る

## データモデル
`Pilot` テーブルの `faction` カラム（`VARCHAR`, デフォルト空文字）に勢力コードを格納する。
