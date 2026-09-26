# 設計図システム（`master_blueprints` / `player_blueprints`）

## 概要

Epic #550「戦利品ドロップと設計図システム」のデータ基盤（Issue #551）。
設計図は「その機体・武器をショップで生産（購入）できる権利」を表す。
設計図を1度入手すれば、以降はクレジットで何度でも購入できる。
設計図なしで購入できるアイテムは **標準配備品** とする。

データ基盤とサービス層（Issue #551）と、admin-tool での設計図設定の編集（Issue #554）を実装済み。
いずれも **ゲームの挙動は変えていない**。ショップの購入制限・ドロップ抽選は後続のSub-Issueで行う。

---

## テーブル構成

```
master_blueprints (設計図マスター)
├── id: str                      ← 設計図ID (例: mobile_suit:rx_78_2 / weapon:beam_rifle)
├── target_type: str             ← MOBILE_SUIT / WEAPON
├── target_id: str               ← master_mobile_suits.id / master_weapons.id
├── is_standard_issue: bool      ← true なら設計図なしで購入できる
├── duplicate_credit_value: int  ← 入手済みの設計図を再入手したときに付与するクレジット
└── created_at / updated_at
   UNIQUE (target_type, target_id)

player_blueprints (所持設計図)
├── id: UUID
├── user_id: str                 ← 所有者 (Pilot.user_id)
├── blueprint_id: str            ← master_blueprints.id (FK)
├── source: str                  ← 入手経路 MIGRATION / DROP
├── source_battle_id: UUID|null  ← 入手元のバトル (battle_results.id、論理参照)
└── acquired_at: datetime
   UNIQUE (user_id, blueprint_id)
```

* 機体マスター・武器マスターの各アイテムに、設計図マスターが1対1で対応する
* 設計図IDは `{target_type を小文字にした値}:{target_id}` で決まる（`BlueprintService.blueprint_id_for()`）。後続のドロップテーブルから人が読める形で参照できるようにするため
* 入手経路と対象の種別は `BlueprintSource` / `BlueprintTargetType`（`app/models/models.py`）で定義する。DB上は文字列として保存する

---

## 設計図マスターの作成タイミング

| 契機 | 処理 | 初期値 |
|---|---|---|
| マイグレーション（`i3d4e5f6a7b8`） | 既存の全機体・武器マスター分を作成 | 標準配備、換金額 = 価格の20% |
| admin の機体・武器マスター新規作成 | `MobileSuitService.create_master_mobile_suit` / `WeaponService.create_master_weapon` から作成 | 同上。リクエストの `blueprint` で指定した項目はその値にする |
| admin の機体・武器マスター更新 | 設計図マスターが無いアイテム（データ不整合）を保存したときに作成 | 同上 |
| シードスクリプト（`scripts/seed/seed_master_data.py`） | 新規投入した機体・武器分を作成 | 同上 |

* 導入直後にショップの挙動を変えないため、**全件を標準配備で作成する**。運用者が admin-tool から標準配備を外していく
* 換金額の初期値（価格の20%、`DUPLICATE_CREDIT_RATIO`）は暫定値。アイテムごとに admin-tool から調整する前提で、固定の計算式にはしない
* 機体・武器マスターを削除すると、対応する設計図マスターと全プレイヤーの所持記録も削除する

---

## 既存所持品への設計図付与（マイグレーション）

マイグレーション時点で既存プレイヤーが所持している機体・武器について、対応する設計図を入手経路 `MIGRATION` で付与する。
購入制限の導入後も、すでに持っている装備を追加購入できるようにするため。

| 対象 | 特定方法 |
|---|---|
| 武器 | `player_weapons.master_weapon_id` |
| 機体 | `mobile_suits.master_mobile_suit_id`。`NULL` の場合は **機体名で機体マスターを引く**（`weapon_slot_count` の解決と同じ考え方） |

対象外:

* NPC・エース機（`user_id` が `NULL`、または `pilots.is_npc = true` のユーザーが所有）
* 練習機（`STARTER_KITS`）。機体マスターに存在しないため
* 改名した機体のうち `master_mobile_suit_id` が `NULL` のもの。機体名で機体マスターを引けないため

あわせて、ショップ購入時（`POST /api/shop/purchase/{item_id}`）に `MobileSuit.master_mobile_suit_id` を設定するよう修正した。
今後の購入制限・図鑑で機体名の照合に頼らないため。

---

## 設計図サービス（`app/services/blueprint_service.py`）

| メソッド | 内容 |
|---|---|
| `can_purchase(session, user_id, target_type, target_id)` | 購入できるかを返す。標準配備品、または設計図を所持していれば `True`。設計図マスターが無いアイテムは導入前と同じく `True` |
| `grant_blueprint(session, user_id, blueprint_id, source, source_battle_id=None)` | 設計図を付与する。未所持なら所持記録を作り、所持済みなら `duplicate_credit_value` 分のクレジットを `Pilot.credits` に加算する。結果を `BlueprintGrantResult(blueprint_id, is_new, credits_awarded)` で返す |
| `get_player_blueprints(session, user_id)` | 所持設計図の一覧を入手日時の古い順に返す |
| `ensure_master_blueprint(session, target_type, target_id, price)` | 設計図マスターが無ければ標準配備で作成する。既存の設定は上書きしない |
| `save_master_blueprint_settings(session, target_type, target_id, price, settings)` | 設計図マスターが無ければ作成してから、`settings`（`MasterBlueprintSettingsInput`）で指定した項目を保存する。未指定（`None`）の項目は変更しない |
| `settings_of(blueprint, price)` | 設計図マスターの設定を `MasterBlueprintSettings` で返す。設計図マスターが無ければ作成時と同じ初期値を返す（`can_purchase` と同じく標準配備扱い） |
| `delete_master_blueprint(session, target_type, target_id)` | 設計図マスターと所持記録を削除する |

* `grant_blueprint` / `ensure_master_blueprint` / `save_master_blueprint_settings` / `delete_master_blueprint` は **コミットしない**。バトル終了時に複数プレイヤーへまとめて付与する処理（後続Sub-Issue）で、報酬付与と同じトランザクションに載せるため
* `grant_blueprint` は、設計図マスターが無い場合と、所持済みでクレジットを加算するパイロットが無い場合に `LookupError` を送出する

---

## API

### `GET /api/blueprints/me`

ログイン中プレイヤーの所持設計図一覧を返す（要認証）。後続の購入制限・図鑑画面で使用する。

```json
[
  {
    "blueprint_id": "mobile_suit:zaku_ii",
    "target_type": "MOBILE_SUIT",
    "target_id": "zaku_ii",
    "source": "MIGRATION",
    "source_battle_id": null,
    "acquired_at": "2026-09-26T00:00:00"
  }
]
```

---

## admin-tool での設計図設定の編集（Issue #554）

機体マスター（`/mobile-suits`）・武器マスター（`/weapons`）の画面で、アイテムごとの設計図設定を確認・編集できる。
新規エンドポイントは作らず、既存の admin API に `blueprint` を追加した。

| API | `blueprint` |
|---|---|
| `GET /api/admin/mobile-suits`・`/api/admin/weapons` | 各アイテムの設定（`MasterBlueprintSettings`: `is_standard_issue` / `duplicate_credit_value`）。機体・武器マスターと設計図マスターを外部結合の1クエリで取得する |
| `POST`（新規作成） | 任意（`MasterBlueprintSettingsInput`）。省略した項目は初期値（標準配備・価格の20%） |
| `PUT`（更新） | 任意（`MasterBlueprintSettingsInput`）。省略した項目は変更しない |

* 価格を変更しても、換金額は自動で追従させない。換金額は運用者が明示的に決める値のため
* 換金額に負の値を指定すると `422`
* 設計図マスターが無いアイテム（#551 以前のデータ不整合など）は、一覧では初期値で表示する。保存したときに設計図マスターを作成する
* admin-tool の一覧に「設計図（標準配備／要設計図）」「換金額」列と、標準配備・要設計図の絞り込みを追加した
* 編集フォームの「設計図」欄で標準配備フラグと換金額を編集する。換金額の空欄は、新規作成では初期値、編集では変更なしとして送る
* Clone & Edit では、コピー元の設計図設定を引き継ぐ

---

## 後続のSub-Issueで対応する事項

* ショップでの購入制限と「未解放」表示（`can_purchase` の組み込み）
* ドロップテーブル・抽選（`grant_blueprint` の組み込み、入手経路 `DROP`）
* レア機体向けの技術断片・技術Lv。設計図マスターに必要技術Lvのカラムを追加する想定
* 戦場（フィールド）ごとの標準配備設定。現状はアイテム単位の真偽値のみ
