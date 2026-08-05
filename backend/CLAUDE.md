# CLAUDE.md 

このファイルは、Claude Code がこのリポジトリの`backend`ディレクトリで作業する際の規約・構造・判断基準を記述します。

## バックエンドの構造

```
backend/
├── app/
│   ├── engine/
│   │   ├── calculator.py   ← PilotStats dataclass・命中/ダメージ計算関数
│   │   └── combat.py       ← バトルシミュレーション本体
│   ├── models/
│   │   └── models.py       ← SQLModel の全テーブル定義（Pilot, MobileSuit など）
│   ├── routers/
│   │   └── pilots.py       ← パイロット登録・ステータス配分エンドポイント
│   └── services/
│       └── pilot_service.py ← パイロットビジネスロジック
├── alembic/
│   └── versions/           ← DBマイグレーションファイル
├── data/
│   └── master/
│       └── backgrounds.json ← 経歴マスタデータ（フロントエンドの同名ファイルと別管理）
├── tests/
│   ├── unit/               ← 単体テスト（DB不使用）
│   └── test_onboarding.py  ← パイロット登録の統合テスト
└── main.py                 ← WebSocket バトルセッション・PilotStats 構築
```

---

## パイロットステータス体系

### 現在のステータス一覧（Phase E-1 以降）

| キー | 名称 | 用途 |
|---|---|---|
| `sht` | 射撃精度 (SHT) | 射撃攻撃力補正率（シグモイド入力） |
| `mel` | 格闘技巧 (MEL) | 格闘攻撃力補正率（シグモイド入力） |
| `intel` | 直感 (INT) | クリティカル率・回避率 |
| `ref` | 反応 (REF) | イニシアチブ・機動性乗算 |
| `tou` | 耐久 (TOU) | ダメージ加算・被クリティカル率低下 |
| `luk` | 幸運 (LUK) | ダメージ乱数偏り・完全回避 |

**`dex` は廃止済み**（Phase E-1 で `sht`/`mel` に置換）。コード中に `dex` を書いてはいけない。

### PilotStats dataclass（`app/engine/calculator.py`）

```python
@dataclass
class PilotStats:
    sht: int = field(default=0)
    mel: int = field(default=0)
    intel: int = field(default=0)
    ref: int = field(default=0)
    tou: int = field(default=0)
    luk: int = field(default=0)
```

### combat.py での注意点

`calculate_hit_chance` / `calculate_damage_variance` は引数として `attacker_dex`/`defender_dex` を受け取るが、
`combat.py` では常に `0` を渡す（DEX廃止のため）。将来のリファクタリングに委ねている。

```python
attacker_dex = 0  # DEX は廃止（Phase E-1: SHT/MEL に置換）
```

---

## backgrounds.json の二重管理

**同名ファイルが2箇所に存在する。両方を必ず同期して更新すること。**

| パス | 用途 |
|---|---|
| `backend/data/master/backgrounds.json` | FastAPI ルーター（`pilots.py`）が読み込む |
| `frontend/src/data/backgrounds.json` | Next.js オンボーディングページが読み込む |

現在のベースステータスキー: `SHT`, `MEL`, `INT`, `REF`, `TOU`, `LUK`（`DEX` は存在しない）

---

## 武器データモデル（`player_weapons` / `MobileSuit.weapons`）

武器の所持・装備は `PlayerWeapon`（`player_weapons` テーブル、`models.py`）でインスタンス管理されている:

- `id`（UUID）/ `user_id` / `master_weapon_id`（`master_weapons` への論理FK）
- `base_snapshot`: 購入時点の `Weapon` スペックのスナップショット（JSON）
- `custom_stats`: 強化・改造による差分（`power_bonus` / `accuracy_bonus` / `upgrade_level`、スキーマは `WeaponCustomStats`）。`WeaponEngineeringService`（`app/services/weapon_engineering_service.py`、Issue #411）が改造ロジックを担い、`pilot.credits` を消費して段階強化する。上限は base値に対する倍率（`power_bonus` は200%、`accuracy_bonus` は130%）。実効スペックは `WeaponService.apply_effective_spec` で `base_snapshot + custom_stats` をマージして計算する
- `equipped_ms_id` / `equipped_slot`: 装備状態の正。`UniqueConstraint(equipped_ms_id, equipped_slot)` で1スロット1武器を担保

一方で `MobileSuit.weapons`（JSON列）は**バトルエンジンが直接参照するためのスナップショットのリスト**であり、装備操作のたびに `PlayerWeapon` の内容から書き込まれる（dual-write）。装備状態を問い合わせる/表示する処理は必ず `PlayerWeapon.equipped_ms_id`/`equipped_slot` を正として使うこと。装備中の武器を改造した場合は dual-write だけでは反映されないため、`WeaponService.resync_mobile_suit_weapons` がバトルエントリー登録時（`app/routers/entries.py`）に再同期している。

**`weapon_power`（機体強化）との関係**: `EngineeringService`（`app/services/engineering_service.py`）の `weapon_power` 強化項目は、`PlayerWeapon` インスタンス単位ではなく `MobileSuit.weapons` の**全スロットに一律加算**する実装（`_apply_weapon_power_upgrade`）のまま維持されている。武器を外す・付け替えると強化投資が失われるが、これは「機体側のパイロット/システム補正」として意図的に武器インスタンス単位の改造（`custom_stats`）とは別軸として維持する方針（Issue #404 で決定、方針(b)）。詳細は `docs/features/weapon-data-model.md` を参照。

## バトル結果の集計値（ダイジェスト等）は書き込み時に1回だけ計算する

`BattleResult` は `battle_logs.logs`（`BattleLogRecord.logs`, JSON列）というターンごとの生ログを別テーブルに持っているが、
「撃破数」「被弾ランク」「一言ログ」のような**集計・派生値を一覧表示のたびにJSONから再計算するのは避ける**。
唯一の `BattleResult` 生成箇所（`main.py` の `simulate_battle`）でログ確定後に一度だけ集計し、`BattleResult` の
非正規化カラムとして保存する（`app/engine/battle_digest.py` がこのパターンの実装例。Issue #415）。
既存レコードとの互換のため、追加カラムは nullable にしてバックフィルはしない方針で問題ない
（フロントエンド側で `null` 時のフォールバック表示を用意する）。

新たに `BattleResult` の生成箇所が増えた場合（マルチプレイ/ルーム戦など）は、集計ロジックを `main.py` に重複実装せず
`battle_digest.py` のような独立モジュールを呼び出す形にすること。

### 割合の閾値判定には `round()` を使わない

「HP20%未満なら辛勝」のような**閾値判定に使う割合**は `round()` で丸めると、`19.9%` が `20%` に繰り上がり
条件から漏れる、といった境界のズレが起きる（`battle_digest.py` の `min_hp_percent` で実際に発生し、Copilotレビューで指摘された）。
表示用の丸めと閾値判定用の丸めは別物と考え、閾値判定には `int()`（切り捨て）を使うこと。

### HPには回復要素がない

`app/engine/simulation.py`/`combat.py` にHP回復（repair）処理は存在しない。そのため「バトル中の最低到達HP」を
求めたいだけなら、ログを走査せずバトル終了時点の `current_hp` をそのまま使ってよい（`compute_digest_stats` 参照）。
将来 repair 系のスキル/機構を追加する場合はこの前提が崩れるため、`battle_digest.py` の集計ロジックも合わせて見直すこと。

## Neon DB（`NEON_DATABASE_URL`）はチーム共有のリモートDB

`backend/.env` の `NEON_DATABASE_URL` はローカル専用DBではなく共有のリモート（Neon）インスタンスを指している。
`alembic upgrade`/`downgrade` を含む「実DBへの書き込みを伴う操作」は、ユーザーに確認してから実行すること。
マイグレーションファイル自体の妥当性は `alembic heads`/`alembic history`（DB接続不要）や `python -m py_compile` で
静的に確認できるので、実DBに当てずに検証したい場合はそちらを使う。

## コーディング規約
`Agent.md` の `4. コーディング規約`を参照してください。

## テスト規約
`Agent.md` の `5. テスト方針`を参照してください。

### テストの実行
- テストを実行する際は、パイプ（例: `| tail`）を使用しないでください。
- 代わりに、pytestの `--tb=short` または `--tb=line` オプションを使用して出力の行数を制限してください。
- 例: `pytest --tb=short`

```bash
# テスト実行例 --tb=short を使用して出力を簡潔にする
cd backend && python -m pytest tests/unit --tb=short

# テスト実行例 --tb=line を使用してサマリーのみ表示する
cd backend && python -m pytest tests/unit --tb=line
``` 
