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
のファジィ推論コスト**（Issue #446 対応時に `cProfile` で確認。Issue #450 対応時に
`room_size=50/100` で再計測し、`FuzzyEngine._clip_and_combine()`/`evaluate()` 系が
`step()` 全体の 80〜90% を占めることを改めて確認済み）。`_select_target_fuzzy` は
1ユニット・1ステップあたり最大3回呼ばれる（`ai_decision.py` から2回、`action_handler.py`
から1回）うえ、索敵済み候補1件ごとに `FuzzyEngine.infer_with_debug()`（重心デファジィフィケーション）
を実行するため、索敵済み候補数が増えるほど無視できないコストになる。この重複呼び出しの
排除・ファジィ推論結果のステップ内キャッシュは Issue #454 でスコープ化した
（本Issueのポテンシャルフィールド最適化とは独立した対応）。`app/engine/movement.py` の
ポテンシャルフィールド計算（味方斥力・最近敵引力）は Issue #450 で `UnitSpatialGrid` を
使ったグリッド化を行ったが、上記の通り `room_size=50/100` 規模では体感できるほどの
改善にはならない（ボトルネックが別にあるため）。詳細は下記「ポテンシャルフィールド計算の
O(N²)対策（Issue #450）」を参照。

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

## スポーン位置サンプリングの準O(N²)対策（Issue #447）

`app/engine/simulation.py` の `_sample_position_in_zone()`（ゾーン内でユニット配置位置を
サンプリングし、既配置ユニットとの `min_dist` を満たすまでリサンプリングする）は、
配置済みユニットが増えるほど1回のサンプリングあたりの距離判定コストが線形に増える
準O(N²)構造だった。`UnitSpatialGrid`（Issue #446 のセル分割near-neighborパターン）をそのまま使わず、
`app/engine/spatial_grid.py` に `PointSpatialGrid` を新設した
理由は、`UnitSpatialGrid` が「全ユニットが揃った状態で一括構築・以降は読み取り専用」という
索敵フェーズの前提を持つのに対し、スポーン配置は「1体ずつ配置しながら都度既配置点を
追加していく」逐次構築が必要なため。**近傍探索を伴う既存構造体を流用できないか検討する際は、
「一括構築 vs 逐次構築」というアクセスパターンの違いをまず確認すること**（同じ「セル幅 ≥
探索半径なら3x3x3近傍セル走査で漏れなく捕捉できる」という性質は共通して使えるが、
クラス自体は別に用意する必要があった）。

`_sample_position_in_zone()` は `current_min_dist` を試行のたびに段階的に緩和する仕様
（`SPAWN_ZONE_MIN_DIST_RELAXATION_FACTOR`）があるため、`PointSpatialGrid` のセルサイズは
緩和前の最大値（`ALLY_REPULSION_RADIUS`）で固定して構築している。セルサイズが緩和後の
`current_min_dist` を常に上回っていれば近傍セル探索の正しさは崩れないため、緩和のたびに
グリッドを再構築する必要はない。

計測用に `backend/scripts/simulation/spawn_scale_bench.py`（DB不要、合成ユニットで
`BattleSimulator` 初期化＝スポーン処理の平均処理時間を計測、`--obstacle-density` で
障害物密度を切り替え可能）を用意した。

## ポテンシャルフィールド計算のO(N²)対策（Issue #450）

`app/engine/movement.py` の `_calculate_potential_field()`（行動ユニットごとに毎ステップ
呼ばれる）が内部で呼ぶ `_ally_repulsion()` / `_closest_enemy_attraction()` は、Issue #446/#447
と同種の `self.units` 線形走査（O(N²)）を抱えていた。`_threat_enemy_repulsion()` を除く
この2関数を `UnitSpatialGrid` ベースに書き換えた。

### `_ally_repulsion()`: 固定半径カットオフなので3x3x3近傍探索で完結

`ALLY_REPULSION_RADIUS`（150m固定）というカットオフが既にあるため、セルサイズを
`ALLY_REPULSION_RADIUS` にした `UnitSpatialGrid.neighbors()`（3x3x3近傍走査）にそのまま
置き換えられる。挙動が変わるリスクは低い。

### `_closest_enemy_attraction()`: グローバル最近傍が必要なので環状探索を新設

MOVE行動時に「最も近い敵」という**グローバルな**最近傍を求める必要があるため、
`neighbors()` の固定3x3x3走査だけでは不十分（近傍セルに敵が一体もいない場合、本来の
最近敵を見逃してしまう）。そのため `UnitSpatialGrid.nearest(pos, predicate)` を新設し、
近傍セルに候補がいない場合は探索半径（セル単位）を1段ずつ外側へ広げる環状探索を実装した。
ある半径 `r` まで走査を終えた時点で見つかっている最小距離が `r * cell_size` 以下なら、
未走査のセルにそれより近い候補は存在し得ない（`UnitSpatialGrid` 自体の前提「セル幅 ≥
探索半径なら3x3x3近傍走査で漏れなく捕捉できる」を任意半径に一般化した性質）ため、その
時点で打ち切って良い。`tests/unit/test_spatial_grid.py` の
`test_nearest_matches_brute_force_over_random_layout` で、ランダム配置に対して
`nearest()` の結果がO(N)総当たりの結果と厳密に一致することを検証している。

**殻（半径 `r` の外周セルのみ）を直接列挙しないと簡単にO(r³)に退化する**ことが実装時に
判明した実装上の罠: 「半径 `r` の立方体全体を毎回ループし、`max(|dx|,|dy|,|dz)==r` で
フィルタする」実装は一見自然だが、ループ自体のコストが立方体の体積 O(r³) に比例してしまい、
半径が伸びるケース（近傍セルに敵が全くおらず遠方まで探す必要がある場合）で無駄な走査が
急増する。`_shell_offsets()`（`spatial_grid.py`）で殻の外周セルだけを直接 O(r²) で
生成するように修正した。`sim_scale_bench.py --sizes 8` でこの罠を仕込んだ実装のまま
計測したところ、8機構成ですら数十msかかっており（本来ミリ秒未満で終わるはずの規模）、
シェル走査の実装ミスは規模の大小に関わらず致命的に遅くなりうることを示す実例になった。
グリッド系の近傍探索・環状探索を新規実装する際は、「殻だけを直接生成できているか」
（立方体全体を舐めてフィルタしていないか）を必ず確認すること。

### `_threat_enemy_repulsion()` は対象外（挙動を変えずには最適化できない） → Issue #453 で対応済み

`_threat_enemy_repulsion()` の斥力式 `1.5 * (-vec_to_enemy) / max(dist, 1.0)` は、
`vec_to_enemy` の大きさが `dist` に等しいため、`dist >= 1.0` の範囲では距離によらず
ほぼ一定の大きさ（正規化ベクトル）になる、つまり**実質的に距離減衰がない**設計になっている
（コメント上は「減衰しつつも」と書かれているが実装は違う）。そのため近傍セルへの
絞り込みや遠方の早期打ち切りは、遠方の高脅威敵からの斥力を消してしまい挙動を変える。
`_ally_repulsion`/`_closest_enemy_attraction` と異なり挙動変更なしには最適化できないため
Issue #450 のスコープ外とし、挙動変更を許容した上での対応はIssue #453に切り出した
（下記「高脅威敵斥力の距離減衰導入とO(N²)対策（Issue #453）」で対応済み）。

## 高脅威敵斥力の距離減衰導入とO(N²)対策（Issue #453）

`_threat_enemy_repulsion()` に `THREAT_REPULSION_DECAY_SCALE`（既定300m、
`app/engine/constants.py`）を基準とした距離減衰を導入した:
`dist <= THREAT_REPULSION_DECAY_SCALE` では従来どおり一定の斥力
（`THREAT_ENEMY_REPULSION_COEFF`=1.5）を維持し、それより遠いと
`THREAT_ENEMY_REPULSION_COEFF * (THREAT_REPULSION_DECAY_SCALE / dist) ** 2` で
1/dist^2 減衰する。300mという基準値は典型的な武器射程の下限帯に合わせたもので、
実戦闘で頻出する交戦距離帯（数百m）では挙動をほぼ変えず、無限遠まで一定という
非現実的な部分だけを是正する設計。

早期打ち切り半径 `THREAT_REPULSION_CUTOFF_RADIUS`（既定 `300 * sqrt(20)` ≈ 1342m）は、
斥力の大きさが基準係数の5%未満まで減衰する距離を基準に設定した。**減衰の指数を
1乗（1/dist）ではなく2乗（1/dist^2）にしているのは、同じ5%基準でもカットオフ半径を
大幅に小さくするため。** 1乗減衰だと同基準での打ち切り半径は
`20 * THREAT_REPULSION_DECAY_SCALE = 6000m` になり、`room_size=50/100` の
フィールド辺長（最大 `MAX_FIELD_SIZE=8000m`）とほぼ同スケールになってしまう
（初期実装でこの問題が発生し、PR #456 の Copilot レビューで指摘された。後述）。

この半径での近傍探索には `UnitSpatialGrid.radius_neighbors()`（Issue #453 で新設、
`app/engine/spatial_grid.py`）を使う専用グリッド（`MovementMixin._get_threat_repulsion_grid()`）
を新設し、`_ally_repulsion()` 用の `_get_movement_grid()`（セルサイズ=
`ALLY_REPULSION_RADIUS`=150m）とは別に保持している（カットオフ半径の前提が大きく
異なるグリッドを共有すると近傍探索の正しさが崩れるため。上述「索敵・ターゲット選定
処理のO(N²)対策」の索敵グリッドに関する注意書きと同じ理由）。

#### 初期実装の罠: セルサイズ=カットオフ半径にすると絞り込みが効かない（Copilot指摘）

初期実装では `UnitSpatialGrid` のセルサイズをカットオフ半径そのもの（当時6000m）に
設定し、既存の `neighbors()`（3x3x3固定走査）で候補を絞り込んでいた。しかし
`MAX_FIELD_SIZE=8000m` に対してセルサイズ6000mは大きすぎ、フィールド全体が
わずか1〜2セルに収まってしまうため、3x3x3走査が実質的に全ユニットを返す退化が
起きていた（見た目はグリッド化されているが、実態は各ユニットごとに全ユニットを
走査するのとほぼ同じでO(N^2)のままだった）。この点はPR #456 の Copilot レビューで
指摘され、以下のように修正した:

1. 減衰指数を1乗→2乗にして、同じ「基準係数の5%未満」という打ち切り基準でも
   カットオフ半径を6000m→約1342mへ大幅に縮小
2. `UnitSpatialGrid` に `radius_neighbors(pos, radius)` を新設し、セルサイズは
   `THREAT_REPULSION_DECAY_SCALE`（300m）という小さい値に固定したまま、
   `nearest()` と同じ殻走査（`_shell_offsets()`）でカットオフ半径まで動的に
   走査範囲を広げる方式に変更（セルサイズを探索したい距離に合わせて大きくする
   のではなく、セルサイズは小さく保ったまま走査半径（セル単位）だけを可変にする、
   という発想の転換）

**グリッド系の近傍探索を新規実装する際は、「セルサイズを探索したい最大距離に
合わせる」という直感的なアプローチが、その距離がフィールドサイズに対して
大きい場合に容易に退化することを踏まえること。** セルサイズは索敵グリッド
（Issue #446）やALLY_REPULSION_RADIUSグリッド（Issue #450）のように「実際に
細かく分割できる小さな値」に固定し、探索したい半径が大きい場合は
`nearest()`/`radius_neighbors()` のような殻走査で対応するのが正しいパターン。

### ゲームバランスへの影響（`sim_bench.BenchRunner` 実測）

8機（4vs4）バトルを2つの乱数シードで実行し、導入前後を比較した:

| seed | ラウンド数 | 導入前 win_counts | 導入後 win_counts | 導入前 平均戦闘時間 | 導入後 平均戦闘時間 |
|---|---|---|---|---|---|
| 453 | 50 | PLAYER 1 / ENEMY 49 / DRAW 0 | PLAYER 18 / ENEMY 30 / DRAW 2 | 54.98s | 25.01s |
| 123 | 20 | PLAYER 0 / ENEMY 20 / DRAW 0 | PLAYER 0 / ENEMY 20 / DRAW 0 | 15.14s | 14.80s |

seed=123 はユニット性能差自体で一方的な結果になる組み合わせで、斥力式の変更による
差はほぼ無かった。一方 seed=453 では導入前は弱い側が「射程外の高脅威敵から
無限遠まで一定の力で逃げ続ける」ため戦闘に参加できず一方的に負け続けていたが、
導入後は逃げの強制力が現実的な距離帯に収まり、勝率の偏りが大幅に緩和され
（1-49→18-30-2）、平均戦闘時間もほぼ半減した（55s→25s）。**この変更は単なる
最適化ではなく、旧実装の「非減衰・無限遠まで一定」という設計自体が組み合わせ次第で
一方的な不均衡を生む要因になっていたことを示している**（2乗減衰への変更前は
25-23-2とさらに互角に近い結果だったが、カットオフ半径を現実的な大きさに縮める
ため2乗減衰へ変更した結果、遠距離での減衰がやや強くなり分布はやや偏りが戻った。
それでも導入前の1-49と比べれば明確な改善）。今後この関数の斥力式・減衰基準を
調整する場合は、単一シードの結果だけで判断せず複数シードで比較すること
（組み合わせ依存でほぼ差が出ないケースがあるため）。

### パフォーマンスへの影響（`sim_scale_bench.py` 実測）

`sim_scale_bench.py --sizes 8,50,100 --steps 50` の結果（導入前 → 導入後）:

| room_size | 導入前 (sec/step) | 導入後 (sec/step) |
|---|---|---|
| 8   | 0.0160 | 0.0239 |
| 50  | 0.1982 | 0.2220 |
| 100 | 1.3269 | 1.4487 |

Issue #450 と同様、絶対値としてはやや増加している（`radius_neighbors()` の殻走査は
セルサイズを小さく保つ代償として、候補が実際には少ない場合でも走査半径分のセルを
律儀に辿るための固定オーバーヘッドを持つため）。ただし `_select_target_fuzzy` の
ファジィ推論コストが `room_size=50/100` の80〜90%を占めるという既知の支配的
ボトルネック（上述「索敵・ターゲット選定処理のO(N²)対策」参照）を踏まえると、
この増分（10〜20%程度）はステップ全体で見れば無視できる範囲であり、本Issueの
主目的（無限遠まで一定という非現実的な挙動の解消とその代償として発生しうる
O(N^2)の実質的な解消）は達成できている。真のO(N^2)解消効果はユニット密度が
高い・カットオフ半径内の候補数が多いケースで顕在化するため、本ベンチの
均一分散配置では体感しにくい。

### グリッドは1ステップに1回だけ構築してキャッシュする

`_calculate_potential_field()` は行動ユニットごとに呼ばれるため、`BattleSimulator._movement_grid`
（`MovementMixin._get_movement_grid()`）でグリッドを遅延構築・キャッシュし、同一ステップ内の
呼び出しでは使い回す。`step()` の冒頭で毎ステップ `self._movement_grid = None` にリセットする
ことで次のステップでは最新位置から再構築させる（索敵フェーズの `UnitSpatialGrid` を毎ステップ
使い捨てで再構築しているのと同じ設計）。

**この「1ステップに1回だけ構築」は、同一ステップ内で先に行動したユニットの移動後の位置が
グリッドに反映されないという意味で、最適化前の「毎回 `self.units` を線形走査（＝常に最新位置）」
とは厳密には異なる。** ただし1ステップの移動量（`max_speed * dt`）はセルサイズ
（`ALLY_REPULSION_RADIUS`=150m）よりはるかに小さいため、実際にセル境界をまたぐケースは
稀であり、8機バトルの `sim_bench.BenchRunner`（150ラウンド、完全ランダム）による比較でも
勝敗分布・行動分布に有意な差は確認されなかった（Issue #450 のPR参照）。

### ベンチマーク

`sim_scale_bench.py --sizes 8,50,100 --steps 50` の結果（最適化前 → 最適化後）:

| room_size | 最適化前 (sec/step) | 最適化後 (sec/step) |
|---|---|---|
| 8   | 0.0012 | 0.0164 |
| 50  | 0.2129 | 0.1973 |
| 100 | 1.4266 | 1.4360 |

`room_size=50/100`（本Issueが本来狙うスケール）では改善というよりノイズの範囲内で
横ばい——上述の通りこのスケールで支配的なのはファジィ推論コストであり、本Issueの
最適化は補助的な位置づけであることを裏付けている。一方 `room_size=8` は最適化前の
O(N)総当たり（N=8なら数マイクロ秒オーダー）と比べるとグリッド構築・環状探索の
定数コストの方が相対的に重くなり、絶対値としては遅くなる（0.0012s→0.0164s）。
ただしこれは1ステップあたり十数msというオーダーの絶対値であり、実運用（最大数百
ステップ程度のバトル）では体感できるレベルの遅延にはならない。

## ターゲット選定のファジィ推論コスト削減（Issue #454）

Issue #446〜#453 で候補列挙のO(N²)構造を解消した後も、`room_size=50/100` 規模では
`cProfile` 上で `BattleSimulator.step()` の80〜90%を `FuzzyEngine` の推論処理
（`infer_with_debug()` / `_centroid_for_variable()`）が占めていた。この真のボトルネックに
対応したのが本Issue。詳細な調査経緯・実測値は `docs/features/battle-engine-feature.md`
26章を参照。要点は以下の2点:

1. **`_select_target_fuzzy()`（`app/engine/targeting.py`）はステップ内キャッシュ可能**:
   1ユニット・1ステップあたり最大3回（`ai_decision.py` から2回、`action_handler.py`
   から1回）呼ばれるが、`step()` のフェーズ構成を調べた結果、呼び出し1・2の間
   （AI意思決定フェーズ・胴体向き更新フェーズ）ではHP・位置・武器クールダウンいずれも
   変化しない一方、呼び出し3（行動フェーズ）は同一ステップ内で先行するユニットの攻撃・
   移動が後続ユニットの候補に影響しうる。そのため `unit_id → (計算時点の _step_count,
   選択結果)` のキャッシュを導入しつつ、**キャッシュ対象のターゲットが撃破されていた
   場合は無条件で再計算する**という無効化条件を入れた。「呼び出しの間で状態が変わり
   うるかを先に調査してからキャッシュ方針を決める」という進め方は、本Issueに限らず
   ステップ内で複数回呼ばれる関数をキャッシュ化する際に踏襲すべき手順。

2. **`FuzzyEngine._centroid_for_variable()`（`app/engine/fuzzy_engine.py`）の重心
   デファジフィケーションは numpy でベクトル化してホットパス自体を高速化した**:
   「200点の数値積分 × 発火中の集合数」という Python ネストループ自体が支配的コストで
   あり、`infer()`/`infer_with_debug()` の呼び分け（デバッグ情報構築の回避）では
   ほとんど効果がないことを確認した（両者は内部で同じ `_fuzzify()`/`_evaluate_rules()`/
   `_defuzzify_centroid()` を呼んでおり、差は返り値に `fuzzified`/`activations` の
   参照を含めるかだけで、追加のコピーは発生しないため）。`MembershipFunction` に
   `evaluate_array()`（numpy配列を受け取るベクトル化版の `evaluate()`）を追加し、
   `_centroid_for_variable()` 内のサンプル点ループを numpy 配列演算に置き換えた。
   **「ループ回数を減らす」だけでなく「どのループが実際に高コストか cProfile で
   特定してからそこだけを最適化する」ことが重要**（本Issueでは `infer()`/
   `infer_with_debug()` の分離は直感的には効きそうに見えたが実際はほぼノーコストで、
   数値積分のベクトル化が真の対策だった）。

`sim_scale_bench.py --sizes 8,50,100 --steps 50` 実測（Issue #453時点 → 本Issue後）:

| room_size | 対応前 (sec/step) | 対応後 (sec/step) |
|---|---|---|
| 8   | 0.0239 | 0.0177 |
| 50  | 0.2220 | 0.0449 |
| 100 | 1.4487 | 0.1937 |

`room_size=100` で約7.5倍高速化し、`cProfile` 上の `FuzzyEngine` 系の累積時間比率も
80〜90%から約34%まで低下した。8機（4vs4）バトルを2つの乱数シードで各30ラウンド
実行して勝敗分布・撃墜数分布を比較したところ、n=30のサンプリングノイズの範囲内の
差にとどまり、統計的に有意な偏りは確認されなかった（詳細は
`docs/features/battle-engine-feature.md` 26.6節）。

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
