# 設計図システム（`master_blueprints` / `player_blueprints`）

## 概要

Epic #550「戦利品ドロップと設計図システム」のデータ基盤（Issue #551）。
設計図は「その機体・武器をショップで生産（購入）できる権利」を表す。
設計図を1度入手すれば、以降はクレジットで何度でも購入できる。
設計図なしで購入できるアイテムは **標準配備品** とする。

データ基盤とサービス層（Issue #551）、admin-tool での設計図設定の編集（Issue #554）、ショップの購入制限と「未解放」表示（Issue #556）、ドロップテーブルと抽選（Issue #560）を実装済み。
標準配備を外したアイテムの設計図は、ドロップテーブルに入れるとバトルで入手できる。

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
* ドロップテーブル（`drop_tables` / `drop_table_entries`）と `battle_results.loot` は「ドロップテーブルと抽選（Issue #560）」を参照

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
* 機体・武器マスターを削除すると、対応する設計図マスターと全プレイヤーの所持記録、その設計図を含むドロップテーブルのエントリーも削除する

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
| `get_unlock_states(session, user_id, target_type, target_ids)` | ショップ一覧用に、対象アイテムごとの解放状態（`UnlockState(is_standard_issue, is_unlocked, unlock_hint)`）を返す。判定は `can_purchase` と同じ。設計図マスター・所持設計図・ドロップテーブル（未解放のアイテムがあるときだけ）をそれぞれ1回のクエリで取得し、商品数によらずクエリは最大3回 |
| `grant_blueprint(session, user_id, blueprint_id, source, source_battle_id=None)` | 設計図を付与する。未所持なら所持記録を作り、所持済みなら `duplicate_credit_value` 分のクレジットを `Pilot.credits` に加算する。結果を `BlueprintGrantResult(blueprint_id, is_new, credits_awarded)` で返す |
| `get_player_blueprints(session, user_id)` | 所持設計図の一覧を入手日時の古い順に返す |
| `ensure_master_blueprint(session, target_type, target_id, price)` | 設計図マスターが無ければ標準配備で作成する。既存の設定は上書きしない |
| `save_master_blueprint_settings(session, target_type, target_id, price, settings)` | 設計図マスターが無ければ作成してから、`settings`（`MasterBlueprintSettingsInput`）で指定した項目を保存する。未指定（`None`）の項目は変更しない |
| `settings_of(blueprint, price)` | 設計図マスターの設定を `MasterBlueprintSettings` で返す。設計図マスターが無ければ作成時と同じ初期値を返す（`can_purchase` と同じく標準配備扱い） |
| `delete_master_blueprint(session, target_type, target_id)` | 設計図マスターと所持記録、その設計図を含むドロップテーブルのエントリーを削除する |

* `grant_blueprint` / `ensure_master_blueprint` / `save_master_blueprint_settings` / `delete_master_blueprint` は **コミットしない**。バトル終了時の抽選（`DropService.roll`）で、バトル結果の保存と同じトランザクションに載せるため
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

## ショップの購入制限と「未解放」表示（Issue #556）

### 購入 API

`POST /api/shop/purchase/{item_id}`（機体）・`POST /api/shop/purchase/weapon/{weapon_id}`（武器）で、`can_purchase()` が `False` のアイテムは `403` を返す。クレジットは減らない。

| 順序 | 判定 | エラー |
|---|---|---|
| 1 | 商品の存在 | `404` |
| 2 | パイロット | `404` |
| 3 | 勢力（機体のみ） | `403`「この機体はあなたの勢力（…）では購入できません」 |
| 4 | 設計図 | `403`「この機体の設計図を所持していません」／「この武器の設計図を所持していません」 |
| 5 | 所持金 | `400` |

* 機体は `purchase_mobile_suit()`（`app/routers/shop.py`）、武器は `WeaponService.purchase_weapon()` で判定する
* 標準配備品と、設計図マスターが無いアイテムは設計図なしで購入できる

### ショップ一覧 API

`GET /api/shop/listings`（機体）・`GET /api/shop/weapons`（武器）の各商品に次の項目を追加した。

| 項目 | 内容 |
|---|---|
| `is_standard_issue` | 標準配備品か。設計図マスターが無いアイテムは `true` |
| `is_unlocked` | 購入できるか（標準配備品、または設計図を所持している） |
| `unlock_hint` | 未解放のときに表示する入手方法のヒント。解放済みなら `null` |

* `GET /api/shop/weapons` はプレイヤーごとの解放状態を返すため、**認証必須** に変更した（未認証は `401`）
* `unlock_hint` はサーバー側で組み立てる。Issue #556 時点では固定の文言だった。Issue #560 でドロップテーブルから組み立てるように変更した（「ドロップテーブルと抽選（Issue #560）」の「ショップの入手ヒント」）
* 解放状態はプレイヤーごとに異なるため、`SHOP_LISTINGS` / `WEAPON_SHOP_LISTINGS` の TTL キャッシュには入れない

### ショップ画面

画面側の仕様は `shop-ui-improvement.md` の「12. 設計図による購入制限と「未解放」表示」を参照。

### 着手前のデータ確認（2026-09-26）

#551 のマイグレーションでは、`mobile_suits.master_mobile_suit_id` が `NULL` で、機体名でも機体マスターを引けない所持機体に設計図を付与していない。
本番DB（Neon）を読み取り専用のクエリで確認した結果は次のとおり。

* 該当する所持機体（NPC・エース機を除く）は1件。練習機（`MS-06T Zaku II Trainer`）で、改名した機体ではなかった
* 練習機は機体マスターに存在せずショップでも販売していないため、設計図の付与は不要。データ修正は行っていない

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

## ドロップテーブルと抽選（Issue #560）

バトル終了時に、プレイヤーごとに設計図のドロップを抽選して付与する。
何がどの確率で出るかはドロップテーブルに持たせ、抽選結果は `BattleResult.loot` に記録する。

### テーブル構成

```
drop_tables (ドロップテーブル)
├── id: int
├── scope_type: str              ← 適用範囲の種別 MISSION / BATCH (DropScopeType)
├── scope_key: str               ← MISSION は missions.id の文字列、BATCH は "default"
├── name: str                    ← 管理用の名前
├── drop_rate: float             ← 1回のバトルで何かがドロップする確率 (0〜1)
├── win_rate_multiplier: float   ← 勝利時に drop_rate に掛ける倍率 (1以上)
└── created_at / updated_at
   UNIQUE (scope_type, scope_key)

drop_table_entries (テーブルに含まれる設計図)
├── id: int
├── drop_table_id: int           ← drop_tables.id (FK)
├── blueprint_id: str            ← master_blueprints.id (FK)
├── weight: int                  ← 抽選の重み (1以上)
└── requires_win: bool           ← true なら勝利時だけ抽選対象
   UNIQUE (drop_table_id, blueprint_id)

battle_results.loot: JSON|null   ← 戦利品の一覧 (LootItem)
```

* 定期バトル（`BattleRoom`）にはミッションも戦闘環境も無いため、定期バトル全体で1つのテーブル（`BATCH` / `default`）を使う
* 将来の戦域ローテーションでは、`DropScopeType` に戦域・環境単位の種別を追加する
* 同じ設計図を複数のテーブルに入れられる
* マイグレーション `j4e5f6a7b8c9` はテーブル作成とカラム追加のみ。既存のバトル結果の `loot` は `NULL` のまま

### 抽選（`app/services/drop_service.py`）

`DropService.roll(session, user_id, scope, is_win, battle_result_id, rng)` がプレイヤー1人分の抽選と付与を行い、`list[LootItem]` を返す。コミットは呼び出し側で行う。

1. パイロットが無い、または NPC パイロット（`Pilot.is_npc`）なら抽選しない
2. `scope`（`DropScope.mission(mission_id)` / `DropScope.batch()`）に対応するテーブルが無ければドロップしない
3. `rng.random()` がドロップ率未満ならドロップする。勝利時のドロップ率は `min(drop_rate × win_rate_multiplier, 1)`
4. 抽選対象のエントリーから、`weight` の重みで1つ選ぶ（`rng.choices`）。次のエントリーは対象外
   * 敗北時の `requires_win = true` のエントリー
   * パイロットの勢力では購入できない機体の設計図。判定はショップと同じ `is_available_to_faction()`（`app/core/gamedata.py`）。武器には勢力が無いため対象外にならない
5. 対象が無ければドロップしない。あれば `BlueprintService.grant_blueprint(source=DROP, source_battle_id=battle_result_id)` で付与する。所持済みなら `duplicate_credit_value` 分のクレジットに換金される

* 1回のバトルでドロップするのは最大1個
* 勝利は `win_loss == "WIN"`。`DRAW` は敗北と同じ扱い
* 乱数は `random.Random` を引数で受け取る。テストでは結果を固定できる

### 組み込み先

| 経路 | 場所 | 適用範囲 |
|---|---|---|
| ソロミッション | `main.py` の `POST /api/battle/simulate`（報酬付与の直後） | `DropScope.mission(mission_id)` |
| 定期バトル | `scripts/run_batch.py` の `_save_battle_results`（プレイヤーごとの報酬付与の直後） | `DropScope.batch()` |

* 所持設計図の `source_battle_id` に記録するため、`BattleResult.id` を先に `uuid.uuid4()` で決めてから抽選する
* 付与した設計図・換金したクレジットは、`BattleResult` と同じコミットで確定する
* 定期バトルでは、抽選を報酬付与と別の `try/except` で囲む。1人の抽選でエラーが起きても、他のプレイヤーとバトル結果の保存は止めない（そのプレイヤーの `loot` は空配列）
* 未ログインのソロミッションと NPC は抽選しない

### 抽選結果の記録

```json
[
  {
    "kind": "BLUEPRINT",
    "blueprint_id": "mobile_suit:gelgoog",
    "target_type": "MOBILE_SUIT",
    "target_id": "gelgoog",
    "is_new": true,
    "credits_awarded": 0
  }
]
```

* ドロップしなかった場合は空配列。導入前のバトル結果は `null`
* `kind` は、技術断片（Sub-Issue 8）を同じ一覧に追加するための項目
* 換金したクレジットは `credits_gained`（バトル報酬）に含めず、`credits_awarded` に記録する
* レスポンス: `POST /api/battle/simulate` の `rewards.loot`、`GET /api/battles`・`/api/battles/unread`・`/api/battles/{battle_id}` の `loot`（`BattleResultSummary`）。`rewards.total_credits` は換金後の所持クレジット
* フロントエンドは型（`LootItem`、`src/types/battleCore.ts`）のみ追加した。表示は Sub-Issue 6

### ショップの入手ヒント

`get_unlock_states()` の `unlock_hint` を、ドロップテーブルから組み立てる。

| 状態 | 例 |
|---|---|
| ミッションと定期バトルで入手できる | 「『Mission 02: 防衛線突破』・定期バトルでドロップ」 |
| すべて勝利時のみ | 「定期バトルでドロップ（勝利時のみ）」 |
| 一部の戦闘だけ勝利時のみ | 「『Mission 02: 防衛線突破』・定期バトル（勝利時のみ）でドロップ」 |
| どのテーブルにも入っていない | 「現在は入手できません」（`UNAVAILABLE_UNLOCK_HINT`） |

* ミッションはミッションID順に並べ、定期バトルを最後に置く
* ミッションが見つからない `MISSION` テーブルは、テーブル名で表示する
* 未解放のアイテムのテーブルとエントリーは、ミッション名と合わせて1回のクエリで取得する

### 初期データ（`scripts/seed/seed_drop_tables.py`）

ドロップテーブルの編集画面（Sub-Issue 5）ができるまでは、シードスクリプトで投入する。

| テーブル | `drop_rate` | `win_rate_multiplier` | エントリー |
|---|---|---|---|
| 定期バトル | 0.3 | 1.5 | dom（重み3）、zaku_ii_f（重み3）、gelgoog（重み1・勝利時のみ）、gundam（重み1・勝利時のみ） |

```bash
cd backend
python scripts/seed/seed_drop_tables.py --dry-run   # 投入内容の確認のみ
python scripts/seed/seed_drop_tables.py             # 投入（既存のテーブル・エントリーは変更しない）
python scripts/seed/seed_drop_tables.py --force     # 既存の設定もこの値で上書きする
```

* べき等に実行できる。設計図マスターが無い設計図のエントリーは投入しない
* ミッションごとのテーブルは未投入。ソロミッションは直近30日の実績が0件のため、定期バトルを優先した
* 本番DB（Neon）への投入は書き込みになるため、実行前に確認を取る

---

## 後続のSub-Issueで対応する事項

* admin-tool でのドロップテーブル編集（Sub-Issue 5）
* バトル結果モーダル・バトル履歴での戦利品表示（Sub-Issue 6）
* 設計図コレクション（図鑑）画面（Sub-Issue 7）
* レア機体向けの技術断片・技術Lv（Sub-Issue 8）。設計図マスターに必要技術Lvのカラムを追加する想定
* 戦域・環境単位のドロップテーブル（Sub-Issue 10）
* 戦場（フィールド）ごとの標準配備設定。現状はアイテム単位の真偽値のみ
