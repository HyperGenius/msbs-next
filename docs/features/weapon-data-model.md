# 武器データモデル（`master_weapons` / `player_weapons` / 改造差分）

## 概要

武器改造（強化）機能の実装に向けて、武器データモデルの整理を行った（Issue #404）。
`PlayerWeapon.custom_stats` は以前から `player_weapons` テーブルの予約フィールドとして存在していたが、書き込み・読み取りロジックが一切なく常に空 `{}` だった。本Issueで `custom_stats` のスキーマを定義し、`base_snapshot + custom_stats` をマージして実効スペックを計算するロジックを実装した。

本Issueは**データモデル整理が主目的**であり、UI（改造画面）の実装は別Issueに切り出す。

---

## テーブル構成

```
master_weapons (マスター武器定義)
├── id: str                   ← スネークケースID (例: zaku_mg)
├── name / price / description
└── weapon: JSON               ← Weapon スペック本体

player_weapons (プレイヤー武器インスタンス)
├── id: UUID
├── user_id: str                ← 所有者
├── master_weapon_id: str       ← master_weapons への論理FK
├── base_snapshot: JSON         ← 購入時の Weapon スペックスナップショット
├── custom_stats: JSON          ← 強化・改造による差分（本Issueでスキーマ定義）
├── equipped_ms_id / equipped_slot ← 装備状態の正
└── acquired_at: datetime
```

`MobileSuit.weapons`（JSON列）はバトルエンジンが直接参照するためのスナップショットであり、装備操作のたびに `PlayerWeapon` の内容（`base_snapshot + custom_stats` のマージ結果）が dual-write される。装備状態やスペックの問い合わせは常に `PlayerWeapon` 側を正として使うこと。

---

## `weapon_power`（機体強化）と武器改造の関係 — 方針(b)を採用

既存の機体強化機能 `EngineeringService` には `weapon_power` という強化項目があり、装備中の**全武器**の `MobileSuit.weapons[*].power` に一律加算する実装になっている（`_apply_weapon_power_upgrade`）。これは武器インスタンス単位ではなく機体のJSONスナップショットに乗っているため、武器を外す・付け替えると強化投資が失われるという既知の制約がある。

本Issueでは、以下の理由から **`weapon_power` を武器インスタンス単位の `custom_stats` へ統合しない（方針(b)）** ことを決定した:

- 過去に武器を付け替えたプレイヤーは、その時点で強化投資が既に失われている。現在の `MobileSuit.weapons[*].power` と `PlayerWeapon.base_snapshot` の差分は「現在装備中の武器」についてしか計算できず、正確な移行スクリプトを書けない
- 既存データを破壊せずに済む安全な選択肢を優先した

そのため `weapon_power` は「機体側のパイロット/システム補正」として用途を再定義し、`EngineeringService` の実装はそのまま維持する。武器インスタンス単位の改造（`custom_stats`）とは別軸の強化として、コード上のコメント・将来のUIコピーで明確に区別する（`EngineeringService` docstring 参照）。

この決定に伴い、**Alembic マイグレーションは本Issueでは不要**（`custom_stats` は既存カラムで、スキーマ変更を伴わない）。

---

## `custom_stats` スキーマ

`app/models/models.py` の `WeaponCustomStats`（`SQLModel`、テーブル定義ではなくスキーマ定義用）:

| キー | 型 | デフォルト | 説明 |
|---|---|---|---|
| `power_bonus` | `int` | `0` | 威力への加算値 |
| `accuracy_bonus` | `float` | `0.0` | 命中率への加算値(%) |
| `upgrade_level` | `int` | `0` | 改造レベル（将来の改造ツリー・表示用、現状は算出に使用しない） |

`custom_stats` カラム自体は引き続き自由形式の `dict`（JSON）。キー欠損時は `WeaponCustomStats` のデフォルト値（0/未変更）として扱われるため、既存の空 `{}` の行も安全にマージできる。

---

## 実効スペックのマージ

`app/services/weapon_service.py` の `WeaponService.apply_effective_spec(base_snapshot, custom_stats) -> Weapon`:

```python
diff = WeaponCustomStats(**custom_stats)
merged = dict(base_snapshot)
merged["power"] = merged.get("power", 0) + diff.power_bonus
merged["accuracy"] = merged.get("accuracy", 0.0) + diff.accuracy_bonus
return Weapon(**merged)
```

`WeaponService.equip_weapon` は装備時、`MobileSuit.weapons` に書き込む値としてこのマージ結果を使用する（`base_snapshot` をそのまま書き込んでいた従来の実装から変更）。これにより、将来 `custom_stats` に改造差分が書き込まれるようになれば、装備し直すだけでバトルエンジン側にも反映される。

現時点では `custom_stats` を書き込むAPI・UIは未実装のため、常に空 `{}` として扱われ、実質的な挙動は変化しない。

---

## 関連ファイル

- `backend/app/models/models.py` — `WeaponCustomStats`、`PlayerWeapon.custom_stats` の docstring 更新
- `backend/app/services/weapon_service.py` — `apply_effective_spec` 追加、`equip_weapon` を更新
- `backend/app/services/engineering_service.py` — `weapon_power` の位置づけをdocstringで明記
- `backend/tests/unit/test_weapon_custom_stats.py` — マージロジックのユニットテスト
- `backend/tests/test_weapon_shop.py` — 装備フローで改造差分が反映されることのテスト（`test_equip_weapon_reflects_custom_stats_bonus_in_mobile_suit_weapons`）
- `frontend/src/types/shop.ts` — `WeaponCustomStats` 型、`PlayerWeapon.custom_stats` の型を具体化

---

## 武器改造機能（Issue #411）

`custom_stats`（`power_bonus` / `accuracy_bonus`）を実際に読み書きする改造ロジック・APIを実装した。UI（改造画面）は本Issueの対象外で別Issueに切り出す。

### `WeaponEngineeringService`（`app/services/weapon_engineering_service.py`）

`EngineeringService`（機体強化）と同様に、サーバーサイドで段階コスト計算・上限キャップ検証を行い `pilot.credits` を消費する。対象は `PlayerWeapon` インスタンス単位で、**未装備の武器も改造可能**（`weapon_power` と異なり、改造投資は武器を外しても失われない）。

- `power_bonus`: 1ステップ +5、コスト `int(60 * (1 + current_bonus / 30))`
- `accuracy_bonus`: 1ステップ +1.0、コスト `int(100 * (1 + current_bonus / 5))`
- 上限キャップは **base値（`base_snapshot`）に対する倍率**で表現する（絶対値キャップの `weapon_power` とは計算方法が異なる点に注意）:
  - `power_bonus`: 実効値（`base.power + power_bonus`）が `base.power` の **200%** に達するまで
  - `accuracy_bonus`: 実効値が `base.accuracy` の **130%** に達するまで
- 改造回数の上限はなし（キャップまで何度でも改造可能）。失敗要素・改造のリセット機能はなし

### APIエンドポイント（`app/routers/player_weapons.py`）

- `POST /api/player-weapons/{pw_id}/upgrade` — `{ target_stat, steps }` を受け取り改造を実行
- `GET /api/player-weapons/{pw_id}/upgrade-preview/{stat_type}` — 次の1ステップのコスト・変化後の値をプレビュー

### バトルへの反映（装備中武器を改造した場合）

装備時の dual-write（`equip_weapon`）だけでは、装備中の武器を後から改造しても `MobileSuit.weapons` に反映されない。これを解消するため `WeaponService.resync_mobile_suit_weapons(session, mobile_suit)` を新設し、バトルエントリー登録時（`app/routers/entries.py` の `create_entry`、機体スナップショットを保存する直前）に呼び出すことで、**再装備しなくてもバトル開始前に改造差分が反映される**。

### フロントエンド

- `frontend/src/types/shop.ts`: `WeaponUpgradeRequest` / `WeaponUpgradeResponse` / `WeaponUpgradePreview` 型を追加
- `frontend/src/services/weaponEngineering.ts`: `upgradePlayerWeapon` / `getWeaponUpgradePreview`（`services/upgrades.ts` と同型のAPIクライアント）。UIからの呼び出しは別Issueで実装

## 今後の拡張（別Issue）

- 武器改造UI（Garage/Engineering画面への統合、コスト・プレビュー表示）
- `docs/features/garage-weapon-inventory.md` の所持武器一覧に改造状態（`custom_stats` 由来の差分）を表示する拡張
- 改造の種類・コスト体系をマスターデータ化するかどうかの検討（現状は対象外）

---

## テスト

```bash
cd backend && python -m pytest tests/unit/test_weapon_custom_stats.py tests/test_weapon_shop.py tests/test_weapon_engineering.py --tb=short
cd frontend && ./node_modules/.bin/tsc --noEmit
cd frontend && npx vitest run tests/unit/weaponEngineeringService.test.ts
```
