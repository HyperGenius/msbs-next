# 設計図システム（`master_blueprints` / `player_blueprints`）

## 概要

Epic #550「戦利品ドロップと設計図システム」のデータ基盤（Issue #551）。
設計図は「その機体・武器をショップで生産（購入）できる権利」を表す。
設計図を1度入手すれば、以降はクレジットで何度でも購入できる。
設計図なしで購入できるアイテムは **標準配備品** とする。

データ基盤とサービス層（Issue #551）、admin-tool での設計図設定の編集（Issue #554）、ショップの購入制限と「未解放」表示（Issue #556）、ドロップテーブルと抽選（Issue #560）、admin-tool でのドロップテーブル編集（Issue #562）、戦利品の表示（Issue #564）、設計図コレクション（図鑑）画面（Issue #566）、技術断片と技術Lv（Issue #569）を実装済み。
標準配備を外したアイテムの設計図は、ドロップテーブルに入れるとバトルで入手できる。
設計図に必要な技術Lvを設定すると、設計図と技術Lvがそろったときだけ購入できる（「技術断片と技術Lv（Issue #569）」）。

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
* 技術マスター・必要な技術Lv・プレイヤーの累計断片数（`master_technologies` / `blueprint_tech_requirements` / `player_technologies`）は「技術断片と技術Lv（Issue #569）」を参照

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
* 機体・武器マスターを削除すると、対応する設計図マスターと全プレイヤーの所持記録、その設計図を含むドロップテーブルのエントリー、必要な技術Lvの設定も削除する

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
| 4 | 技術Lv（Issue #569） | `403`「技術Lvが足りません: サイコミュ技術 Lv2 が必要（現在 Lv1）」。設計図が無い場合は設計図のエラーを優先する |
| 5 | 所持金 | `400` |

* 機体は `purchase_mobile_suit()`（`app/routers/shop.py`）、武器は `WeaponService.purchase_weapon()` で判定する
* 標準配備品と、設計図マスターが無いアイテムは設計図なしで購入できる

### ショップ一覧 API

`GET /api/shop/listings`（機体）・`GET /api/shop/weapons`（武器）の各商品に次の項目を追加した。

| 項目 | 内容 |
|---|---|
| `is_standard_issue` | 標準配備品か。設計図マスターが無いアイテムは `true` |
| `is_unlocked` | 購入できるか（標準配備品、または設計図を所持している） |
| `unlock_hint` | 設計図の入手方法のヒント。設計図を所持していれば `null` |
| `missing_tech_requirements` | 足りない技術Lv（`tech_id` / `tech_name` / `required_lv` / `current_lv`）。標準配備品と、技術Lvが足りている商品は空配列（Issue #569） |

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
| `GET /api/admin/mobile-suits`・`/api/admin/weapons` | 各アイテムの設定（`MasterBlueprintSettings`: `is_standard_issue` / `duplicate_credit_value` / `tech_requirements`）。機体・武器マスターと設計図マスターを外部結合の1クエリ、必要な技術Lvを1クエリで取得する |
| `POST`（新規作成） | 任意（`MasterBlueprintSettingsInput`）。省略した項目は初期値（標準配備・価格の20%） |
| `PUT`（更新） | 任意（`MasterBlueprintSettingsInput`）。省略した項目は変更しない |

* 価格を変更しても、換金額は自動で追従させない。換金額は運用者が明示的に決める値のため
* 換金額に負の値を指定すると `422`
* 設計図マスターが無いアイテム（#551 以前のデータ不整合など）は、一覧では初期値で表示する。保存したときに設計図マスターを作成する
* admin-tool の一覧に「設計図（標準配備／要設計図）」「換金額」列と、標準配備・要設計図の絞り込みを追加した
* 編集フォームの「設計図」欄で標準配備フラグと換金額を編集する。換金額の空欄は、新規作成では初期値、編集では変更なしとして送る
* Clone & Edit では、コピー元の設計図設定を引き継ぐ
* 必要な技術Lv（`tech_requirements`）の編集は「技術断片と技術Lv（Issue #569）」の「admin-tool」を参照

---

## ドロップテーブルと抽選（Issue #560）

バトル終了時に、プレイヤーごとに設計図のドロップを抽選して付与する。
何がどの確率で出るかはドロップテーブルに持たせ、抽選結果は `BattleResult.loot` に記録する。

### テーブル構成

```
drop_tables (ドロップテーブル)
├── id: int
├── scope_type: str              ← 適用範囲の種別 MISSION / BATCH / THEATER (DropScopeType)
├── scope_key: str               ← MISSION は missions.id の文字列、BATCH は "default"、THEATER は master_theaters.id
├── name: str                    ← 管理用の名前
├── drop_rate: float             ← 1回のバトルで何かがドロップする確率 (0〜1)
├── win_rate_multiplier: float   ← 勝利時に drop_rate に掛ける倍率 (1以上)
└── created_at / updated_at
   UNIQUE (scope_type, scope_key)

drop_table_entries (テーブルに含まれる設計図・技術断片)
├── id: int
├── drop_table_id: int           ← drop_tables.id (FK)
├── reward_type: str             ← BLUEPRINT / TECH_FRAGMENT (DropRewardType、Issue #569)
├── blueprint_id: str|null       ← master_blueprints.id (FK)。BLUEPRINT のときだけ入る
├── tech_id: str|null            ← master_technologies.id (FK)。TECH_FRAGMENT のときだけ入る
├── weight: int                  ← 抽選の重み (1以上)
└── requires_win: bool           ← true なら勝利時だけ抽選対象
   UNIQUE (drop_table_id, blueprint_id)
   UNIQUE (drop_table_id, tech_id)
   CHECK (reward_type に対応する blueprint_id・tech_id の片方だけが入る)

battle_results.loot: JSON|null   ← 戦利品の一覧 (LootItem)
```

* 定期バトルは、ルームの戦域のテーブル（`THEATER` / 戦域ID）で抽選する。戦域のテーブルが無ければ共通テーブル（`BATCH` / `default`）で抽選する（「戦域別ドロップテーブル（Issue #580）」）
* 同じ設計図を複数のテーブルに入れられる
* マイグレーション `j4e5f6a7b8c9` はテーブル作成とカラム追加のみ。既存のバトル結果の `loot` は `NULL` のまま

### 抽選（`app/services/drop_service.py`）

`DropService.roll(session, user_id, scope, is_win, battle_result_id, rng)` がプレイヤー1人分の抽選と付与を行い、`list[LootItem]` を返す。コミットは呼び出し側で行う。

1. パイロットが無い、または NPC パイロット（`Pilot.is_npc`）なら抽選しない
2. `scope`（`DropScope.mission(mission_id)` / `DropScope.batch()` / `DropScope.theater(theater_id)`）から抽選に使うテーブルを決める（`DropService.resolve_table()`）。戦域のテーブルが無ければ共通テーブルを使う。どちらも無ければドロップしない
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
| 定期バトル | `scripts/run_batch.py` の `_save_battle_results`（プレイヤーごとの報酬付与の直後） | `DropScope.for_battle(conditions.theater_id)`。戦域なしなら `DropScope.batch()` |

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
* `kind` は戦利品の種別。技術断片は `TECH_FRAGMENT`（「技術断片と技術Lv（Issue #569）」）
* 換金したクレジットは `credits_gained`（バトル報酬）に含めず、`credits_awarded` に記録する
* レスポンス: `POST /api/battle/simulate` の `rewards.loot`、`GET /api/battles`・`/api/battles/unread`・`/api/battles/{battle_id}` の `loot`（`BattleResultSummary`）。`rewards.total_credits` は換金後の所持クレジット
* レスポンスの各項目には、表示用の `target_name` が付く（「戦利品の表示（Issue #564）」）

### ショップの入手ヒント

`get_unlock_states()` の `unlock_hint` を、ドロップテーブルから組み立てる。

| 状態 | 例 |
|---|---|
| ミッションと戦域で入手できる | 「『Mission 02: 防衛線突破』・東南アジア密林でドロップ」 |
| すべて勝利時のみ | 「ソロモン宙域でドロップ（勝利時のみ）」 |
| 一部の戦闘だけ勝利時のみ | 「ソロモン宙域（勝利時のみ）・東南アジア密林でドロップ」 |
| 全戦域が共通テーブルを使う | 「全戦域でドロップ」 |
| どのテーブルにも入っていない | 「現在は入手できません」（`UNAVAILABLE_UNLOCK_HINT`） |

* ミッションはミッションID順に並べ、その後に戦域を巡回順に並べる
* 戦域の表示名は図鑑と同じ変換（`TheaterDropSources`、「戦域別ドロップテーブル（Issue #580）」）で決める。無効な戦域は出さない
* ミッションが見つからない `MISSION` テーブルは、テーブル名で表示する
* 未解放のアイテムのテーブルとエントリーは、ミッション名と合わせて1回のクエリで取得する。戦域とテーブルの有無の取得で、もう1回クエリを使う

### 初期データ（`scripts/seed/seed_drop_tables.py`）

初期値の投入用。投入後の調整は admin-tool の `/drop-tables`（「admin-tool でのドロップテーブル編集（Issue #562）」）で行う。

| テーブル | `drop_rate` | `win_rate_multiplier` | エントリー |
|---|---|---|---|
| 定期バトル（共通テーブル） | 0.3 | 1.5 | dom（重み3）、zaku_ii_f（重み3）、gelgoog（重み1・勝利時のみ）、gundam（重み1・勝利時のみ） |
| ソロモン宙域（`THEATER` / `solomon`） | 0.3 | 1.5 | zaku_ii_f（重み3）、gelgoog（重み1・勝利時のみ）、技術断片 beam_generator_tech（重み2）・psycommu_tech（重み1） |
| 東南アジア密林（`THEATER` / `southeast_asia_jungle`） | 0.3 | 1.5 | dom（重み3）、gouf（重み3）、技術断片 beam_generator_tech（重み2）・psycommu_tech（重み1） |

* 戦域のテーブルは暫定案。戦域向けの機体を追加するとき（Epic #573 Sub-Issue 10）に見直す

```bash
cd backend
python scripts/seed/seed_drop_tables.py --dry-run   # 投入内容の確認のみ
python scripts/seed/seed_drop_tables.py             # 投入（既存のテーブル・エントリーは変更しない）
python scripts/seed/seed_drop_tables.py --force     # 既存の設定もこの値で上書きする
```

* べき等に実行できる。設計図・技術マスターが無いエントリーと、戦域マスターが無い戦域のテーブルは投入しない
* ミッションごとのテーブルは未投入。ソロミッションは直近30日の実績が0件のため、定期バトルを優先した
* 本番DB（Neon）への投入は書き込みになるため、実行前に確認を取る
* シードを実行していなくても、admin-tool で保存すれば定期バトルのテーブルが作成される

---

## admin-tool でのドロップテーブル編集（Issue #562）

admin-tool の `/drop-tables` で、定期バトルのテーブル（`BATCH` / `default`）の設定とエントリーを編集できる。
画面・API の仕様は `admin-drop-tables.md` を参照。

* 編集対象は定期バトルの共通テーブルと戦域のテーブル（Issue #580 で追加）。ミッションのテーブルは変更しない
* 保存すると、ショップの `unlock_hint` と定期バトルの抽選に次のリクエスト・次のバッチから反映される（どちらもテーブルを都度DBから読む）
* 抽選ロジック（`DropService.roll()`）は変更していない。テーブルの取得を `DropService.find_table()` に切り出し、admin API と共用している
* 画面の出現率は `DropService.roll()` と同じ計算をフロントエンドで行う。抽選の計算を変える場合は `admin-tool/src/lib/dropTable.ts` の `dropChances()` もそろえる

---

## 戦利品の表示（Issue #564）

バトル結果モーダルとバトル履歴で、入手した戦利品を表示する。

### API: 対象の名前（`target_name`）

レスポンスの戦利品（`LootItemDetail`）に、対象の表示名 `target_name` を追加した。

```json
{
  "kind": "BLUEPRINT",
  "blueprint_id": "mobile_suit:gelgoog",
  "target_type": "MOBILE_SUIT",
  "target_id": "gelgoog",
  "target_name": "ゲルググ",
  "is_new": true,
  "credits_awarded": 0
}
```

| 対象 | `target_name` |
|---|---|
| 機体 | 機体マスターの `name_ja`。空なら `name` |
| 武器 | 武器マスターの `name` |
| マスターが無い（削除済み） | `target_id` |

* 名前は `battle_results.loot` に保存しない。レスポンスを組み立てるときに機体・武器マスターから引く（`LootService`、`app/services/loot_service.py`）。導入済みのバトル結果にも名前を付けるため
* 対象: `POST /api/battle/simulate` の `rewards.loot`、`GET /api/battles`・`/api/battles/unread`・`/api/battles/{battle_id}` の `loot`
* `LootService.summaries()` は、バトル件数によらず最大2回のクエリ（機体・武器マスター）で名前を取得する。戦利品が無ければクエリしない
* `loot = null`（導入前のバトル）はそのまま `null` で返す

### 画面

| 画面 | 表示 |
|---|---|
| バトル結果モーダル（`BattleResultModal`） | 獲得報酬の下の「戦利品」欄。詳細は `battle-result-modal.md` |
| バトル履歴の一覧（`BattleList`） | 戦利品のあったバトルにバッジ（`LootBadge`）。新規入手があれば `NEW`、換金のみなら換金額の合計 |
| バトル詳細（`BattleSummaryPanel`） | 戦果サマリーの「戦利品」欄。表示内容はモーダルと同じ |

* 1件の表示は共通コンポーネント `LootItemCard`（`src/components/loot/`）。一覧は `LootList`
  * 新規入手（`is_new = true`）: シアンで強調し、`NEW` と「ショップで購入できるようになりました」を表示する
  * 換金（`is_new = false`）: アンバーで「所持済みのため +N C に換金」を表示する
* ドロップなし（空配列）は「戦利品なし」を控えめに表示する。導入前のバトル（`null`）は欄もバッジも出さない
* 換金したクレジットは、獲得報酬のクレジット（`credits_gained`）と分けて表示する

---

## 設計図コレクション（図鑑）（Issue #566）

設計図の所持・未所持と、未所持の設計図を入手できる戦域を一覧で確認できる。
画面の仕様は `blueprint-collection.md` を参照。

### `GET /api/blueprints/collection`

ログイン中プレイヤーの図鑑の一覧を、設計図ID順に返す（要認証）。`GET /api/blueprints/me` は変更していない。

```json
[
  {
    "blueprint_id": "mobile_suit:gelgoog",
    "target_type": "MOBILE_SUIT",
    "target_id": "gelgoog",
    "target_name": "Gelgoog",
    "faction": "ZEON",
    "is_standard_issue": false,
    "is_owned": false,
    "acquired_at": null,
    "source": null,
    "is_available_to_faction": true,
    "obtainable_theaters": [{ "label": "全戦域", "requires_win": true }]
  }
]
```

| 項目 | 内容 |
|---|---|
| `target_name` | 機体は `name_ja`、空なら `name`。武器は `name` |
| `faction` | 機体の勢力。武器と共通機体は空文字 |
| `is_owned` / `acquired_at` / `source` | 所持設計図（`player_blueprints`）の有無と、入手日時・入手経路。未所持なら `false` / `null` / `null` |
| `is_available_to_faction` | パイロットの勢力で入手できるか。判定はショップ・抽選と同じ `is_available_to_faction()`。パイロットが無ければ `true` |
| `obtainable_theaters` | 入手できる戦域（`label` / `requires_win`）。未所持・要設計図・勢力内の設計図だけに入れる。それ以外は空配列 |

* 機体・武器マスターが無い設計図（データ不整合）は返さない
* 実装は `BlueprintCollectionService.get_collection()`（`app/services/blueprint_collection_service.py`）。パイロット・所持設計図・ドロップテーブルとエントリー・有効な戦域とテーブルの有無・設計図マスターと機体・武器マスター・技術Lvをそれぞれ1回のクエリで取得し、設計図の数によらずクエリは8回
* ドロップ率は返さない

### 適用範囲から戦域の表示への変換

ドロップテーブルから図鑑の戦域名への変換は、`TheaterDropSources.sources_for()`（`app/services/drop_source_service.py`）の1か所にまとめている。ショップの `unlock_hint` も同じ変換を使う。

| 適用範囲 | 図鑑での表示 |
|---|---|
| 戦域（`THEATER`） | 戦域名。戦域が無効なら表示しない |
| 共通テーブル（`BATCH` / `default`） | 共通テーブルを使う有効な戦域の名前。すべての有効な戦域が共通テーブルを使うなら「全戦域」（`ALL_THEATERS_LABEL`）。共通テーブルを使う有効な戦域が無ければ表示しない |
| ミッション（`MISSION`） | 表示しない。ソロミッションを運用していないため |

* ミッションのテーブルにしか入っていない設計図は、`obtainable_theaters` が空になる（画面では「現在は入手できません」）
* 戦域は巡回順に並べる。「全戦域」は先頭に置く
* 同じ戦域が複数のテーブルにあれば1件にまとめる。どれか1つでも敗北時にドロップするなら `requires_win = false`

---

## 技術断片と技術Lv（Issue #569）

機体・武器に共通の **技術断片** をバトルでドロップさせ、集めた数でプレイヤーの **技術Lv** を上げる。
レア機体・レア武器は「設計図 ＋ 必要な技術Lv」がそろったときに購入できる。
技術はコードで固定せずマスターデータとして持ち、admin-tool から追加・編集する。

> **注意: 機体の `beam_generator_lv` とは別物。**
> `MasterMobileSuit.beam_generator_lv`・`WeaponSpecBase.required_beam_generator_lv` は、その機体が装備できるビーム武器のLv（装備制約）。
> 本節の技術Lv（例: ビームジェネレータ技術 `beam_generator_tech`）はプレイヤーごとの値で、購入条件にだけ使う。
> 名前が重ならないよう、技術IDは `*_tech` とする。

### テーブル構成

```
master_technologies (技術マスター)
├── id: str                      ← スネークケース (例: beam_generator_tech)
├── name: str                    ← 表示名
├── description: str
├── level_thresholds: JSON       ← Lvごとに必要な累計断片数。要素数が最大Lv
├── overflow_credit_value: int   ← 最大Lv後に断片を入手したときに付与するクレジット
└── created_at / updated_at

blueprint_tech_requirements (設計図の購入に必要な技術Lv)
├── id: int
├── blueprint_id: str            ← master_blueprints.id (FK)
├── tech_id: str                 ← master_technologies.id (FK)
└── required_lv: int             ← 1以上、技術の最大Lv以下
   UNIQUE (blueprint_id, tech_id)

player_technologies (プレイヤーの累計断片数)
├── id: UUID
├── user_id: str                 ← Pilot.user_id
├── tech_id: str                 ← master_technologies.id (FK)
├── fragment_count: int          ← 累計の断片入手数
└── updated_at
   UNIQUE (user_id, tech_id)
```

* `level_thresholds` は1要素以上で、正の整数の狭義単調増加（`validate_level_thresholds()`）。違反は admin API で `422`
* 必要な技術Lvは **設計図マスターに紐づける**（機体マスターには持たせない）。機体・武器（将来は拡張パーツ）を同じ仕組みで扱うため。参照整合性のため JSON ではなく別テーブルにした
* 技術Lvは DB に保存しない。累計数と閾値から毎回計算する（`TechnologyService.level_for()`）。閾値を引き上げると既存プレイヤーのLvが下がることがあるが、購入済みの機体・武器は残るため許容する
* 導入時点では全プレイヤーの累計数を0とする（`player_technologies` は空）。既存の機体・武器には購入条件を設定しないため、導入直後に購入できなくなるアイテムは無い
* マイグレーション `k5f6a7b8c9d0` はテーブル作成と `drop_table_entries` の変更のみ。既存のエントリーは `reward_type = BLUEPRINT` になる

### 初期データ（`backend/data/master/technologies.json`）

`scripts/seed/seed_master_data.py` で投入する（既存の技術はスキップ、`--force` で上書き）。

| ID | 名前 | 閾値 | 最大Lv後の換金額 |
|---|---|---|---|
| `beam_generator_tech` | ビームジェネレータ技術 | `[3, 8, 15]`（Lv1 = 3個 / Lv2 = 8個 / Lv3 = 15個） | 500 C |
| `psycommu_tech` | サイコミュ技術 | `[3, 8, 15]` | 500 C |

* 換金額 500 C は勝利時の基本報酬と同じ額にした仮の値。閾値と合わせて admin-tool で調整する

### 断片の付与（`TechnologyService.grant_fragment()`）

* 1回のドロップで得る断片は1個。断片は消費せず、閾値に達すると自動でLvが上がる
* 最大Lvに **達した後** の断片は累計数に加算せず、`overflow_credit_value` 分のクレジットをパイロットに加算する（設計図の重複時の換金と同じ扱い）。最大Lvに到達する断片そのものは累計数に加算する
* 技術Lvは戦闘に影響しない。戦闘中の計算・装備時のチェックには使わない（判定は購入時のみ）

### 購入の判定

`BlueprintService.get_unlock_states()`（一覧）・`get_unlock_state()`・`can_purchase()`（1件）で判定する。

| アイテム | 購入できる条件 |
|---|---|
| 標準配備品 | 常に購入できる（技術Lvも問わない） |
| 標準配備でないもの | 設計図を所持していて、必要な技術Lvをすべて満たしている |
| 設計図マスターが無いもの | 常に購入できる |

* `UnlockState` に `needs_blueprint`（設計図の入手が必要か）と `missing_tech_requirements`（足りない技術Lv）を追加した。`unlock_hint` は設計図が必要なときだけ入る
* `get_unlock_states()` のクエリはアイテム数によらず最大5回（標準配備・所持設計図・必要な技術Lv・プレイヤーの技術Lv・入手ヒント）。必要な技術Lvが1件も無ければ4回
* 購入APIのエラー文言は `purchase_denial_message()`、足りない技術Lvの文言は `format_missing_tech()`（「サイコミュ技術 Lv2 が必要（現在 Lv1）」）。frontend の `formatMissingTech()` と同じ文言

### ドロップ

* 技術断片は **設計図と同じ抽選** の中でドロップする。1回のバトルでドロップするのは最大1個（設計図 **または** 技術断片）。`weight`・`requires_win` は設計図と同じく使える
* 技術断片は勢力による絞り込みを受けない
* 候補は `reward_type, blueprint_id, tech_id` の順に並べる。同じ `reward_type` の中は NULL でない方のIDだけで順序が決まるため、DB（SQLite / PostgreSQL）の NULL の並び順に依存せず、シードだけで抽選結果が決まる。設計図だけのテーブルでは従来と同じ順序になる
* 設計図とは別枠で抽選する方式は採用していない。バランスに問題があれば別Issueで変更する

### 戦利品（`LootItem`）

```json
{
  "kind": "TECH_FRAGMENT",
  "tech_id": "psycommu_tech",
  "fragment_count": 8,
  "level": 2,
  "max_level": 3,
  "is_level_up": true,
  "fragments_to_next_level": 7,
  "credits_awarded": 0,
  "target_name": "サイコミュ技術"
}
```

| 項目 | 内容 |
|---|---|
| `fragment_count` / `level` / `max_level` | 入手後の累計数・技術Lv・最大Lv。入手した時点の値で、閾値を後から変えても書き換えない |
| `is_level_up` | この断片で技術Lvが上がったか |
| `fragments_to_next_level` | 次のLvまでに必要な断片数。最大Lvなら `null` |
| `credits_awarded` | 最大Lv後の断片を換金したクレジット |
| `target_name` | 技術マスターの `name`。マスターが無ければ `tech_id`（`LootService` が引く） |

* 設計図の項目（`blueprint_id` / `target_type` / `target_id`）は `null`、`is_new` は `false`
* 導入前の設計図の戦利品（技術断片の項目を持たない JSON）もそのまま読める。`LootService.with_names()` のクエリは最大3回（機体・武器・技術マスター）

### API

| API | 内容 |
|---|---|
| `GET /api/technologies/me`（要認証） | 全技術の進捗を技術ID順に返す（`PlayerTechnologyProgress`: `level` / `max_level` / `fragment_count` / `next_level_threshold` / `fragments_to_next_level` / `overflow_credit_value` / `obtainable_theaters`）。未入手の技術は累計0・Lv0 |
| `GET /api/blueprints/collection` | 各設計図に `tech_requirements`（`tech_id` / `tech_name` / `required_lv` / `current_lv`）を追加。標準配備品は空配列 |
| `GET /api/shop/listings`・`/api/shop/weapons` | `missing_tech_requirements` を追加（「ショップ一覧 API」） |
| `GET/POST /api/admin/technologies`、`PUT/DELETE /api/admin/technologies/{tech_id}` | 技術マスターの CRUD（`admin-technologies.md`） |
| `POST/PUT /api/admin/mobile-suits`・`/api/admin/weapons` | `blueprint.tech_requirements` を受け付ける。指定すると置き換え、省略すると変更しない。存在しない技術・最大Lv超え・重複は `422` |
| `PUT /api/admin/drop-tables/batch`（戦域のテーブルも同じ） | 技術断片のエントリー（`{"reward_type": "TECH_FRAGMENT", "tech_id": ...}`）を受け付ける（`admin-drop-tables.md`） |

* `obtainable_theaters` は設計図と同じ変換（`TheaterDropSources`）で組み立てる。`get_technologies()` は `blueprint_collection_service.py` に置いた。`TechnologyService` を抽選側（`drop_service.py`）からも使うため、`TechnologyService` は他のサービスに依存させていない

### 画面

| 画面 | 表示 |
|---|---|
| ショップの「未解放」表示 | 設計図の入手ヒントに加えて、足りない技術Lvを1行ずつ表示する（`UnlockRequirements`、`shop-ui-improvement.md`） |
| バトル結果モーダル・バトル履歴 | 技術断片のカード（技術名・累計数・次のLvまでの残り・Lvアップ・最大Lv後の換金額）。Lvアップは設計図の新規入手と同じ入手演出（`battle-result-modal.md`） |
| 図鑑（`/collection`） | 技術タブ（技術ごとのLv・累計数・次のLvまでの残り・入手先）と、所持済みの設計図に足りない技術Lv（`blueprint-collection.md`） |
| admin-tool | 技術マスター画面（`/technologies`）、設計図設定の必要な技術Lv、ドロップテーブルの技術断片エントリー |

### admin-tool

* 技術マスター画面（`/technologies`）: `admin-technologies.md`
* 機体・武器の編集フォームの「設計図」欄（`BlueprintSettingsFields`）に「必要な技術Lv」の行を追加した。技術は技術マスターから選び、Lvは1〜最大Lvから選ぶ。同じ技術は2行に置けない。保存するとフォームの内容で置き換える
* ドロップテーブル（`/drop-tables`）に「技術断片を追加」を追加した（`admin-drop-tables.md`）

### 本Issueの対象外

* 技術Lvによる能力値の補正、装備時の技術Lvチェック、サイコミュ武器の搭載条件など戦闘中の挙動に関わる制約
* 拡張パーツ（未実装）の購入条件への技術Lvの追加。拡張パーツを設計図マスターの対象に加えれば、同じ `blueprint_tech_requirements` で扱える

---

## 戦域別ドロップテーブル（Issue #580）

ドロップテーブルを戦域単位で持てるようにした（Epic #573 Sub-Issue 7、Epic #550 Sub-Issue 10）。
戦域ごとにドロップする設計図を変え、「その戦域に向いた機体を手に入れるために、向いていない構成で工夫して挑む」ループを作る。

### 抽選

* `DropScopeType.THEATER` を追加した。`scope_key` は戦域ID。`scope_type` は文字列カラムで制約も無いため、マイグレーションは無い
* 定期バトルは `DropScope.for_battle(conditions.theater_id)` で抽選する。戦域なしのルームは共通テーブル（`BATCH` / `default`）を使う
* `DropService.resolve_table()` は、戦域のテーブルがあればそれだけを使う。無ければ共通テーブルを使う
* 戦域のテーブルにエントリーが無い場合は、共通テーブルを使わない（その戦域ではドロップしない）
* 抽選の仕様（1バトル最大1個、勝利時の倍率、`requires_win`、勢力による除外、技術断片）は変えていない
* 戦域を削除すると（`TheaterService.delete_theater()`）、その戦域のテーブルとエントリーも同じトランザクションで削除する

### 入手先の表示

* 図鑑の `obtainable_theaters` とショップの `unlock_hint` に戦域名を出す（「適用範囲から戦域の表示への変換」「ショップの入手ヒント」）
* 共通テーブルは、共通テーブルを使う有効な戦域があるときだけ入手先に出す
* 無効な戦域のテーブルは、現在は入手できないため入手先に出さない
* フロントエンドは API の文言をそのまま表示するため、変更していない

### admin-tool

* `/drop-tables` で、共通テーブルと各戦域のテーブルを選んで編集できる（`admin-drop-tables.md`）
* 戦域のテーブルが無い戦域は「共通テーブルを使用中」と表示する。保存すると戦域のテーブルを作成する。削除すると共通テーブルを使う状態に戻る

### 本番DBへの反映

* 戦域のテーブルの初期値は `seed_drop_tables.py` に追加した（「初期データ」）。本番DB（Neon）への投入は書き込みになるため、実行前に確認を取る
* 投入しなくても、全戦域が共通テーブルを使うため、これまでどおり抽選される

---

## 後続のSub-Issueで対応する事項

* 戦域のテーブルの本格的な初期値（戦域向けの機体の追加とあわせて決める。Epic #573 Sub-Issue 10）
* 戦場（フィールド）ごとの標準配備設定。現状はアイテム単位の真偽値のみ
