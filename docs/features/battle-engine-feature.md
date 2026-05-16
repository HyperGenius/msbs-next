# バトルエンジン高度化 機能仕様書

**バージョン:** 0.9.0  
**作成日:** 2026-04-27  
**更新日:** 2026-05-09  
**ステータス:** Phase 1-1 / Phase 2-1 / Phase 2-2 / Phase 2-3 / Phase 3-1 / Phase 3-2 / Phase 3-3 / Phase 5-2 / Phase 6-3 / Phase 6-4 実装済み

---

## 1. 概要

### 1.1 目的

現在の単純なターン制バトルエンジン（`BattleSimulator`）を、フィールド上の各MS/Pilotが自律的に判断・行動するニアリアルタイムシミュレーションへと高度化する。

### 1.2 現在の実装

| 項目 | 現状 |
|------|------|
| 進行方式 | ターン制（機動性順にソートしたユニットが順番に行動） |
| AI意思決定 | ルールベース（`tactics.priority` による固定戦術） |
| ターゲット選択 | `CLOSEST / WEAKEST / STRONGEST / THREAT / RANDOM` の5択 |
| 移動 | 単純な直線移動（ポテンシャルフィールド未実装） |
| 索敵 | `sensor_range` 内の敵を即時発見（確率要素なし） |
| 武器選択 | `active_weapon_index` の固定選択 |
| 戦略階層 | なし（すべてフラットなルール） |

### 1.3 ゴール

| 項目 | 目標 |
|------|------|
| 進行方式 | ニアリアルタイム（時間ステップ制） |
| AI意思決定 | 3階層ファジィ推論（戦略 → 行動選択 → 詳細行動） |
| ターゲット選択 | ファジィ推論による動的な脅威度・優先度計算 |
| 移動 | ポテンシャルフィールドによる自律的な移動経路生成 |
| 索敵 | 確率的索敵（距離・ノイズ・ミノフスキー粒子の影響） |
| 武器選択 | ファジィ推論による状況適応型武器選択 |
| 戦略階層 | 3階層のAI意思決定（後述） |
| チーム編成 | 複数チーム（PvPvE）を標準。特定ミッションでは2チーム構成も使用 |

---

## 2. アーキテクチャ

### 2.1 進行方式：時間ステップ制

ターン制を廃止し、**固定時間ステップ**（デフォルト `dt = 0.1s`）を導入する。  
1ステップごとに全ユニットが並列に判断・行動を更新する。

```
ループ（最大ステップ数 or 勝敗確定まで）:
  1. 索敵フェーズ（各ユニットが周囲を走査）
  2. AI意思決定フェーズ（3階層ファジィ推論で次の行動を決定）
  3. 行動実行フェーズ（移動・攻撃・スキル使用 等）
  4. リソース更新フェーズ（EN回復・弾薬・クールダウン・HP更新）
  5. 終了判定
```

### 2.2 AI意思決定の3階層

```
┌─────────────────────────────────────────────┐
│  高階層: 戦略・戦術 (Strategy & Tactics)      │
│  目標：大局的な方針を決定                     │
│  例：拠点制圧 / 防衛 / 撤退                   │
│  更新頻度：低（Nステップごと）                 │
├─────────────────────────────────────────────┤
│  中階層: 行動選択 (Behavior Selection)        │
│  目標：今何をすべきかを決定                   │
│  例：攻撃 / 移動 / スキル使用 / 撤退          │
│  入力：HP割合・敵数・味方数・距離など          │
│  更新頻度：中（毎ステップ）                    │
├─────────────────────────────────────────────┤
│  低階層: 詳細行動 (Detailed Action)           │
│  目標：選択された行動の具体的実行方法を決定    │
│  例：どの敵を狙う / どの武器を使う / 経路生成  │
│  更新頻度：高（毎ステップ）                    │
└─────────────────────────────────────────────┘
```

#### 高階層：戦略・戦術

- ゲーム開始時やフェーズ切り替えタイミングで更新
- 戦略タイプ（後述の `StrategyMode`）を選択し、中・低階層のファジィルールセットを切り替える
- 現フェーズでは **チームレベル**での戦略制御（個別ユニットは中・低階層で自律）

**StrategyMode 一覧（初期実装）**

| StrategyMode | 説明 |
|---|---|
| `AGGRESSIVE` | 積極的に敵を殲滅。高火力武器優先、前進を重視 |
| `DEFENSIVE` | 防衛ラインを維持。味方攻撃中の敵を優先、継戦武器優先 |
| `SNIPER` | 長距離狙撃特化。遠距離・低速の敵を優先 |
| `ASSAULT` | 近距離突撃特化。格闘・近距離高火力武器優先 |
| `RETREAT` | 撤退モード。被ダメージ回避を最優先 |

#### 中階層：行動選択（ファジィ推論）

現在HPと周囲の状況から「今すべき行動」を確率的に決定する。

**入力変数（Linguistic Variables）**

| 変数 | 範囲 | ファジィ集合 |
|------|------|------------|
| `hp_ratio` | 0.0〜1.0 | LOW / MEDIUM / HIGH |
| `enemy_count_near` | 0〜N | FEW / SEVERAL / MANY |
| `ally_count_near` | 0〜N | FEW / SEVERAL / MANY |
| `distance_to_nearest_enemy` | 0〜MAX | CLOSE / MID / FAR |

**出力変数**

| 変数 | 取りうる行動 |
|------|------------|
| `action` | ATTACK / MOVE / USE_SKILL / RETREAT |

**ルール例（AGGRESSIVE モード）**
```
IF hp_ratio IS HIGH AND enemy_count_near IS FEW THEN action IS ATTACK
IF hp_ratio IS LOW AND enemy_count_near IS MANY THEN action IS RETREAT
IF distance_to_nearest_enemy IS FAR THEN action IS MOVE
```

#### 低階層：詳細行動（ファジィ推論）

行動が「ATTACK」と決まった場合、具体的なターゲットと武器を決定する。

##### ターゲット選択

**入力変数**

| 変数 | 説明 |
|------|------|
| `target_hp_ratio` | ターゲットのHP割合 |
| `target_distance` | ターゲットとの距離 |
| `target_attack_power` | ターゲットの攻撃力（武器平均威力） |
| `is_attacking_ally` | ターゲットが味方を攻撃中か（boolean） |

**出力変数**

| 変数 | 説明 |
|------|------|
| `target_priority` | 0.0〜1.0 のターゲット優先度スコア |

##### 武器選択

**入力変数**

| 変数 | 説明 |
|------|------|
| `distance_to_target` | ターゲットとの距離 |
| `current_en_ratio` | 現在EN / 最大EN |
| `ammo_ratio` | 現在弾数 / 最大弾数 |
| `target_resistance` | ターゲットのビーム / 実弾耐性 |

**出力変数**

| 変数 | 説明 |
|------|------|
| `weapon_score` | 武器ごとのスコア（最高スコアの武器を選択） |

---

### 2.3 移動：ポテンシャルフィールド + 慣性モデル

現在の単純な直線移動に代わり、**ポテンシャルフィールド法**による目標方向の決定と**慣性モデル**による物理的な移動制約を組み合わせる。

#### 2.3.1 慣性モデル（物理制約）

MSの機動戦をリアルに再現するため、各ユニットは以下の物理パラメータを持つ。

| パラメータ | 説明 |
|---|---|
| `max_speed` | 最大速度 (m/s) |
| `acceleration` | 加速度 (m/s²) |
| `deceleration` | 減速度 (m/s²) |
| `max_turn_rate` | 最大旋回速度 (deg/s) |

**制約ルール**

- **突然停止の禁止:** 現在速度から `deceleration × dt` ずつしか減速できない。完全停止には `current_speed / deceleration` 秒必要。
- **旋回制限:** 1ステップで変更できる向きに `max_turn_rate × dt` deg の上限がある。
  - 通常MS（`max_turn_rate = 360 deg/s`、`dt = 0.1s`）→ 1ステップ最大 36° 旋回（180° 旋回は約0.5s）
  - MA・大型MS（`max_turn_rate = 30 deg/s`）→ 1ステップ最大 3° 旋回（180° 旋回に約6s必要）
- **加速制限:** 現在速度は `acceleration × dt` ずつしか増加できない。

**ユニット種別のデフォルト値目安**

| ユニット種別 | `max_speed` | `acceleration` | `deceleration` | `max_turn_rate` |
|---|---|---|---|---|
| 通常MS | 80 m/s | 30 m/s² | 50 m/s² | 360 deg/s |
| 高機動型MS | 150 m/s | 60 m/s² | 80 m/s² | 540 deg/s |
| MA（モビルアーマー） | 300 m/s | 15 m/s² | 8 m/s² | 30 deg/s |
| 大型機（ビグ・ザム等） | 40 m/s | 10 m/s² | 20 m/s² | 90 deg/s |

#### 2.3.2 ポテンシャルフィールド（Phase 3-2 実装済み）

ポテンシャルフィールド法で「目標方向ベクトル」を算出し、慣性モデルで実際の速度・位置を更新する。

| ソース | 種別 | 係数（絶対値）| 条件 |
|--------|------|------|------|
| 攻撃対象の敵 | 引力 | `+2.0` | `current_action == "ATTACK"` かつターゲット選択済み |
| MOVE / RETREAT 行動時の最近敵 | 引力 | `+1.5` | `current_action in ("MOVE", "RETREAT")` |
| 攻撃範囲外の高脅威敵 | 斥力（away_vec 方向に加算） | `1.5` | 脅威スコア（攻撃力/自機最大HP）> `HIGH_THREAT_THRESHOLD(0.5)` かつ射程外 |
| 味方ユニット | 弱い斥力（away_vec 方向に加算） | `0.8` | 距離 ≤ `ALLY_REPULSION_RADIUS(150m)` |
| マップ境界 | 斥力（境界から離れる方向に加算） | `3.0` | 境界からの距離 < `BOUNDARY_MARGIN(200m)` |
| 撤退ポイント | 強引力 | `+5.0` | `current_action == "RETREAT"` かつ撤退ポイント設定済み（Phase 3-3） |

**実装クラス:** `BattleSimulator._calculate_potential_field(unit, target, retreat_points)`

**ポテンシャル計算式:**
```
引力: contribution = coeff × (pos_s - pos_unit) / ‖pos_s - pos_unit‖
斥力: contribution = coeff × (pos_unit - pos_s) / max(‖pos_unit - pos_s‖, 1.0)
合計ベクトルを XZ 平面に投影して正規化 → desired_direction を得る
```

**ローカルミニマム対策:** 合算後のベクトルが `1e-6` 以下ならランダム単位ベクトルを返す。

**関連定数（`backend/app/engine/constants.py`）:**
- `ALLY_REPULSION_RADIUS = 150.0` m
- `BOUNDARY_MARGIN = 200.0` m
- `HIGH_THREAT_THRESHOLD = 0.5`
- `MAP_BOUNDS = (0.0, 5000.0)` m
- `RETREAT_ATTRACTION_COEFF = 5.0`（Phase 3-3）

**移動ログの間引き:** `MOVE_LOG_MIN_DIST = 100.0` m — 残距離がこの値未満のステップでは MOVE ログを抑制し、ログ量を削減する。

#### 2.3.3 撤退行動の制約（Phase 3-3 実装済み）

`RETREAT` 行動を選択したユニットは、フィールド上に設定された**撤退ポイント**（`RetreatPoint`）への強引力（係数 `RETREAT_ATTRACTION_COEFF = 5.0`）によって撤退経路へ誘導される。撤退ポイントが未設定（`retreat_points=[]`）のフィールドでは `RETREAT` はファジィルールの出力から除外され、`MOVE` にフォールバックされる。

**撤退フロー:**

```
1. ファジィ推論で RETREAT が出力
2. retreat_points が空 → MOVE にフォールバック（殲滅戦）
3. retreat_points が設定されている → RETREAT を確定
4. _calculate_potential_field() が RETREAT 中ユニットに撤退ポイントへの強引力を適用
5. ステップ末に _retreat_check_phase() を実行
6. 撤退ポイントの radius 内に入ったユニットを RETREATED ステータスに変更
7. BattleLog に action_type="RETREAT_COMPLETE" を記録
8. ACTIVE な生存ユニットが 1 チーム以下 → 戦闘終了
```

**ユニットステータス管理（`unit_resources[unit_id]["status"]`）:**

| ステータス | 説明 |
|---|---|
| `ACTIVE` | 通常の戦闘参加状態 |
| `RETREATED` | 撤退ポイントから離脱完了 |
| `DESTROYED` | 撃破済み（HP=0） |

撤退ポイントの詳細は「2.5 バトルフィールド定義」を参照。

---

### 2.4 ファジィルールのデータ駆動化

ファジィルールは **JSONファイル** として外部化し、StrategyMode に応じてロードするルールセットを切り替える。これにより、コードを変更せずにゲームバランスをチューニングできる。

```
backend/data/fuzzy_rules/
  aggressive.json
  defensive.json
  sniper.json
  assault.json
  retreat.json
```

#### JSONスキーマ（例: ターゲット選択ルール）

```json
{
  "strategy": "AGGRESSIVE",
  "rules": [
    {
      "id": "rule_001",
      "conditions": [
        { "variable": "target_hp_ratio", "set": "LOW" },
        { "variable": "distance_to_target", "set": "CLOSE" }
      ],
      "operator": "AND",
      "output": { "variable": "target_priority", "set": "HIGH" }
    }
  ],
  "membership_functions": {
    "target_hp_ratio": {
      "LOW":    { "type": "trapezoid", "params": [0.0, 0.0, 0.25, 0.40] },
      "MEDIUM": { "type": "triangle",  "params": [0.25, 0.50, 0.75] },
      "HIGH":   { "type": "trapezoid", "params": [0.60, 0.75, 1.0, 1.0] }
    }
  }
}
```

---

### 2.5 バトルフィールド定義

バトルフィールドには、シミュレーションに使用する静的パラメータを定義する。

#### 撤退ポイント（RetreatPoint）

撤退ポイントはフィールド上に設定された「離脱可能エリア」を示す座標と半径のペア。ユニットがその範囲内に進入すると、そのユニットはバトルから正式に離脱する。

| フィールド | 型 | 説明 |
|---|---|---|
| `position` | `Vector3` | 撤退ポイントの座標 |
| `radius` | `float` | 有効半径（m）。この範囲に入ると離脱扱い |
| `team_id` | `str \| None` | チームIDを指定すると特定チーム専用。`None` は全チーム共通 |

**ミッション種別ごとの設定例**

| ミッション種別 | 撤退ポイント設定 |
|---|---|
| 通常ミッション（PvPvE） | 各チームの出撃ポイント付近に1つずつ配置 |
| ボス戦（2チーム） | プレイヤーチームのみに配置（任意） |
| 殲滅戦 | 設定なし → `RETREAT` 行動は選択されない |

#### チーム編成

本仕様のデフォルトは **複数チーム（PvPvE）による乱戦** とする。

| 編成パターン | 説明 | 使用例 |
|---|---|---|
| **PvPvE（標準）** | 3チーム以上が独立して戦闘 | プレイヤー軍 vs 敵A vs 敵B の三つ巴 |
| **2チーム** | 特定ミッション向け | プレイヤー軍 vs 大ボス＋取り巻き |

どちらの構成も内部的には `team_id` による同一のチーム管理機構を使用する。ミッション定義で `teams` リストに指定するチーム数で切り替える。

---

## 3. データモデル変更

### 3.1 `MobileSuit` への追加フィールド

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `strategy_mode` | `str` | 現在の戦略モード（`AGGRESSIVE` 等） |
| `current_action` | `str` | 現在の行動（`ATTACK / MOVE / USE_SKILL / RETREAT`） |
| `target_id` | `UUID \| None` | 現在のターゲットID |
| `max_speed` | `float` | 最大速度 (m/s)。デフォルト: 80.0 ✅ Phase 3-1 実装済み |
| `acceleration` | `float` | 加速度 (m/s²)。デフォルト: 30.0 ✅ Phase 3-1 実装済み |
| `deceleration` | `float` | 減速度 (m/s²)。デフォルト: 50.0 ✅ Phase 3-1 実装済み |
| `max_turn_rate` | `float` | 最大旋回速度 (deg/s)。通常MS: 360、MA: 30 ✅ Phase 3-1 実装済み |

> **Note:** `current_action` / `target_id` は戦闘中の一時状態のため、`unit_resources` の `dict` に含めてDBには保存しない方針を基本とする（要検討）。

### 3.1.1 `unit_resources` への速度状態追加（Phase 3-1 実装済み）

`BattleSimulator.unit_resources[unit_id]` に以下を追加した（DB 非保存・戦闘中一時状態）。

| キー | 型 | 初期値 | 説明 |
|------|-----|--------|------|
| `velocity_vec` | `np.ndarray` | `[0, 0, 0]` | 現在の速度ベクトル (3D, m/s) |
| `heading_deg` | `float` | `0.0` | 現在の向き (XZ平面, 度) |

### 3.2 `BattleLog` への追加フィールド

> **ログスキーマの方針:** 旧ターン制ログとの後方互換性は持たない。本仕様に基づく新スキーマを採用し、既存の `BattleViewer` も新スキーマに合わせて更新する。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `timestamp` | `float` | バトル内の経過時間 (s)（旧: `turn` は廃止） |
| `fuzzy_scores` | `dict \| None` | ファジィ推論の中間スコア（デバッグ用） |
| `strategy_mode` | `str \| None` | 行動決定時の戦略モード |
| `velocity_snapshot` | `Vector3 \| None` | 行動時点の速度ベクトル |

---

## 4. 開発・実行環境

### 4.1 実行基盤の方針

| フェーズ | 実行環境 | 条件 |
|---------|---------|------|
| MVP〜中期 | GitHub Actions | 月次計算コストが無料枠の範囲 |
| 計算負荷増大後 | Cloud Run（バッチ） | ユニット数・ステップ数の増加時 |

### 4.2 ローカル開発・バランス調整環境

- **データソース:** 本番環境DB（ReadOnly接続）
- **結果出力:** JSONファイル（`/data/sim_results/` 等）、DBへの反映なし
- **目視確認:** フロントエンドの `BattleViewer` コンポーネントで再生
- **実行スクリプト:** `backend/scripts/run_simulation.py`（新規作成予定）

```bash
# ローカル実行例
python scripts/run_simulation.py \
  --mission-id <UUID> \
  --strategy aggressive \
  --output data/sim_results/result_$(date +%Y%m%d_%H%M%S).json
```

---

## 5. 実装ロードマップ

### Phase 1：MVP（最小動作確認）

**目標:** 時間ステップ制への移行 + 中階層ファジィ推論の最小実装

- [x] `BattleSimulator` の進行方式をターン制→時間ステップ制へリファクタリング
  - `process_turn()` を廃止し `step(dt: float = 0.1)` に移行
  - `self.turn` → `self.elapsed_time: float` に置換
  - `calculate_initiative()` / イニシアチブソート廃止
  - 最大 5000 ステップで引き分け終了
  - ステップ処理順: 索敵 → 行動 → リソース更新
- [x] 新 `BattleLog` スキーマへの移行
  - `turn: int` → `timestamp: float`（バトル内経過時間 s）
  - `velocity_snapshot: Vector3 | None` 追加
  - `fuzzy_scores: dict | None` 追加
  - `strategy_mode: str | None` 追加
- [x] `BattleViewer` を新ログスキーマに対応（Phase 1-4 で対応）
- [x] `FuzzyEngine` クラスの新規作成（Phase 1-2）
- [x] 中階層ファジィ推論の実装（Phase 1-2）
- [x] `aggressive.json` ルールセットの初期定義（Phase 1-2）
- [x] ローカル実行スクリプト（`run_simulation.py`）の作成（Phase 1-3）

### Phase 2：低階層ファジィ推論

- [x] ターゲット選択ファジィルール実装
- [x] 武器選択ファジィルール実装
- [x] `defensive.json` / `sniper.json` ルールセット追加

### Phase 3：移動の高度化

- [x] 慣性モデルの実装（Phase 3-1）
  - `MobileSuit` に `max_speed` / `acceleration` / `deceleration` / `max_turn_rate` フィールドを追加
  - `unit_resources` に `velocity_vec` / `heading_deg` を追加
  - `_apply_inertia(unit, desired_direction, dt)` ヘルパーを実装（旋回制限・加速制限・位置更新）
  - `_process_movement()` / `_search_movement()` を `_apply_inertia()` 呼び出しに改修
  - `BattleLog.velocity_snapshot` に速度ベクトルを記録
  - DB マイグレーション追加（`n8o9p0q1r2s3`）
- [x] ポテンシャルフィールドによる移動実装（Phase 3-2：目標方向ベクトル算出）
- [x] `RETREAT` モード時の撤退ポイント引力計算（Phase 3-3）
- [x] バトルフィールドへの `RetreatPoint` 定義の追加（Phase 3-3）
- [x] 複数チーム（3チーム以上）対応の確認テスト（Phase 3-3）

### Phase 4：戦略・戦術階層

- [x] チームレベルの戦略モード切り替えロジック（Phase 4-2 実装済み）
- [x] 戦況に応じた動的 `StrategyMode` 変更（劣勢時に `RETREAT` へ移行等）（Phase 4-3 実装済み）
- [x] `assault.json` / `retreat.json` ルールセット追加（Phase 4-1）

### Phase 5：スケールアウト・最適化

- [ ] Cloud Run バッチ実行対応
- [ ] ファジィルールのホットリロード（JSON変更のみでリロード）
- [ ] バランス調整GUI or CLIツールの整備

---

## 6. 未決定事項・検討中の課題

> 以下は仕様策定時点で未決定または議論が必要な事項です。実装フェーズで順次決定する。

### 6.1 時間ステップのデフォルト値

- `dt = 0.1s` を基準に検討しているが、GitHub Actions での最大実行時間（デフォルト6時間）を踏まえ、**バトル1件あたりの最大ステップ数** を決める必要がある
- 例：最大 `5000` ステップ × `dt=0.1s` = 500秒相当

### 6.2 デファジフィケーション手法

- 重心法（Centroid）を基本方針とするが、計算コストとのトレードオフを検証する
- 最大メンバーシップ法（MOM）の方が軽量な場合は切り替えを検討

### 6.3 ファジィライブラリの採用可否

- 既存の Python ファジィライブラリ（`scikit-fuzzy` 等）の採用 vs. 自前実装
- `requirements.txt` への依存追加コストと保守性を比較して決定

### 6.4 `current_action` / `target_id` の永続化

- 戦闘中の一時状態のみ `unit_resources` に持たせるか、`MobileSuit` モデルに追加してDBに保存するかを決定する
- リプレイ・デバッグ用途では `BattleLog` の `fuzzy_scores` に保存する方針が有力

### 6.5 パイロット個別のファジィパラメータ

- エースパイロット（`is_ace = True`）はファジィルールのパラメータ（集合の形状・閾値）を個別チューニングする設計を検討
- 例：エースは `hp_ratio.LOW` の閾値を引き下げ、低HPでも攻撃行動を選びやすくする

### 6.6 GitHub Actions での実行コスト上限

- 1バトルシミュレーションの目標実行時間（GitHub Actions の課金単位を考慮）
- 複数バトルの並列実行可否

---

## 7. 関連ドキュメント

- [battle_simulation_roadmap.md](../roadmaps/battle_simulation_roadmap.md) — これまでの実装履歴
- [BATCH_ARCHITECTURE.md](../BATCH_ARCHITECTURE.md) — バッチ実行基盤
- [TACTICS_IMPLEMENTATION.md](../TACTICS_IMPLEMENTATION.md) — 現在の戦術実装詳細

---

## 8. Phase 2-3: 戦略モード拡張 (DEFENSIVE / SNIPER)

### 8.1 概要

Phase 2-3 では、AGGRESSIVE のみだった戦略モードを拡張し、**DEFENSIVE** と **SNIPER** の2戦略向けファジィルールセットを追加した。ユニットの `strategy_mode` フィールドにより、行動選択・ターゲット選択・武器選択の全3レイヤーで動的にルールセットを切り替えられる。

### 8.2 実装ファイル一覧

| ファイル | 戦略 | レイヤー | ルール数 |
|---------|------|---------|---------|
| `backend/data/fuzzy_rules/defensive.json` | DEFENSIVE | behavior_selection | 12 |
| `backend/data/fuzzy_rules/defensive_target_selection.json` | DEFENSIVE | target_selection | 12 |
| `backend/data/fuzzy_rules/defensive_weapon_selection.json` | DEFENSIVE | weapon_selection | 12 |
| `backend/data/fuzzy_rules/sniper.json` | SNIPER | behavior_selection | 12 |
| `backend/data/fuzzy_rules/sniper_target_selection.json` | SNIPER | target_selection | 12 |
| `backend/data/fuzzy_rules/sniper_weapon_selection.json` | SNIPER | weapon_selection | 12 |

### 8.3 MobileSuit.strategy_mode フィールド

`MobileSuit` モデルに `strategy_mode: str | None` フィールドを追加した（DBマイグレーション: `m7n8o9p0q1r2`）。

| 値 | 説明 |
|----|------|
| `None` (未設定) | AGGRESSIVE にフォールバック |
| `AGGRESSIVE` | 積極的な攻撃重視 |
| `DEFENSIVE` | 防衛ライン維持、継戦能力優先 |
| `SNIPER` | 遠距離維持、確実撃破重視 |
| `ASSAULT` | 近距離突撃特化。格闘・近距離高火力武器優先（Phase 4-1 実装済み） |
| `RETREAT` | 撤退重視。遠距離牽制優先（Phase 4-1 実装済み） |

無効な値が設定された場合は `AGGRESSIVE` にフォールバックし、警告ログを出力する。

### 8.4 BattleSimulator の変更点

- `_strategy_engines: dict[str, dict[str, FuzzyEngine]]` を追加
  - キー構造: `{"AGGRESSIVE": {"behavior": ..., "target": ..., "weapon": ...}, "DEFENSIVE": {...}, "SNIPER": {...}}`
  - `_load_strategy_engines()` がディレクトリを走査し自動ロード
- `_resolve_strategy_mode(unit)` ヘルパーメソッドを追加
  - 無効モードは AGGRESSIVE にフォールバック + 警告ログ
- `_ai_decision_phase()`: unit の strategy_mode に応じた behavior エンジンを選択
- `_select_target_fuzzy()`: unit の strategy_mode に応じた target エンジンを選択
- `_select_weapon_fuzzy()`: unit の strategy_mode に応じた weapon エンジンを選択
- `BattleLog.strategy_mode` に実際に使用した戦略モード名を記録

### 8.5 VALID_STRATEGY_MODES 定数

`backend/app/engine/constants.py` に追加:

```python
VALID_STRATEGY_MODES: frozenset[str] = frozenset(
    {"AGGRESSIVE", "DEFENSIVE", "SNIPER", "ASSAULT", "RETREAT"}
)
```

### 8.6 run_simulation.py の変更

`--strategy` オプションを追加。例:
```bash
python scripts/run_simulation.py --mission-id 1 --strategy SNIPER
```

---

## 9. Phase 4-1: ルールセット拡張 (ASSAULT / RETREAT)

### 9.1 概要

Phase 4-1 では、**ASSAULT** と **RETREAT** の2戦略向けファジィルールセット（各3レイヤー）を追加した。
Phase 2-3 で確立した「JSONファイルを追加するだけで新戦略を組み込めるアーキテクチャ」を活用し、コード変更なしに2戦略を追加している。

### 9.2 実装ファイル一覧

| ファイル | 戦略 | レイヤー | ルール数 |
|---------|------|---------|---------|
| `backend/data/fuzzy_rules/assault.json` | ASSAULT | behavior_selection | 12 |
| `backend/data/fuzzy_rules/assault_target_selection.json` | ASSAULT | target_selection | 12 |
| `backend/data/fuzzy_rules/assault_weapon_selection.json` | ASSAULT | weapon_selection | 12 |
| `backend/data/fuzzy_rules/retreat.json` | RETREAT | behavior_selection | 12 |
| `backend/data/fuzzy_rules/retreat_target_selection.json` | RETREAT | target_selection | 12 |
| `backend/data/fuzzy_rules/retreat_weapon_selection.json` | RETREAT | weapon_selection | 12 |

### 9.3 ASSAULT 戦略の特性

- **行動選択**: 近距離の敵に対して積極的に ATTACK を選択。HP LOW でも CLOSE 距離では ATTACK を継続（AGGRESSIVEよりも低HP閾値まで攻撃）
- **ターゲット選択**: CLOSE 距離の敵を HIGH 優先度で選択。FAR 距離の敵は LOW 優先度
- **武器選択**: CLOSE 距離での武器スコアを HIGH に設定。FAR 距離での武器スコアは LOW に設定

### 9.4 RETREAT 戦略の特性

- **行動選択**: HP LOW 時や敵数 MANY 時に RETREAT を最優先。撤退ポイント未設定時は MOVE にフォールバック
- **ターゲット選択**: 基本的に脅威度低く設定。近距離高火力敵のみ HIGH 優先度
- **武器選択**: FAR/MID 距離での武器スコアを HIGH に設定。遠距離から牽制しながら撤退

### 9.5 自動ロードの仕組み

`_STRATEGY_FILE_PREFIXES` に `"ASSAULT": "assault"` / `"RETREAT": "retreat"` が登録済みであり、
`_load_strategy_engines()` が `assault.json` / `assault_target_selection.json` / `assault_weapon_selection.json`
（および `retreat*` 系）を自動検出してロードする。追加のコード変更は不要。

---

## 10. Phase 4-2: TeamStrategyController インフラ

### 10.1 概要

Phase 4-2 では、チームレベルの戦略モードを管理する **`TeamStrategyController`** と **`TeamMetrics`** データクラスを実装した。`BattleSimulator._strategy_phase()` が定期的に各チームのメトリクスを収集し、コントローラが戦略変更を判断する基盤を整備した。

### 10.2 主要コンポーネント

- **`TeamMetrics`** (`backend/app/engine/strategy_controller.py`): チームの現在の戦況データ（生存率・HP率・現在戦略等）
- **`TeamStrategyController`** (`backend/app/engine/strategy_controller.py`): チームの戦略モードを管理するコントローラ。`should_evaluate()` / `evaluate()` / `apply()` の3メソッドを持つ
- **`BattleSimulator._collect_team_metrics()`**: 指定チームの TeamMetrics を算出するヘルパー
- **`BattleSimulator._strategy_phase()`**: 全チームの戦略評価・更新フェーズ

---

## 11. Phase 4-3: 動的 StrategyMode 遷移ルール

### 11.1 概要

Phase 4-3 では、`TeamStrategyController.evaluate()` に **遷移ルール評価ロジック** を実装した。チームの戦況データ（HP率・生存率）に基づき、事前定義されたルールセット `STRATEGY_TRANSITION_RULES` を上から評価して StrategyMode を自動切換えする。

### 11.2 `StrategyTransitionRule` データ構造

```python
@dataclass
class StrategyTransitionRule:
    """戦略遷移ルール定義."""
    rule_id: str
    from_strategy: str | None   # None は any にマッチ
    to_strategy: str
    condition: Callable[[TeamMetrics], bool]
    description: str
```

### 11.3 戦略遷移ルール一覧 (T01〜T10)

ルール評価は上から順に実施し、最初にマッチしたルールを採用する（最優先ルール優先）。

| ルールID | 現在モード | 条件 | 遷移先モード | 説明 |
|---------|----------|------|------------|------|
| `T01` | `AGGRESSIVE` | `avg_hp_ratio < 0.30` AND `alive_ratio < 0.50` | `RETREAT` | 大損害を受けたら撤退 |
| `T02` | `AGGRESSIVE` | `avg_hp_ratio < 0.50` AND `alive_ratio < 0.60` | `DEFENSIVE` | 劣勢になったら防衛重視に切替 |
| `T03` | `DEFENSIVE` | `avg_hp_ratio < 0.25` AND `alive_ratio < 0.40` | `RETREAT` | 防衛中も限界なら撤退 |
| `T04` | `DEFENSIVE` | `avg_hp_ratio >= 0.65` AND `alive_ratio >= 0.70` | `AGGRESSIVE` | 体勢を立て直したら攻勢へ |
| `T05` | `SNIPER` | `avg_hp_ratio < 0.30` AND `alive_ratio < 0.50` | `RETREAT` | スナイパーも大損害なら撤退 |
| `T06` | `SNIPER` | `avg_hp_ratio < 0.50` | `DEFENSIVE` | スナイパーが劣勢なら防衛へ |
| `T07` | `ASSAULT` | `avg_hp_ratio < 0.35` AND `alive_ratio < 0.50` | `RETREAT` | 突撃部隊も壊滅寸前なら撤退 |
| `T08` | `ASSAULT` | `avg_hp_ratio < 0.55` | `AGGRESSIVE` | 突撃継続が難しければ通常攻撃に切替 |
| `T09` | `RETREAT` | `alive_ratio < 0.20` | `RETREAT` | 撤退中は変更しない（維持） |
| `T10` | `RETREAT` | `retreat_points_empty == True` | `DEFENSIVE` | 撤退ポイントなし → 防衛に切替（殲滅戦） |

> **Note:** T09 の `RETREAT → RETREAT` は「一度 RETREAT に入ったら撤退ポイントへ到達するまで維持」の意図。ループ内で `to_strategy == current_strategy` の場合はスキップするため次のルールへ進む。

### 11.4 撤退ポイント未設定時の T10 フォールバック

`_strategy_phase()` 内で `evaluate()` が "RETREAT" を返した場合に `len(self.retreat_points) == 0` を確認し、空なら "DEFENSIVE" に置き換えて `rule_id = "T10"` とする。

```python
if new_strategy == "RETREAT" and len(self.retreat_points) == 0:
    new_strategy = "DEFENSIVE"
    matched_rule_id = "T10"
```

### 11.5 `STRATEGY_CHANGED` ログの詳細フィールド

```python
details = {
    "previous_strategy": "AGGRESSIVE",
    "new_strategy": "DEFENSIVE",
    "rule_id": "T02",           # マッチしたルールID
    "trigger_metrics": {
        "avg_hp_ratio": 0.45,
        "alive_ratio": 0.55,
        "min_hp_ratio": 0.10,
        "alive_count": 3,
        "total_count": 5,
    }
}
```

### 11.6 閾値定数（`backend/app/engine/constants.py`）

遷移ルールの閾値はすべて `constants.py` に定数として分離されており、コード変更なしにチューニング可能。

| 定数名 | デフォルト値 | 対応ルール |
|--------|------------|---------|
| `AGGRESSIVE_RETREAT_HP_THRESHOLD` | `0.30` | T01 |
| `AGGRESSIVE_RETREAT_ALIVE_THRESHOLD` | `0.50` | T01 |
| `AGGRESSIVE_DEFENSIVE_HP_THRESHOLD` | `0.50` | T02 |
| `AGGRESSIVE_DEFENSIVE_ALIVE_THRESHOLD` | `0.60` | T02 |
| `DEFENSIVE_RETREAT_HP_THRESHOLD` | `0.25` | T03 |
| `DEFENSIVE_RETREAT_ALIVE_THRESHOLD` | `0.40` | T03 |
| `DEFENSIVE_AGGRESSIVE_HP_THRESHOLD` | `0.65` | T04 |
| `DEFENSIVE_AGGRESSIVE_ALIVE_THRESHOLD` | `0.70` | T04 |
| `SNIPER_RETREAT_HP_THRESHOLD` | `0.30` | T05 |
| `SNIPER_RETREAT_ALIVE_THRESHOLD` | `0.50` | T05 |
| `SNIPER_DEFENSIVE_HP_THRESHOLD` | `0.50` | T06 |
| `ASSAULT_RETREAT_HP_THRESHOLD` | `0.35` | T07 |
| `ASSAULT_RETREAT_ALIVE_THRESHOLD` | `0.50` | T07 |
| `ASSAULT_AGGRESSIVE_HP_THRESHOLD` | `0.55` | T08 |
| `RETREAT_WIPE_ALIVE_THRESHOLD` | `0.20` | T09 |

---

## 12. Phase 5-2: ファジィルールのホットリロード

### 12.1 概要

`backend/data/fuzzy_rules/` 以下の JSON ファイルを変更するだけで **`BattleSimulator` の再起動なしにルールセットを再ロード**できる仕組み。バランス調整作業（JSON チューニング → シミュレーション実行のサイクル）を短縮するための **ローカル開発専用** 機能。

### 12.2 ファイルハッシュベースの変更検出

`FuzzyEngine` に `_file_hash(path)` ユーティリティ関数を追加。SHA-256 ハッシュでファイル内容の変更を検出する。

```python
# backend/app/engine/fuzzy_engine.py
def _file_hash(path: Path) -> str:
    """ファイルの SHA-256 ハッシュを返す."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
```

### 12.3 `FuzzyRuleCache` クラス

`backend/app/engine/fuzzy_rule_cache.py` に実装。

| メソッド | 説明 |
|---------|------|
| `__init__(rules_dir)` | 全ルールを初期ロードし、ハッシュを記録 |
| `get_engines()` | ハッシュ変更を検出して差分のみ再ロードし、エンジン辞書を返す |
| `force_reload_all()` | 全エンジンを強制再ロード |

### 12.4 `BattleSimulator` の変更

`enable_hot_reload: bool = False` パラメータを追加。`_strategy_engines` をプロパティ化。

| `enable_hot_reload` | 動作 |
|---------------------|------|
| `False`（デフォルト） | 起動時のスナップショットを返す（本番・テスト用） |
| `True` | `FuzzyRuleCache.get_engines()` を呼び差分ロードを行う（ローカル開発用） |

### 12.5 `run_simulation.py --hot-reload` オプション

```bash
# ルールを編集しながら繰り返しシミュレーションを実行
python scripts/run_simulation.py --mission-id 1 --hot-reload
```

変更が検出されると標準出力にログが表示される:

```
[HotReload] aggressive.json が変更されました → AGGRESSIVE:behavior を再ロードしました
```

### 12.6 `schema.json` の除外

`FuzzyRuleCache` は `{prefix}{suffix}.json` の命名規則に一致するファイルのみをロードする。`schema.json` はどの戦略モード・レイヤーのパターンにも一致しないため、自動的に除外される。

## 13. Phase 6-2: 武器クールダウンの時間ステップ制対応

### 13.1 概要

旧ターン制の `cool_down_turn`（整数）を廃止し、時間ステップ制（`dt = 0.1s`）に対応した **秒単位クールダウン** に移行。

| 変更前 | 変更後 |
|--------|--------|
| `current_cool_down: int` (ターン数) | `cooldown_remaining_sec: float` (秒) |
| `cool_down_turn` を基準に `-= 1` | `cooldown_sec` を基準に `-= dt` |

### 13.2 `Weapon.cooldown_sec` フィールド

```python
cooldown_sec: float = Field(
    default=1.0,
    description="発射後の再使用待機時間（秒）。0.0 は連射可能を意味する"
)
```

**武器種別ごとの目安値:**

| 武器種別 | `cooldown_sec` 目安 |
|----------|----------------------|
| MELEE（格闘） | `1.5` |
| CLOSE_RANGE（近距離） | `0.5` |
| RANGED 標準（マシンガン等） | `0.3` |
| RANGED 重火力（ビーム砲等） | `2.0〜5.0` |
| RANGED 狙撃（スナイパーライフル） | `5.0〜10.0` |

`cool_down_turn` は後方互換フィールドとして残るが、シミュレーションでは参照しない。

### 13.3 `weapon_states` の変更

```python
# 変更後
weapon_state = {
    "current_ammo": weapon.max_ammo,
    "cooldown_remaining_sec": 0.0,  # 残りクールダウン時間（秒）
}
```

### 13.4 各フェーズの変更点

| フェーズ | 変更内容 |
|----------|----------|
| `_refresh_phase()` | `cooldown_remaining_sec -= dt`（`max(0.0, ...)` でクリップ） |
| `_check_attack_resources()` | `cooldown_remaining_sec > 0.0` で攻撃ブロック |
| `_consume_attack_resources()` | `cooldown_sec` を `cooldown_remaining_sec` にセット |
| `_log_attack_wait()` | `残りXX.Xs` 形式で秒単位表示 |

### 13.5 WAIT ログ形式

```
...（残り1.5s）...
```

旧形式（`残り2ターン`）は廃止。

---

## 14. Phase 6-3: フィールド初期化改善（スポーン領域分離 + 障害物デフォルト配置）

### 14.1 概要

`BattleField` モデルを拡張し、**スポーン領域の定義** と **障害物の自動生成** を実装する。

- **スポーン領域 (`SpawnZone`)**: チームごとの初期配置エリアを定義し、チーム間の距離を保証する
- **障害物の自動生成**: `obstacle_density` に応じた障害物をフィールドに自動配置する

### 14.2 新モデル: `SpawnZone`

```python
class SpawnZone(SQLModel):
    """スポーン領域定義 (Phase 6-3)."""
    team_id: str      # 使用チームID
    center: Vector3   # 領域中心座標
    radius: float     # 領域半径 (m)。ユニットはこの円内にランダム配置される
```

### 14.3 `BattleField` の拡張

```python
class BattleField(SQLModel):
    obstacles: list[Obstacle] = []
    spawn_zones: list[SpawnZone] = []        # Phase 6-3: チームごとのスポーン領域
    obstacle_density: str = "MEDIUM"         # Phase 6-3: "NONE" / "SPARSE" / "MEDIUM" / "DENSE"
```

### 14.4 `BattleSimulator` の変更

#### 新パラメータ

```python
def __init__(
    self,
    ...
    battlefield: BattleField | None = None,  # Phase 6-3
):
```

**`battlefield=None`（デフォルト）:** 後方互換モード。ユニット位置・障害物は変更されない。  
**`battlefield=BattleField(...)`:** 新機能が有効化される。

#### 自動生成フロー

```
BattleField を battlefield=BattleField(...) で渡した場合:
  1. spawn_zones が空 → _generate_default_spawn_zones() でデフォルト領域を生成
  2. _apply_spawn_zones() で全ユニットをスポーン領域内にランダム配置
  3. obstacles が空 かつ obstacle_density != "NONE" → _generate_obstacles() で自動生成
```

### 14.5 デフォルトスポーン領域

`map_bounds` の場合（Phase 6-5 以降は動的計算値。以下は `map_bounds = (0.0, 5000.0)` の例）:

| チーム数 | 配置方式 | スポーン中心（XZ）| スポーン半径 |
|---|---|---|---|
| 2チーム | 対角 | `(500, 500)` / `(4500, 4500)` | `400m` |
| 3チーム | 三角形頂点 | `(500, 500)` / `(4500, 500)` / `(2500, 4500)` | `400m` |
| 4チーム | 四隅 | `(500, 500)` 等 | `300m` |
| 5チーム以上 | 円周均等配置 | 中心から放射状 | `300m` |

2チームの場合、スポーン中心間距離は約 `5657m`（`≥ 1000m` の要件を満たす）。

### 14.6 障害物自動生成パラメータ

| `obstacle_density` | グリッド N | 配置確率 p | 障害物半径 |
|---|---|---|---|
| `"SPARSE"` | 6 | 0.4 | 100〜200m |
| `"MEDIUM"` | 8 | 0.6 | 80〜150m |
| `"DENSE"` | 10 | 0.8 | 60〜120m |
| `"NONE"` | — | — | 障害物なし |

生成方式: グリッド分割＋ランダムオフセット。スポーン領域と重複する位置には配置しない。

### 14.7 新定数 (`constants.py`)

```python
DEFAULT_OBSTACLE_DENSITY: str = "MEDIUM"
OBSTACLE_GRID_PARAMS: dict[str, dict] = {
    "SPARSE": {"n": 6, "prob": 0.4, "radius_range": (100.0, 200.0)},
    "MEDIUM": {"n": 8, "prob": 0.6, "radius_range": (80.0, 150.0)},
    "DENSE":  {"n": 10, "prob": 0.8, "radius_range": (60.0, 120.0)},
}
SPAWN_ZONE_RADIUS_2TEAM: float = 400.0
SPAWN_ZONE_RADIUS_3TEAM: float = 400.0
SPAWN_ZONE_RADIUS_4TEAM: float = 300.0
SPAWN_ZONE_SAMPLE_MAX_TRIES: int = 50
```

### 14.8 使用例

```python
# デフォルト設定（MEDIUM 密度、スポーン領域は自動生成）
sim = BattleSimulator(player, enemies, battlefield=BattleField())

# 障害物なし（後方互換テスト用）
sim = BattleSimulator(player, enemies, battlefield=BattleField(obstacle_density="NONE"))

# 手動スポーン領域 + DENSE 障害物
bf = BattleField(
    spawn_zones=[
        SpawnZone(team_id="PT", center=Vector3(x=500, y=0, z=500), radius=0.0),  # radius=0.0 の場合、中心座標に固定配置される
        SpawnZone(team_id="ET", center=Vector3(x=4500, y=0, z=4500), radius=400.0),
    ],
    obstacle_density="DENSE",
)
sim = BattleSimulator(player, enemies, battlefield=bf)
```

### 14.9 後方互換性

| 呼び出し方 | スポーン適用 | 障害物生成 |
|---|---|---|
| `BattleSimulator(player, enemies)` | ❌ | ❌（後方互換） |
| `BattleSimulator(player, enemies, obstacles=[...])` | ❌ | ❌（明示的 obstacles 優先） |
| `BattleSimulator(player, enemies, battlefield=BattleField(...))` | ✅ | ✅（density≠NONE の場合） |

---

## 15. Phase 6-4: 確率的索敵（距離依存発見確率の導入）

### 15.1 概要

`_detection_phase()` における新規発見判定を**確率ベース**に変更し、遠方の敵は発見しにくく近距離では確実に発見できるグラデーションを実現する。

**目的:**
- バトル開始直後の「全 MS 同士が即座に索敵完了」を防ぎ、接近戦に至るまでの過程を生む
- ミノフスキー粒子環境での索敵困難性をより忠実に再現
- 索敵スキルや高 `sensor_range` 機体に差別化の価値を持たせる

### 15.2 発見確率の計算式

$$P(\text{detect}) = \max\!\left(0,\ 1 - \left(\frac{d}{d_{\text{eff}}}\right)^k\right)$$

| パラメータ | 説明 |
|---|---|
| $d$ | 索敵ユニットからターゲットまでの距離 (m) |
| $d_{\text{eff}}$ | 有効索敵範囲（`sensor_range × sensor_multiplier`） |
| $k$ | 距離減衰指数。`DETECTION_FALLOFF_EXPONENT`（通常）または `DETECTION_FALLOFF_EXPONENT_MINOVSKY`（ミノフスキー粒子時） |

**`k = 2.0`（デフォルト）での挙動例（`sensor_range = 500m`）:**

| 距離 | 発見確率 |
|---|---|
| 0m | 100% |
| 100m | 96% |
| 250m | 75% |
| 350m | 51% |
| 450m | 19% |
| 500m | 0% |

### 15.3 発見の永続性

発見確率は**新規発見時のみ**適用する。一度発見した敵は `team_detected_units` に追加され、以降は LOS チェックのみで維持・喪失を判定する（Phase A の既存ロジックを維持）。

```
既に発見済み → LOS チェックのみ（確率判定なし）
未発見       → 確率判定 → 成功で発見リストに追加
```

### 15.4 ミノフスキー粒子時の強化

ミノフスキー粒子時は索敵範囲の半減（`× 0.5`）に加え、距離減衰指数 $k$ を `DETECTION_FALLOFF_EXPONENT_MINOVSKY` に切り替えることで、近距離でも発見確率がさらに低下する。

```python
if "MINOVSKY" in self.special_effects:
    effective_sensor_range = sensor_range * 0.5  # MINOVSKY_SENSOR_RANGE_MULTIPLIER
    falloff_exponent = DETECTION_FALLOFF_EXPONENT_MINOVSKY  # 3.0
else:
    effective_sensor_range = sensor_range
    falloff_exponent = DETECTION_FALLOFF_EXPONENT  # 2.0
```

### 15.5 新定数 (`constants.py`)

```python
# 確率的索敵定数 (Phase 6-4)
DETECTION_FALLOFF_EXPONENT: float = 2.0       # 通常環境の距離減衰指数
DETECTION_FALLOFF_EXPONENT_MINOVSKY: float = 3.0  # ミノフスキー粒子時の減衰指数
```

### 15.6 発見ログの変更

発見ログに索敵確率パーセントを追加。

```
# 通常環境
"{actor_name}が{dist_label}に{target.name}を発見！（索敵確率 56%）"

# ミノフスキー粒子時
"{actor_name}が濃密なミノフスキー粒子の中、{dist_label}に{target.name}の反応を捉えた！（索敵確率 21%）"
```

### 15.7 後方互換性

- `random.random()` を使用するため、テストは `unittest.mock.patch("app.engine.targeting.random.random", return_value=0.0)` でモックして決定論的な動作を保証すること
- 既存の確率なし検出ロジックに依存するテストはすべて対応済み（Phase 6-4 実装時に更新）

---

## 16. Phase 6-5: フィールドスケーリング（参加ユニット数に応じた MAP_BOUNDS 動的調整）

### 16.1 概要

固定だった `MAP_BOUNDS = (0.0, 5000.0)` を廃止し、**総ユニット数に応じてフィールドサイズを動的計算**する仕組みを導入する。

- **目的**: 1ユニットあたりの面積（密度）を一定に保ち、少人数戦はコンパクト、多人数戦は十分な広さを確保する
- **設計方針**: グローバル定数 `MAP_BOUNDS` は変更せず、`BattleSimulator` インスタンス変数 `self.map_bounds` として保持する

### 16.2 スケーリング計算式

```
N_total  = 全チームの総ユニット数
面積     = N_total × AREA_PER_UNIT
辺長     = sqrt(面積)
map_bounds = (0.0, clamp(辺長, MIN_FIELD_SIZE, MAX_FIELD_SIZE))
```

**ユニット数と推定フィールドサイズ（参考値）:**

| 総ユニット数 | 面積 (m²) | 計算辺長 (m) | 実効辺長 (m) |
|---|---|---|---|
| 2 | 500,000 | 707 | 2,000（MIN クランプ） |
| 4 | 1,000,000 | 1,000 | 2,000（MIN クランプ） |
| 16 | 4,000,000 | 2,000 | 2,000（MIN クランプ） |
| 17 | 4,250,000 | 2,062 | 2,062 |
| 20 | 5,000,000 | 2,236 | 2,236 |
| 100 | 25,000,000 | 5,000 | 5,000 |
| 256 | 64,000,000 | 8,000 | 8,000（MAX クランプ） |
| 300+ | — | >8,660 | 8,000（MAX クランプ） |

### 16.3 新定数 (`constants.py`)

```python
# フィールドスケーリング定数 (Phase 6-5)
AREA_PER_UNIT: float = 250_000.0  # 1ユニットあたりの面積 (m²) = 500m × 500m
MIN_FIELD_SIZE: float = 2000.0    # 最小フィールド辺長 (m)
MAX_FIELD_SIZE: float = 8000.0    # 最大フィールド辺長 (m)
```

### 16.4 `BattleSimulator` の変更

`__init__()` で `self.units` 確定後にフィールドサイズを計算し、インスタンス変数として保持する。

```python
# フィールドスケーリング: 総ユニット数に応じて map_bounds を動的計算 (Phase 6-5)
n_total = len(self.units)
side_len = math.sqrt(n_total * AREA_PER_UNIT)
side_len = max(MIN_FIELD_SIZE, min(MAX_FIELD_SIZE, side_len))
self.map_bounds: tuple[float, float] = (0.0, side_len)
```

> **注意**: グローバル定数 `constants.MAP_BOUNDS` への上書きは行わない。

### 16.5 影響範囲

`self.map_bounds` に移行したメソッド:

| メソッド | 変更前 | 変更後 |
|---|---|---|
| `BattleSimulator._generate_default_spawn_zones()` | `MAP_BOUNDS` | `self.map_bounds` |
| `BattleSimulator._generate_obstacles()` | `MAP_BOUNDS` | `self.map_bounds` |
| `MovementMixin._boundary_repulsion()` | `MAP_BOUNDS` | `self.map_bounds` |

### 16.6 Phase 6-3 スポーン領域との整合

`_generate_default_spawn_zones()` が `self.map_bounds` を参照するため、
フィールドサイズ変更後に自動生成されるスポーン領域も新しいマップサイズに自動追従する。

2チーム・20ユニット時（`map_bounds = (0.0, 2236.0)`）のスポーン中心例:

| チーム数 | 配置方式 | スポーン中心（XZ）| スポーン半径 |
|---|---|---|---|
| 2チーム | 対角 | `(500, 500)` / `(1736, 1736)` | `400m` |
| 3チーム | 三角形頂点 | `(500, 500)` / `(1736, 500)` / `(1118, 1736)` | `400m` |
| 4チーム | 四隅 | `(500, 500)` 等 | `300m` |
| 5チーム以上 | 円周均等配置 | 中心から放射状 | `300m` |

### 16.7 後方互換性

- グローバル定数 `MAP_BOUNDS = (0.0, 5000.0)` は変更されない
- `BattleSimulator` に `map_bounds` パラメータは追加しない（自動計算のみ）
- `MAP_BOUNDS` を直接参照していた既存のテストは `constants.MAP_BOUNDS` を引き続き使用できる
- `_boundary_repulsion()` は `self.map_bounds` を参照するため、ユニットは動的フィールド内に正しく留まる

