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
`BattleResult` 生成箇所でログ確定後に一度だけ集計し、`BattleResult` の非正規化カラムとして保存する
（`app/engine/battle_digest.py` がこのパターンの実装例。Issue #415）。
既存レコードとの互換のため、追加カラムは nullable にしてバックフィルはしない方針で問題ない
（フロントエンド側で `null` 時のフォールバック表示を用意する）。

### `BattleResult` の生成箇所は2つある（1つだと思い込まないこと）

`grep -rl "BattleResult(" backend --include="*.py"` で確認できる通り、`BattleResult` は以下**2箇所**で生成される。
どちらも独立した生成経路なので、片方だけ集計ロジックを追加するともう片方は永遠に `NULL` のままになる
（実際にIssue #415で `backend/main.py` にしか `battle_digest.py` の呼び出しを追加せず、本番の「デイリーバトルロイヤル」
（下記②のスケジュール実行バッチ）では一切ダイジェストが計算されない状態でリリースしてしまい、ユーザー報告で発覚した）。

1. `backend/main.py` の `simulate_battle`（`POST /api/battle/simulate`）: ユーザーが即座にプレイするソロミッション用
2. `backend/scripts/run_batch.py` の `_save_battle_results`: `.github/workflows/scheduled-battle.yaml` から `cron` で
   定期実行される「デイリーバトルロイヤル」等のルーム対戦バッチ用。こちらは複数プレイヤー分の `BattleResult` をループで
   1回のバッチ実行につき複数件生成する

新たに `BattleResult` の生成箇所を追加・変更する場合は、集計ロジック自体は `battle_digest.py` のような独立モジュールを
呼び出す形にして重複実装を避けつつ、**上記2箇所の両方**に確実に組み込むこと。①では `player`（`MobileSuit`）に
バトル後の最終状態がそのまま入っているが、②では `entry.mobile_suit_snapshot` から再構築した
`entry_unit_for_info` はエントリー時点（バトル前・満タンHP）のスナップショットで、`player_info`/`ms_snapshot` に
意図的にそのまま保存される設計になっている。ダイジェスト計算にはバトル後のHPが必要なため、`simulator` に渡した
（＝`simulator.step()` で実際に書き換えられる）`player_unit`/`enemy_units` 側からIDで対応するユニットを引くこと
（`live_units_by_id` 参照）。

生成箇所が2つに分かれているのは正しい設計（ソロ即時実行 vs バッチのルーム内複数プレイヤー処理はデータの形が違い、
無理に1つの関数へ統合するとかえって複雑になる）だが、**「直前の一言ログ取得 → 集計 → タグ・文言選出」というダイジェスト
計算のグルーコード部分は完全に同一処理**なので、そこは `app/services/battle_digest_service.py` の
`compute_battle_digest_fields()` に一本化してある。`main.py`/`run_batch.py` はどちらもこの関数を呼び、返り値の dict を
`BattleResult(..., **digest_fields)` のように展開するだけにすること。**ここを2箇所に再度コピペで書き戻さないこと**
（実際にIssue #415の初回実装でコピペしてしまい、片方の更新漏れバグを生んだ）。

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

### 直近バトル結果を実DBから確認したい場合

`backend/scripts/verify/fetch_recent_battles.py`（Issue #419）で `battle_results` の直近レコードを取得し、
コンソール表示 + JSON出力できる（読み取り専用）。使い方は `docs/features/balance-cli-tools.md` を参照。
出力先 `backend/scripts/verify/output/` は `.gitignore` 対象なので、取得した実データがコミットされる心配はない。

## `BattleLog` の `velocity_snapshot` は `DESTROYED` ログに含まれない

`combat.py`/`movement.py` の各 `BattleLog` 生成箇所はほぼ毎ティック `velocity_snapshot`（行動時点の速度ベクトル）を
付与しているが、`_process_destruction`（`combat.py`、撃破処理）が出す `action_type="DESTROYED"` のログだけは
`velocity_snapshot` を持たない。フロントエンド（`useBattleSnapshot.ts`）はログ間の位置を
`直近position_snapshot + velocity_snapshot × dt` で外挿して滑らかに表示しているため、撃破後は最後の生存時点の
速度ベクトルのまま `dt` が伸び続け、実位置から大きくズレた位置に外挿されてしまう不具合が実際に発生した
（BattleViewerの照準線が無関係な方向を指す。Issue #421、フロントエンド側で `dt` に上限を設けて対応）。
`BattleLog` の生成箇所を新たに追加・変更する場合、この非対称性（`DESTROYED` だけ `velocity_snapshot` が無い）を
踏まえてフロントエンド側の外挿・補間ロジックに影響しないか確認すること。

## スポーン領域の「チーム間距離保証」は sensor_range のデフォルト値ではなく実測値で判定すること

Phase 6-3（`docs/features/battle-engine-feature.md` §14, §21）のデフォルトスポーン領域は、当初
「`sensor_range` のデフォルト値(500m)×2=1000m」という**固定値**でチーム間の中心間距離を保証する設計だった。
これは (a) 実際に参加するユニットの `sensor_range`（NPCエースは最大900m）を見ておらず、(b) 中心間距離であって
スポーン領域の `radius` を差し引いた「縁と縁の距離」ではなかったため、Phase 6-5 のフィールドスケーリング
（`AREA_PER_UNIT` 由来の面積が `MIN_FIELD_SIZE=2000m` にクランプされるユニット数が少ない戦闘、
特に最も頻度の高い1vs1ソロミッション）と組み合わさると、スポーン直後から索敵が成立してしまうケースが
実際にあった。`BattleSimulator.__init__()` で `self.units` の実際の `sensor_range` の最大値
（+ `SPAWN_DETECTION_SAFETY_MARGIN`）を見てフィールドサイズを動的拡張するよう修正した
（`_min_field_size_for_team_layout()`、`app/engine/simulation.py`）。

**今後スポーン・索敵まわりを変更する際の注意**: 「距離が◯m以上あれば安全」という類のガードを書くときは、
必ず (1) ハードコードしたデフォルト値ではなく実際にバトルへ渡された値（`sensor_range` 等）を参照すること、
(2) 円形領域を扱う場合は中心間距離ではなく `radius` を差し引いた縁と縁の距離で判定すること、の2点を確認する。
将来 `sensor_range` を強化できるスキル/改造要素を追加する場合は、この安全マージン計算がその強化後の値も
カバーできているか見直すこと（現状は改造不可のため base 値がそのまま実効値）。

**さらにPRレビュー(Copilot)で指摘された第3の落とし穴**: 上記の必要フィールドサイズは対称配置（対角・
均等分割・円周配置）の**理想座標**から逆算しているが、障害物が生成される場合は実際のスポーン中心が
`_find_clear_spawn_center()`（#437）により最大 `SPAWN_CENTER_JITTER_RADIUS`（300m）だけジッターしうる。
異チームの2ゾーンが互いに近づく向きへジッターする最悪ケースを見込んで `required_separation` に
`2 × SPAWN_CENTER_JITTER_RADIUS` を追加で上乗せしないと、障害物ありの戦闘でだけ保証が崩れる
（`obstacle_density="NONE"` のテストだけでは検出できない）。円形配置の間隔保証を書く際は、
「理想幾何での距離」と「実際にサンプリング/ジッターされた後の距離」が別物であることを常に意識すること。

## 索敵・ターゲット選定処理のO(N²)対策（Issue #446）と、その先の真のボトルネック

`app/engine/targeting.py` の `_detection_phase()`（索敵）と `_select_target_legacy`/
`_select_target_fuzzy`（ターゲット選定）は元々、行動ユニットごとに敵ユニット全体を
線形走査する実装（O(N²)）だった。`app/engine/spatial_grid.py` の `UnitSpatialGrid`
（セル分割による近傍探索。セル幅 ≥ 探索半径なら3x3x3近傍セルの走査だけで漏れなく
候補を捕捉できる、という性質を利用）を使い、未発見の敵候補の索敵判定は近傍セルのみに
絞り込むようにした。ターゲット選定側は `self.units`（両陣営全体）を毎回フィルタする
代わりに、索敵フェーズが絞り込んだ `team_detected_units` を `TargetingMixin._get_detected_targets()`
で直接再利用する。

**`team_detected_units` はユニット単位ではなくチーム単位で共有される状態**（
`dict[team_id, set[unit_id]]`）である点に注意。同じチームの複数ユニットが同じ
発見済みセットを参照するため、索敵・ターゲット選定まわりを変更する際は「あるユニットが
発見した」ではなく「そのチームが発見した」という単位で状態を扱っていることを踏まえること。

**既発見済みユニットのLOS再チェックは索敵範囲・距離に関わらず毎ステップ行う仕様**であり
（障害物の陰に入った場合に発見済みリストから除外するため）、グリッドによる近傍絞り込みの
対象外。既発見済みセットのサイズは理論上チームの敵人数まで増加しうるため、この経路は
グリッド化後も O(検出済み数) のコストが残る。これは意図的な仕様（`tests/unit/test_los_obstacle.py`
で担保）であり、「距離が離れたらスキップする」といった最適化を安易に入れてはいけない。

**`room_size=50/100` 規模で実際に支配的なのは候補列挙のO(N²)ではなく、`_select_target_fuzzy`
のファジィ推論コスト**（Issue #446 対応時に `cProfile` で確認）。`_select_target_fuzzy` は
1ユニット・1ステップあたり最大3回呼ばれる（`ai_decision.py` から2回、`action_handler.py`
から1回）うえ、索敵済み候補1件ごとに `FuzzyEngine.infer_with_debug()`（重心デファジィフィケーション）
を実行するため、索敵済み候補数が増えるほど無視できないコストになる。今後さらに大規模
（100機超）なバトルの体感速度が問題になる場合は、まずここ（重複呼び出しの排除・
ファジィ推論結果のステップ内キャッシュ）を疑うこと。`app/engine/movement.py` の
ポテンシャルフィールド計算（味方斥力など）も `self.units` を毎ユニット線形走査しており、
同種のO(N²)を抱えているため、`UnitSpatialGrid` パターンの適用候補になる。

`combat.py` の `has_los()`（3D Ray-Sphere交差判定）は障害物リストへの線形走査だが、
計算量はユニット数Nではなく障害物数に依存するため、ユニット数起因のO(N²)対策の対象外。

計測用に `backend/scripts/simulation/sim_scale_bench.py`（DB不要、合成ユニットで
`BattleSimulator.step()` の平均処理時間を計測）を用意した。

**`UnitSpatialGrid` のセルサイズは「その戦闘の生存ユニット中の最大索敵範囲」を使っており、
索敵範囲が個々のユニットで異なっていても取りこぼしは発生しない**（`max(u.sensor_range * sensor_multiplier for u in alive_units)`
をセル幅にするため、どのユニットの実効索敵範囲もセル幅以下になり、3x3x3近傍探索の
「セル幅 ≥ 探索半径なら漏れなく捕捉できる」という前提を常に満たす）。ただし裏を返すと、
一部のユニットだけ突出して索敵範囲が広い場合（将来的なレーダー特化機体などで
sensor_range が現状のNPCエース最大値 900m を大きく超える設計を入れる場合）、セルサイズが
その外れ値に引っ張られて全体が大きくなり、近傍探索で拾う候補数が増えて最適化効果が
薄れる。索敵範囲に大きな幅を持つユニット種別を追加する場合は、範囲帯でグリッドを分ける
などの見直しを検討すること。

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
