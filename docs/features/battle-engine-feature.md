# バトルエンジン高度化 機能仕様書

**バージョン:** 0.9.0  
**作成日:** 2026-04-27  
**更新日:** 2026-05-16  
**ステータス:** Phase 1-1 / Phase 2-1 / Phase 2-2 / Phase 2-3 / Phase 3-1 / Phase 3-2 / Phase 3-3 / Phase 5-2 / Phase 6-3 / Phase 6-4 / Phase 6-5 / Phase 6-6 実装済み

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
  1. obstacles が空 かつ obstacle_density != "NONE" → _generate_obstacles() で自動生成
  2. spawn_zones が空 → _generate_default_spawn_zones() でデフォルト領域を生成
     （対称配置の候補点が障害物と重なる場合、_find_clear_spawn_center() が
      近傍でジッター探索して回避する）
  3. ジッターでも回避しきれなかった障害物・明示的な spawn_zones と重複する障害物は
     _remove_obstacles_overlapping_spawn_zones() で最終的に除去する
  4. _apply_spawn_zones() で全ユニットをスポーン領域内にランダム配置
```

**Issue #437 での変更点（障害物→スポーンの順への変更）:** 旧実装ではスポーン領域を
先に確定し、障害物生成側がスポーン領域と重なるグリッドセルをスキップしていた。この
場合、常にスポーン中心の周囲だけが円形に障害物ゼロの「安全地帯」になり、障害物が
実際の交戦（移動経路・LOS）にほとんど影響しない問題があった。障害物を先に配置する
順に変更し、スポーン中心側が障害物配置に応じて（対称配置を保ったまま）ジッター移動
するようにしたことで、障害物の抜け方が毎回異なる非対称な形状になり、障害物がカバー
や進路の障壁として機能しやすくなった。

### 14.5 デフォルトスポーン領域

`map_bounds` の場合（Phase 6-5 以降は動的計算値。以下は `map_bounds = (0.0, 5000.0)` の例）:

| チーム数 | 配置方式 | スポーン中心（XZ）| スポーン半径 |
|---|---|---|---|
| 2チーム | 対角 | `(500, 500)` / `(4500, 4500)` | `400m` |
| 3チーム | 三角形頂点 | `(500, 500)` / `(4500, 500)` / `(2500, 4500)` | `400m` |
| 4チーム | 四隅 | `(500, 500)` 等 | `300m` |
| 5チーム以上 | 円周均等配置 | 中心から放射状 | `300m` |

2チームの場合、スポーン中心間距離は約 `5657m`。

> **注意（Issue: 初期配置での索敵回避 / 初速付与）**: 上記は `map_bounds = (0.0, 5000.0)` 時点の目安値であり、
> 実際の間隔保証は「参加ユニットの最大 `sensor_range` + 安全マージン」を基準に動的計算される。
> 詳細は [§21](#21-issue-初期配置での索敵回避--スポーン時初速の付与) を参照。

### 14.6 障害物自動生成パラメータ

| `obstacle_density` | グリッド N | 配置確率 p | 障害物半径 |
|---|---|---|---|
| `"SPARSE"` | 6 | 0.4 | 100〜200m |
| `"MEDIUM"` | 8 | 0.6 | 80〜150m |
| `"DENSE"` | 10 | 0.8 | 60〜120m |
| `"NONE"` | — | — | 障害物なし |

生成方式: グリッド分割＋ランダムオフセット。障害物はスポーン領域より先に生成されるため、
生成時点ではスポーン領域を考慮しない（フィールド全体に一様分布する）。スポーン領域との
重複回避は、スポーン領域決定時のジッター探索・最終フィルタ側で行う（#437）。

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

# スポーン中心の障害物回避 (#437)
SPAWN_CENTER_JITTER_RADIUS: float = 300.0    # 障害物回避のためのジッター探索半径 (m)
SPAWN_CENTER_SEARCH_MAX_TRIES: int = 30      # 障害物回避位置の探索最大試行回数
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

---

## 17. Phase 6-6: 発見同ステップ内攻撃抑制（リアクション遅延）

### 17.1 概要

Phase 6-4 で導入した確率的索敵との組み合わせで生じる**「発見と攻撃が同一ステップで起きる」問題**を解消する。

- **問題点**: `_detection_phase()` で発見したステップ内で即座に `_select_target_*()` が攻撃ターゲットを返す → 現実的でない即時攻撃が発生する
- **解決策**: 発見ステップを `detection_step_map` に記録し、発見ステップ + **リアクション遅延（デフォルト 1 ステップ）** を経過するまで、そのターゲットへの攻撃を抑制する

### 17.2 設計方針

| 項目 | 内容 |
|---|---|
| リアクション遅延 | 固定 1 ステップ（= 0.1 秒）。将来はパイロットスキルで短縮予定 |
| 発見ステップ記録 | `detection_step_map[team_id][str(target_id)] = _step_count` |
| 攻撃可否チェック | `_step_count - detection_step >= reaction_delay` |
| 後方互換フォールバック | `detection_step_map` 未登録のターゲットは即時攻撃可能とみなす |

### 17.3 変更ファイル

#### `simulation.py` — `BattleSimulator.__init__()`

```python
# 発見ステップ記録: {team_id: {target_unit_id_str: step_count_at_detection}}
self.detection_step_map: dict[str, dict[str, int]] = {
    unit.team_id: {}
    for unit in self.units
    if unit.team_id is not None
}
```

#### `targeting.py` — `TargetingMixin`

**型宣言の追加（mypy 向け）:**

```python
detection_step_map: dict[str, dict[str, int]]
```

**`_process_single_detection()` — 発見時にステップを記録:**

```python
self.team_detected_units[unit.team_id].add(target.id)
self.detection_step_map[unit.team_id][str(target.id)] = self._step_count
```

**`_get_reaction_delay()` — リアクション遅延ステップ数を返す:**

```python
def _get_reaction_delay(self, actor: MobileSuit) -> int:
    base_delay: int = 1
    return base_delay
```

> 将来の拡張ポイント: パイロット REF/DEX ステータスや認識中の敵数による動的調整

**`_select_target_fuzzy()` / `_select_target_legacy()` — リアクション遅延チェック:**

```python
detection_steps = self.detection_step_map.get(actor.team_id, {})
reaction_delay = self._get_reaction_delay(actor)
detected_targets = [
    t
    for t in potential_targets
    if t.id in self.team_detected_units[actor.team_id]
    # detection_step_map に未登録（テスト等で手動追加）の場合は即時ターゲット可能とみなす
    and (self._step_count - detection_steps.get(str(t.id), self._step_count - reaction_delay)) >= reaction_delay
]
```

### 17.4 実行フロー（1 ステップの例）

```
step() 開始 (_step_count = N)
  │
  ├─ 1. _detection_phase()
  │     └─ 敵発見 → detection_step_map[team][enemy_id] = N
  │
  ├─ 3. _ai_decision_phase(unit)
  │     └─ _select_target_fuzzy(unit): N - N = 0 < 1 → ターゲット None
  │           └─ action = "MOVE" or "SEARCH"
  │
  ├─ 5. _action_phase(unit)
  │     └─ action != "ATTACK" → 攻撃しない
  │
  └─ 8. _step_count = N + 1

step() 開始 (_step_count = N+1)
  │
  ├─ 1. _detection_phase()
  │     └─ 既発見 → LOS チェックのみ（detection_step_map 更新なし）
  │
  ├─ 3. _ai_decision_phase(unit)
  │     └─ _select_target_fuzzy(unit): (N+1) - N = 1 >= 1 → ターゲット選択 OK
  │           └─ action = "ATTACK"
  │
  └─ 5. _action_phase(unit) → 攻撃実行 ✓
```

### 17.5 テストモック

リアクション遅延をスキップしてターゲット選択をテストする場合:

```python
# 決定論的に発見させ、リアクション遅延を経過させる
with patch("app.engine.targeting.random.random", return_value=0.0):
    sim._detection_phase()
sim._step_count += 1  # 発見ステップの次ステップに進める（リアクション遅延を経過）
```

> 後方互換フォールバック: `sim.team_detected_units[team].add(enemy.id)` で手動追加したターゲット（`detection_step_map` 未登録）は即時攻撃可能とみなされる。

### 17.6 後方互換性

- `detection_step_map` は `BattleSimulator.__init__()` で自動生成されるため、既存コードへの影響なし
- `detection_step_map` 未登録のターゲットへの攻撃は従来どおり即時可能（フォールバック）
- 既存テストで `sim.team_detected_units[team].add(target.id)` を手動で呼び出しているケースは `_step_count += 1` 不要

---

## 18. Issue #365: 攻撃中の慣性継続（静止禁止）+ 射撃反動アニメーション

### 18.1 概要

従来はユニットが攻撃射程内に入ると `_process_movement()` が呼ばれず、MSが完全に静止したまま攻撃し続けるという不自然な挙動があった。
Issue #365 では以下の2点を実装する。

1. **Backend:** 攻撃行動中（`ATTACK`/`BOOST_DASH` キャンセル後）も `_process_movement()` を呼び、慣性・ポテンシャルフィールドによる位置更新を継続する。
2. **Frontend:** 攻撃アクション中のユニットに射撃反動アニメーション（減衰振動）を適用する。

### 18.2 Backend: `action_handler.py` 変更点

`ActionHandlerMixin._action_phase()` の `ATTACK` 射程内ブランチと `BOOST_DASH` キャンセル後ブランチで、`_process_attack()` の直後に `_process_movement()` を追加した。

```python
# ATTACK 射程内ブランチ（変更後）
if weapon and distance <= weapon.range:
    self._process_attack(actor, target, distance, pos_actor, weapon)
    # 攻撃中も慣性を継続させるため移動処理を実行 (Issue #365/#366)
    self._process_movement(actor, pos_actor, pos_target, diff_vector, distance, dt, target=target)

# BOOST_DASH キャンセル後ブランチ（変更後）
if weapon and isinstance(weapon, Weapon) and distance <= weapon.range:
    self._process_attack(actor, target, distance, pos_actor, weapon)
    # ブーストキャンセル後も慣性を継続させる (Issue #365/#366)
    self._process_movement(actor, pos_actor, pos_target, diff_vector, distance, dt, target=target)
```

`_process_attack()` はアクターの位置を変更しないため、呼び出し前後の `pos_actor`/`diff_vector` は有効のまま `_process_movement()` に渡せる。

### 18.3 Frontend: 射撃反動アニメーション

**`useBattleEvents.ts`:**

返却型を `BattleEventsResult` インターフェースに変更し、`attackingUnitIds: Set<string>` を追加した。

```typescript
export interface BattleEventsResult {
    events: Map<string, BattleEventEffect | null>;
    attackingUnitIds: Set<string>; // ATTACK / MELEE_COMBO ログを出したユニット ID セット
}
```

**`MobileSuitMesh.tsx`:**

`isAttacking?: boolean` prop を追加し、`useFrame` で減衰振動アニメーションを実装。

```typescript
// 射撃反動アニメーション: 攻撃検出時にタイマーをリセットし、sin 波 × 線形減衰で振動
const RECOIL_DURATION = 0.25; // 秒
useFrame((_, delta) => {
    if (isAttacking) recoilTimeRef.current = RECOIL_DURATION;
    if (recoilTimeRef.current > 0) {
        recoilTimeRef.current = Math.max(0, recoilTimeRef.current - delta);
        const t = 1 - recoilTimeRef.current / RECOIL_DURATION;
        innerGroupRef.current.position.x = Math.sin(t * Math.PI * 5) * 0.12 * (1 - t);
    }
});
```

外側 `<group position={vec}>` は位置制御用のまま維持し、内側 `<group ref={innerGroupRef}>` に mesh コンテンツを移して反動オフセットを適用する。

---

## 19. Issue #366: 攻撃中の軌道旋回移動（ストレイフ）

### 19.1 概要

攻撃射程内でユニットが静止せず、ターゲットを中心に軌道を描くよう旋回（ストレイフ）する引力をポテンシャルフィールドに追加する。

- **発動条件:** `current_action == "ATTACK"` かつ距離 ≤ `weapon.range × STRAFE_MIN_RANGE_RATIO`
- **格闘武器は除外:** 体当たり系武器（`is_melee=True`）ではゼロベクトルを返す
- **旋回方向:** ユニット UUID の16進数ハッシュで決定論的に固定（`uid_int % 2 == 0` なら +1、奇数なら -1）

### 19.2 新規定数（`constants.py`）

```python
# 軌道旋回（ストレイフ）定数 (Issue #366)
STRAFE_ATTRACTION_COEFF: float = 1.0   # ストレイフ引力係数
STRAFE_MIN_RANGE_RATIO: float = 0.8    # 射程のこの割合以内のとき発動（0.8 = 射程の80%以内）
```

### 19.3 `_strafe_attraction()` メソッド（`movement.py`）

```python
def _strafe_attraction(self, unit: MobileSuit, target: MobileSuit) -> np.ndarray:
    """攻撃中の軌道旋回（ストレイフ）引力ベクトルを計算する (Issue #366)."""
    # 格闘武器はストレイフ不要
    weapon = unit.get_active_weapon()
    if weapon is None or getattr(weapon, "is_melee", False):
        return np.zeros(3)

    radial_vec = pos_unit - pos_target  # ターゲットからユニットへの方向（XZ 平面）
    # 射程の STRAFE_MIN_RANGE_RATIO 以内のときのみ発動
    if dist > float(weapon.range) * STRAFE_MIN_RANGE_RATIO:
        return np.zeros(3)

    # 上向きベクトルとのクロス積で接線ベクトル（XZ 平面の垂直方向）を計算
    up = np.array([0.0, 1.0, 0.0])
    tangent = np.cross(up, radial_vec / dist)

    # UUID ハッシュで旋回方向を固定
    uid_int = int(str(unit.id).replace("-", ""), 16)
    direction = 1 if uid_int % 2 == 0 else -1

    return STRAFE_ATTRACTION_COEFF * direction * tangent
```

### 19.4 ポテンシャルフィールドへの組み込み

`_calculate_potential_field()` でフランキング引力（#8）の直後に追加：

```python
# 9. ストレイフ引力（攻撃中・射程内・非格闘武器）(Issue #366)
if current_action == "ATTACK" and target is not None:
    total_force += self._strafe_attraction(unit, target)
```

### 19.5 ポテンシャルフィールド定数一覧（更新版）

| ソース | 種別 | 係数 | 条件 |
|--------|------|------|------|
| 攻撃対象の敵 | 引力 | `+2.0` | `ATTACK` かつターゲット選択済み |
| MOVE / RETREAT 行動時の最近敵 | 引力 | `+1.5` | `MOVE` / `RETREAT` |
| 攻撃範囲外の高脅威敵 | 斥力 | `1.5` | 脅威スコア > `0.5` かつ射程外 |
| 味方ユニット | 斥力 | `0.8` | 距離 ≤ `ALLY_REPULSION_RADIUS(150m)` |
| マップ境界 | 斥力 | `3.0` | 境界からの距離 < `BOUNDARY_MARGIN(200m)` |
| 撤退ポイント | 引力 | `+5.0` | `RETREAT` かつ撤退ポイント設定済み |
| 障害物 | 斥力 | `4.0` | 障害物から `radius + OBSTACLE_MARGIN` 以内 |
| フランキング | 引力（接線） | `+1.5` | フランキングスキル + 確率発動 |
| **ストレイフ** | **引力（接線）** | **`+1.0`** | **`ATTACK` かつ距離 ≤ `weapon.range × 0.8` かつ非格闘武器** |

---

## 20. Issue #385: 戦闘シミュレーション系テストの flaky 対策

### 20.1 概要

`backend/tests/unit` の戦闘シミュレーション系テストが、単体実行では成功するにもかかわらず `pytest tests/unit` でスイート全体を実行すると乱数依存で不定期に失敗する問題を修正した。

原因は主に2つ:

1. **グローバルな `random` モジュール状態のテスト間リーク**: 一部のテスト（例: `test_simulation.py` の `random.seed(12345)`）が明示的にシードを固定すると、それ以降に実行される全テストが同じ乱数列を引き継いでしまい、モンテカルロ的な確率アサーションの結果がテストの実行順序に依存して変化していた。
2. **確率アサーションのターン数不足**: 「N ターン以内に少なくとも1回発生すること」のようなアサーションで、ターン数の余裕が小さすぎて低確率ながら発生しないケースがあった。

### 20.2 対応内容

- `backend/tests/unit/conftest.py` に `autouse` の `_isolate_random_state` フィクスチャを追加し、各テスト実行前に `random.seed()`（引数なし = OS エントロピーで再初期化）を呼び出すことで、あるテストの乱数消費・明示的なシード固定が後続のテストへ波及しないようにした。
- モンテカルロ的アサーションを含むテスト（`test_boost_start_occurs_with_full_field` 等）は、1回の試行で低確率に失敗しうるため、複数回試行していずれかで期待する事象が発生することを確認する方式に変更した。
- 「N ターン以内に完了すること」を検証するテスト（`test_three_team_battle_runs_without_error` 等）は、ターン数に余裕を持たせる、または複数回試行に変更した。

### 20.3 今後のテスト作成における注意

- 戦闘シミュレーションの結果（命中・撃破・イベント発生など）を検証するアサーションは本質的に確率的である。1回の試行のみに依存する `assert` は避け、十分なターン数を確保するか、複数回試行して「いずれかで成立すること」を確認するパターンを使うこと。
- `random.seed()` をテスト内で明示的に呼び出す場合、`tests/unit/conftest.py` の `_isolate_random_state` フィクスチャにより次のテストへは影響しないが、同一テスト内での再現性が必要な場合を除き、テストコード側で無用な `random.seed()` 固定は避けることが望ましい。

### 20.4 Issue #387: `app.routes` 直接走査に依存したテストの脆弱性

`backend/tests` フル実行時に `AttributeError: '_IncludedRouter' object has no attribute 'path'` が偶発的に発生する問題を修正した。

- **原因**: `backend/requirements.txt` の `fastapi` にバージョン指定がなく、インストールタイミングにより取得されるバージョンが変わる。FastAPI 0.137 以降、`include_router()` で追加されたルーターが `app.routes` 内で遅延解決の `_IncludedRouter`（`.path` 属性を持たない）としてまとめて格納されることがあり、`route.path for route in app.routes` のように直接走査するコードが壊れる。
- **対応**: `tests/test_api_structure.py` / `tests/test_entry_feature.py` / `tests/test_ranking_system.py` で `app.routes` の直接走査をやめ、`app.openapi()["paths"].keys()` からエンドポイント一覧を取得するように変更した（FastAPI のバージョンに依存しない安定した方法）。
- **今後の注意**: 登録済みエンドポイントの存在を確認するテストは `app.routes` を直接走査せず、`app.openapi()["paths"]` を使うこと。

---

## 21. Issue: 初期配置での索敵回避 + スポーン時初速の付与

### 21.1 概要

Phase 6-3（§14）で導入したデフォルトスポーン領域の「チーム間距離の保証」は、
`sensor_range` の**デフォルト値（500m）を固定で 2 倍した 1000m** を基準にしており、
以下 2 点を考慮していなかった。

1. 実際に参加するユニットの `sensor_range`（NPC エースは最大 900m、ミッション設定次第ではさらに大きい値も取りうる）
2. スポーン領域自体の半径（中心間距離であって、ユニットが実際に出現しうる縁と縁の距離ではない）

その結果、Phase 6-5（§16）のフィールドスケーリングでユニット数が少なく
`MIN_FIELD_SIZE=2000m` にクランプされる戦闘（1 vs 1 のソロミッションなど、
最も頻度の高いケース）では、スポーン領域の縁と縁の距離が実際の `sensor_range` を
下回り、**戦闘開始直後から敵を発見できてしまう**ケースがあった。

あわせて、「ある程度の初速を持ってフィールドに侵入していく」というゲーム体験を
実現するため、スポーン時に各ユニットへ初速を付与するようにした。

### 21.2 索敵回避: フィールドサイズの動的拡張

`BattleSimulator.__init__()` で `battlefield` が明示的に渡され、かつ
`spawn_zones` が未指定（デフォルト自動生成が使われる）の場合、フィールド辺長を
以下の条件を満たすまで拡張する。

```
required_separation = max(全ユニットの sensor_range)
                       + SPAWN_DETECTION_SAFETY_MARGIN
                       + 2 × SPAWN_CENTER_JITTER_RADIUS
（異チームのスポーン領域は、中心間距離 − 両ゾーンの radius ≥ required_separation を満たす）
```

チーム配置ごとの必要フィールド辺長は `BattleSimulator._min_field_size_for_team_layout()`
で、`_generate_default_spawn_zones()` が生成する対称配置（2チーム: 対角、
3/4チーム: 均等分割、5チーム以上: 円周均等配置）それぞれの幾何から逆算する。

```python
# constants.py
SPAWN_ZONE_MAP_OFFSET: float = 500.0          # スポーン中心のマップ端からのオフセット (m)
SPAWN_DETECTION_SAFETY_MARGIN: float = 200.0  # 最大 sensor_range に上乗せする安全マージン (m)
```

> **障害物ジッターの考慮（Copilotレビュー指摘対応）**: 障害物が生成される場合、
> スポーン中心は `_find_clear_spawn_center()`（§14.4, #437）により最大
> `SPAWN_CENTER_JITTER_RADIUS`（300m）だけ障害物回避のためジッターしうる。
> 最悪ケース（異チームの2ゾーンが互いに近づく向きへジッター）でもガードが崩れない
> よう、`required_separation` には両ゾーン分（`2 × SPAWN_CENTER_JITTER_RADIUS`）を
> 追加で上乗せしている。`test_2team_spawn_zones_guarantee_detection_safety_with_obstacle_jitter`
> （`obstacle_density="DENSE"` で複数回試行）で回帰を検証する。

`side_len` は「ユニット数に応じた面積ベースの辺長（Phase 6-5, §16.2）」と
「索敵回避に必要な辺長」の**大きい方**を採用し、`MAX_FIELD_SIZE` でクランプする。
チーム数が多い・`sensor_range` が非常に大きいなどの理由で `MAX_FIELD_SIZE` を
超えてしまう場合は、警告ログを出したうえでベストエフォートでフィールド上限まで
拡張する（保証を満たせない旨をログで明示する）。

> **注意**: `battlefield=None`（後方互換モード）や `spawn_zones` を明示的に渡した場合は、
> このフィールド拡張は行われない（呼び出し側が意図した配置をそのまま尊重する）。

### 21.3 スポーン時初速の付与

`BattleSimulator._apply_spawn_zones()` で、各ユニットの位置決定後に
「スポーン領域中心 → フィールド中心」方向への初速を付与する。

```python
# constants.py
SPAWN_INITIAL_SPEED_RATIO: float = 0.3  # 初速 = 各ユニットの max_speed × この比率
```

- `unit.velocity`（API/フロントエンド向けスナップショット）と
  `unit_resources[unit_id]["velocity_vec"]`（実シミュレーションが参照する内部状態）の
  両方に同じ初速ベクトルを設定する
- `movement_heading_deg` / `body_heading_deg` も初速の向きに合わせて初期化する
- フィールド中心とスポーン領域中心が一致する場合（実質的に発生しない想定だが）は
  ゼロベクトルにフォールバックする
- `battlefield=None`（後方互換モード）の場合は初速も付与されない（`unit.velocity` はゼロのまま）

### 21.4 テスト

`backend/tests/unit/test_spawn_detection_avoidance.py`

- 2〜5 チームの各配置で、スポーン領域の縁と縁の距離が
  `sensor_range + SPAWN_DETECTION_SAFETY_MARGIN` 以上であること
- `MIN_FIELD_SIZE` クランプ対象の少人数戦でもフィールドが拡張されること
- 明示的な `spawn_zones` を渡した場合はフィールド拡張が行われないこと
- スポーン直後のユニットが `max_speed × SPAWN_INITIAL_SPEED_RATIO` の初速を持ち、
  フィールド中心方向を向いていること

## 22. Issue #446: 索敵・ターゲット選定処理のO(N²)最適化（グリッド分割）

### 22.1 概要

`room_size` を 8 機から 50〜100 機規模へ拡大した際、索敵フェーズ
（`_detection_phase()`）とターゲット選定（`_select_target_legacy` /
`_select_target_fuzzy`）が全ユニット総当たり（O(N²)）で実装されていたため、
演算量が参加ユニット数の増加に対して急激に増加する問題があった。中規模・大規模
バトル対応の前提として、空間分割（グリッド）による絞り込みで総当たりを解消した。

### 22.2 索敵フェーズ: グリッド分割による近傍探索

`app/engine/spatial_grid.py` に `UnitSpatialGrid` を追加した。ユニット位置を
セルサイズ = 「そのステップで有効な最大索敵範囲」のグリッドに分類し、あるユニット
のセルとその近傍26セル（3x3x3）だけを走査することで、索敵範囲外にいるユニットとの
無駄な距離判定・LOS判定を避ける（セル幅 ≥ 探索半径であれば、2セル以上離れた
セル間の最短距離はセル幅以上になるため、3x3x3の走査範囲外は距離的に候補になり
得ないという性質を利用している）。

`_detection_phase()` は以下の2種類の候補を分けて処理する。

1. **既に発見済みの敵**（`team_detected_units[team_id]`）: 索敵範囲外に出ていても
   LOS 喪失判定（障害物の陰に入った場合に発見済みリストから除外する挙動）のため、
   距離に関わらず引き続き処理する（従来の挙動を維持。Issue #446 のIMPORTANT注記
   通り、この経路は新規実装しない）
2. **未発見の敵**: グリッドで絞り込んだ近傍候補のみを対象に新規索敵判定を行う

ユニットID→ユニットの引き当ては `BattleSimulator._units_by_id`（`__init__` で
一度だけ構築）を使い、`self.units` を毎回線形走査しない。

### 22.3 ターゲット選定: 索敵フェーズの絞り込み結果を再利用

`_select_target_legacy` / `_select_target_fuzzy` は、行動ユニットごとに
`self.units`（両陣営含む全ユニット）を毎回フィルタして候補リストを作り直して
いたため、索敵フェーズの絞り込みと合わせて二重の総当たりになっていた。共通処理を
`TargetingMixin._get_detected_targets()` に切り出し、`team_detected_units`
（索敵フェーズが既に絞り込んだ、自チームが発見済みの敵IDの集合）を直接ソースと
して使うことで、`self.units` の全件走査を撤廃した。候補の並び順は
`BattleSimulator._unit_order_index`（`self.units` 内での出現順、`__init__` で
一度だけ構築）でソートし、`min()`/`max()` によるタクティクス選択の同点時
タイブレークが従来の走査順と一致するようにしている。

戦術ロジック自体（WEAKEST/STRONGEST/THREAT/RANDOM/CLOSEST のスコア計算、
ファジィ推論によるスコアリング）は変更していない。あくまで「候補リストの
作り方」のみを最適化しており、命中率・ターゲット選定結果の傾向は変化しない。

### 22.4 `has_los()` の計算量について

`combat.py` の `has_los()`（3D Ray-Sphere交差判定）は障害物リストに対して線形
走査するが、計算量はユニット数 N ではなく障害物数に依存する。障害物数はユニット数
と独立してほぼ一定（`OBSTACLE_GRID_PARAMS` による密度設定）のため、本Issueの
スコープであるユニット数 N に対する O(N²) 解消の対象外と判断し、変更していない。

### 22.5 ベンチマーク

`backend/scripts/simulation/sim_scale_bench.py` で、DBを使わず合成ユニット
（8/50/100機、2チーム均等割り）を生成し `BattleSimulator.step()` 1回あたりの
平均処理時間を計測できる。

```bash
python scripts/simulation/sim_scale_bench.py --sizes 8,50,100 --steps 50
```

### 22.6 テスト

- `backend/tests/unit/test_los_obstacle.py`: LOS遮蔽時の索敵ブロック・
  既発見済みユニットのLOS喪失時の除外がグリッド分割後も維持されていることを確認
  （既存テストがそのままパスすることで担保）
- 既存の `tests/unit` 全体（索敵・ターゲット選定に関するテストを含む）が
  グリッド分割導入後もすべてパスすることを確認済み
- `unit_resources["velocity_vec"]` が `unit.velocity` と一致すること
- `battlefield` 未指定時は初速が付与されないこと（後方互換性）

`backend/tests/unit/test_field_scaling.py` / `test_phase_6_3_field_init.py` の
既存テストは、上記のフィールド拡張ロジックを踏まえて期待値・テストユニットの
`sensor_range` を見直した（実際の索敵回避フロアが支配的にならないよう、
検証したい観点に応じて `sensor_range` を明示するよう変更）。

## 23. Issue #447: スポーン位置サンプリングの準O(N²)最適化（グリッド分割）

### 23.1 概要

`room_size` を 50〜100 機規模へ拡大した際、スポーン位置サンプリング
（`_sample_position_in_zone()`）がユニット配置のたびに既配置ユニット全件との
距離を線形走査していたため、Issue #446 で解消した索敵・ターゲット選定と同様に
演算量がユニット数の増加に対して急激に増加する問題があった（配置済み1機ごとに
`SPAWN_ZONE_SAMPLE_MAX_TRIES × 3` 回の距離判定が発生し、これが未配置ユニット
すべてに対して繰り返されるため準O(N²)）。`_find_clear_spawn_center()`
（障害物回避のためのゾーン中心探索）は元々チーム数単位のループでボトルネックに
なりにくいため対象外とし、`_sample_position_in_zone()` のみを対象に最適化した。

### 23.2 `PointSpatialGrid`: 逐次追加可能な点群グリッド

`app/engine/spatial_grid.py` に、Issue #446 の `UnitSpatialGrid` と同じ理屈
（セル幅 ≥ 探索半径であれば3x3x3近傍セルの走査だけで漏れなく候補を捕捉できる）
を使う `PointSpatialGrid` を追加した。`UnitSpatialGrid` は「全ユニットが揃った
状態で一括構築し、以降は読み取り専用」という索敵フェーズの用途に特化していたが、
スポーン配置ではユニットを1体ずつ配置しながら「既配置点のうち一定距離以内に
別の点がないか」をその都度判定する必要があるため、`insert()` による逐次追加を
サポートする別クラスとして実装した（対象も `MobileSuit` ではなく生の
`np.ndarray` 座標）。

セルサイズは呼び出し側（`_apply_spawn_zones()`）が `ALLY_REPULSION_RADIUS`
（緩和が起きる前の最大 min_dist）で固定して構築する。`_sample_position_in_zone()`
内で試行を重ねるたびに `current_min_dist` を段階的に緩和していくが、セルサイズは
常にその時点の `current_min_dist` 以上であるため、近傍セル探索だけで漏れなく
判定できるという前提は緩和後も崩れない。

### 23.3 `_apply_spawn_zones()` / `_sample_position_in_zone()` の変更

チームごとに配置ループを回す `_apply_spawn_zones()` は、従来 `list[np.ndarray]`
に配置済み位置を追記して `_sample_position_in_zone()` へ丸ごと渡していたが、
チームごとに `PointSpatialGrid(cell_size=ALLY_REPULSION_RADIUS)` を1つ構築し、
ユニットを配置するたびに `grid.insert(pos)` で追加する方式に変更した。
`_sample_position_in_zone()` 側も引数を `placed_positions: list[np.ndarray]` から
`placed_grid: PointSpatialGrid` に変更し、候補点との距離判定は
`placed_grid.neighbors(pos)`（近傍セルのみ）に対してのみ行う。

円内一様サンプリング・段階的な min_dist 緩和・最終フォールバック（中心座標を返す）
といったアルゴリズム自体は変更していないため、配置結果の分布・重なり回避の
挙動は最適化前と同一である。

### 23.4 ベンチマーク

`backend/scripts/simulation/spawn_scale_bench.py` で、DBを使わず合成ユニット
（8/50/100機、2チーム均等割り）を生成し `BattleSimulator` 初期化
（障害物生成 + スポーン領域決定 + スポーン配置）1回あたりの平均処理時間を
計測できる。`--obstacle-density` で障害物密度を切り替え、リトライ回数増加時の
挙動も確認できる。

```bash
python scripts/simulation/spawn_scale_bench.py --sizes 8,50,100 --repeats 20
python scripts/simulation/spawn_scale_bench.py --obstacle-density DENSE
```

最適化前後の比較（`obstacle_density=MEDIUM`、synthetic 2チーム構成、
`repeats=10` の平均）:

| room_size | 最適化前 (sec/spawn) | 最適化後 (sec/spawn) |
|---|---|---|
| 8   | 0.0033 | 0.0034 |
| 50  | 0.0267 | 0.0151 |
| 100 | 0.1468 | 0.0621 |
| 200 | 0.8838 | 0.3282 |

ユニット数が増えるほど改善幅が拡大しており、準O(N²)構造の解消を確認できる。

### 23.5 テスト

- `backend/tests/unit/test_spatial_grid.py`: `PointSpatialGrid` の
  挿入・近傍探索（同一セル / 隣接セル / 2セル以上離れた点の除外 / 逐次追加）を
  `UnitSpatialGrid` と同様の観点で単体検証
- `backend/tests/unit/test_phase_6_3_field_init.py`:
  50機・障害物なしでのゾーン内収容 + 間隔保証、100機・障害物ありでの
  クラッシュなし + ゾーン内収容を追加検証（AC の「50/100機規模」要件に対応）
- 既存の `tests/unit` 全体（8機・障害物ありのケースを含むスポーン関連テスト）が
  最適化後もすべてパスすることを確認済み

## 24. Issue #450: ポテンシャルフィールド計算処理のO(N²)最適化（グリッド分割）

### 24.1 概要

Issue #446/#447 と同様、`app/engine/movement.py` の `_calculate_potential_field()`
（行動ユニットごとに毎ステップ呼ばれる）が内部で呼ぶ `_ally_repulsion()` /
`_closest_enemy_attraction()` / `_threat_enemy_repulsion()` は `self.units` を毎回
線形走査しており、O(N²)構造だった。`room_size` を50〜100へ拡大する前提として、
`_ally_repulsion()` / `_closest_enemy_attraction()` の2関数を `UnitSpatialGrid`
ベースに書き換えた。

### 24.2 `_ally_repulsion()`: 固定半径カットオフによる3x3x3近傍探索

`ALLY_REPULSION_RADIUS`（150m固定）というカットオフが既にあるため、セルサイズ =
`ALLY_REPULSION_RADIUS` の `UnitSpatialGrid.neighbors()`（3x3x3近傍走査）にそのまま
置き換えた。

### 24.3 `_closest_enemy_attraction()`: `UnitSpatialGrid.nearest()` による環状探索

MOVE行動時の「最も近い敵」はグローバルな最近傍である必要があり、`neighbors()` の
固定3x3x3走査だけでは「近傍セルに敵が一体もいない場合、本来の最近敵を見逃す」ケースが
発生しうる。`UnitSpatialGrid` に `nearest(pos, predicate)` を新設し、近傍セルに候補が
いない場合は探索半径（セル単位）を1段ずつ外側へ広げる環状探索を実装した。ある半径 `r`
まで走査を終えた時点で見つかっている最小距離が `r * cell_size` 以下なら、未走査のセルに
それより近い候補は存在し得ないため、その時点で打ち切る（`UnitSpatialGrid` の「セル幅 ≥
探索半径なら3x3x3近傍走査で漏れなく捕捉できる」という前提を任意半径に一般化した性質）。

殻（半径 `r` の外周セル）は `_shell_offsets()` で直接 O(r²) 生成する。「半径 `r` の
立方体全体をO(r³)でループしてフィルタする」実装は一見自然だが、探索半径が伸びるケースで
無駄な走査コストが急増するため避けている（詳細は `backend/CLAUDE.md` 参照）。

### 24.4 `_threat_enemy_repulsion()` は対象外（挙動を変えずには最適化できない）

`_threat_enemy_repulsion()` の斥力式は `dist >= 1.0` の範囲で距離によらずほぼ一定の
大きさになる、つまり実質的に距離減衰がない設計になっている。近傍セルへの絞り込みや
早期打ち切りは遠方の高脅威敵からの斥力を消してしまい挙動を変えるため、`_ally_repulsion`/
`_closest_enemy_attraction` と異なり本Issueのスコープ外とした。挙動変更を許容した上での
対応は Issue #453 に切り出した（→ 25章）。

### 24.5 グリッドの構築タイミング: 1ステップに1回だけキャッシュ

`_calculate_potential_field()` は行動ユニットごとに呼ばれるため、`BattleSimulator._movement_grid`
でグリッドを遅延構築・キャッシュし、同一ステップ内の呼び出しでは使い回す。`step()` の
冒頭で毎ステップ `self._movement_grid = None` にリセットし、次のステップでは最新位置から
再構築する。これにより、同一ステップ内で先に行動したユニットの移動後の位置がグリッドに
即座には反映されないという最適化前との差異が生じるが、1ステップの移動量はセルサイズ
（150m）よりはるかに小さく、実測（後述）でも有意な挙動差は確認されなかった。

### 24.6 ベンチマークと挙動比較

`sim_scale_bench.py --sizes 8,50,100 --steps 50` の結果（最適化前 → 最適化後）:

| room_size | 最適化前 (sec/step) | 最適化後 (sec/step) |
|---|---|---|
| 8   | 0.0012 | 0.0164 |
| 50  | 0.2129 | 0.1973 |
| 100 | 1.4266 | 1.4360 |

`room_size=50/100`（本Issueが本来想定するスケール）では明確な改善は見られなかった。
`cProfile` で再計測したところ、`room_size=50/100` では `FuzzyEngine` の推論処理
（`_clip_and_combine()`/`evaluate()` 系）が `step()` 全体の80〜90%を占めており、
`_select_target_fuzzy()` の重複呼び出し・ファジィ推論コストが支配的なボトルネックで
あることを再確認した（Issue #446 対応時の所見と一致）。本Issueのポテンシャルフィールド
最適化はこのスケールでは補助的な位置づけであり、体感できる改善には Issue #454
（ファジィ推論コストの削減）が必要になる。

`room_size=8` は最適化前のO(N)総当たり（N=8なら数マイクロ秒オーダー）と比べてグリッド
構築・環状探索の定数コストが相対的に重くなり、絶対値としては遅くなる（0.0012s→0.0164s）。
1ステップあたり十数msのオーダーであり、実運用（最大数百ステップ程度のバトル）で体感できる
遅延にはならないと判断した。

8機（1v7）バトルでの挙動比較は `sim_bench.BenchRunner`（150ラウンド、完全ランダム、
Issue #446 のPR #449と同一手法）で実施した:

| | 最適化前 | 最適化後 |
|---|---|---|
| win_counts | PLAYER:0 / ENEMY:150 / DRAW:0 | PLAYER:0 / ENEMY:150 / DRAW:0 |
| 平均戦闘時間 | 6.6s | 6.4s |
| ATTACK比率 | 1.9% | 2.0% |
| MISS比率 | 6.0% | 6.0% |
| MOVE比率 | 91.9% | 91.8% |
| 平均撃墜数（両チーム） | 1.0 | 1.0 |

勝敗分布は完全一致、行動分布も同水準で有意な傾向の変化は確認されなかった。

### 24.7 テスト

- `backend/tests/unit/test_spatial_grid.py`: `UnitSpatialGrid.nearest()` の環状探索を
  単体検証（同一セル内候補・空グリッド・述語に一致する候補が存在しない場合の`None`返却・
  近傍セルに候補がいない場合の遠方セル捕捉・「最初に見つかったセルの候補」ではなく
  真にグローバルな最近傍を選ぶこと・述語フィルタ・ランダム配置でのO(N)総当たりとの
  厳密一致）
- 既存の `tests/unit` 全体（`test_potential_field.py` を含む）が最適化後もすべてパス
  することを確認済み

## 25. Issue #453: 高脅威敵斥力の距離減衰導入とO(N²)対策

### 25.1 概要

24章（Issue #450）でスコープ外とした `_threat_enemy_repulsion()`（高脅威敵・自機射程外
への斥力）に、挙動変更を許容した上で距離減衰を導入し、`UnitSpatialGrid` によるグリッド化
（早期打ち切り）を行った。

### 25.2 距離減衰式

旧式 `1.5 * (-vec_to_enemy) / max(dist, 1.0)` は `vec_to_enemy` の大きさが `dist` に
等しいため、`dist >= 1.0` の範囲で距離によらずほぼ一定の大きさ（正規化ベクトル）になる、
実質的に距離減衰のない設計だった。新式では `THREAT_REPULSION_DECAY_SCALE`
（既定300m、`app/engine/constants.py`。典型的な武器射程の下限帯に合わせた基準値）を
導入し:

```
decay = (THREAT_REPULSION_DECAY_SCALE / max(dist, THREAT_REPULSION_DECAY_SCALE)) ** 2
force += THREAT_ENEMY_REPULSION_COEFF * decay * (-vec_to_enemy) / max(dist, 1.0)
```

- `dist <= THREAT_REPULSION_DECAY_SCALE`: `decay = 1` となり旧式と同じ一定の斥力
  （`THREAT_ENEMY_REPULSION_COEFF = 1.5`）を維持する
- `dist > THREAT_REPULSION_DECAY_SCALE`: `decay = (THREAT_REPULSION_DECAY_SCALE / dist) ** 2`
  となり、大きさが `THREAT_ENEMY_REPULSION_COEFF * (THREAT_REPULSION_DECAY_SCALE / dist) ** 2`
  （1/dist^2 に比例）で減衰する

`max(dist, 1.0)` のクランプは維持しており、近距離での発散は起きない。減衰指数を
1乗ではなく2乗にしている理由は25.3節参照。

### 25.3 早期打ち切り半径とグリッド化

早期打ち切り半径 `THREAT_REPULSION_CUTOFF_RADIUS`（既定 `300 * sqrt(20)` ≈ 1342m）は、
斥力の大きさが基準係数 `THREAT_ENEMY_REPULSION_COEFF` の5%未満まで減衰する距離を
基準に設定した。

**この半径での近傍探索には、セルサイズを `THREAT_REPULSION_DECAY_SCALE`（300m）に
固定した専用の `UnitSpatialGrid`（`MovementMixin._get_threat_repulsion_grid()`）と、
`UnitSpatialGrid.radius_neighbors(pos, radius)`（本Issueで新設、`nearest()` と同じ
殻走査 `_shell_offsets()` を使い、走査半径だけをセル単位で動的に広げる）を組み合わせて
使う。** 24章の `_get_movement_grid()`（セルサイズ=`ALLY_REPULSION_RADIUS`=150m）とは
セルサイズ・カットオフ半径の前提が異なるため、共有せず別グリッドとして保持している
（`_movement_grid` と同様、`step()` の冒頭で毎ステップ `self._threat_repulsion_grid = None`
にリセットされ、次のステップで最新位置から再構築）。

#### 初期実装の罠: セルサイズ=カットオフ半径にすると絞り込みが効かない（PR #456 の Copilot レビュー指摘）

初期実装では、減衰指数を1乗（1/dist）のまま `THREAT_REPULSION_CUTOFF_RADIUS` を計算し
（同じ5%基準で `20 * 300m = 6000m`）、この6000mを**そのまま `UnitSpatialGrid` のセルサイズ**
として使い、既存の `neighbors()`（3x3x3固定走査）で候補を絞り込んでいた。しかし
`MAX_FIELD_SIZE=8000m` に対してセルサイズ6000mは大きすぎ、フィールド全体がわずか
1〜2セルに収まってしまうため、3x3x3走査が実質的に全ユニットを返す退化が起きていた
（見た目はグリッド化されているが、実態は各ユニットごとに全ユニットを走査するのと
ほぼ同じでO(N²)のままだった）。

この点はPR #456 のCopilotレビューで指摘され、以下のように修正した:

1. 減衰指数を1乗→2乗にして、同じ「基準係数の5%未満」という打ち切り基準でも
   カットオフ半径を6000m→約1342mへ大幅に縮小
2. `UnitSpatialGrid.radius_neighbors()` を新設し、セルサイズは
   `THREAT_REPULSION_DECAY_SCALE`（300m）という小さい値に固定したまま、殻走査で
   カットオフ半径まで動的に走査範囲を広げる方式に変更

**教訓: グリッド系の近傍探索を新規実装する際、「セルサイズを探索したい最大距離に
合わせる」という直感的なアプローチは、その距離がフィールドサイズに対して大きい場合に
容易に退化する。** セルサイズは索敵グリッド（Issue #446）や `ALLY_REPULSION_RADIUS`
グリッド（Issue #450）のように「実際に細かく分割できる小さな値」に固定し、探索したい
半径が大きい場合は `nearest()`/`radius_neighbors()` のような殻走査で対応するのが
正しいパターン。

### 25.4 ゲームバランスへの影響（`sim_bench.BenchRunner` 実測）

8機（4vs4）バトルを2つの乱数シードで実行し、導入前後を比較した（数値は2乗減衰への
修正後の最終版）:

| seed | ラウンド数 | 導入前 win_counts | 導入後 win_counts | 導入前 平均戦闘時間 | 導入後 平均戦闘時間 |
|---|---|---|---|---|---|
| 453 | 50 | PLAYER 1 / ENEMY 49 / DRAW 0 | PLAYER 18 / ENEMY 30 / DRAW 2 | 54.98s | 25.01s |
| 123 | 20 | PLAYER 0 / ENEMY 20 / DRAW 0 | PLAYER 0 / ENEMY 20 / DRAW 0 | 15.14s | 14.80s |

seed=123 はユニット性能差自体で一方的な結果になる組み合わせで、斥力式変更による差は
ほぼ無かった。一方 seed=453 では、導入前は劣勢側が「射程外の高脅威敵から無限遠まで
一定の力で逃げ続ける」ため戦闘に参加できず一方的に負け続けていたが、導入後は逃げの
強制力が現実的な距離帯（数百m）に収まり、勝率の偏りが大幅に緩和され（1-49→18-30-2）、
平均戦闘時間もほぼ半減した（55s→25s）。この変更は最適化に留まらず、旧実装の
「非減衰・無限遠まで一定」という設計自体が組み合わせ次第で一方的な不均衡を生む
要因になっていたことを示す結果となった（1乗減衰版では25-23-2とさらに互角に近かったが、
Copilotレビュー対応でカットオフ半径を現実的な大きさに縮めるため2乗減衰に変更した結果、
遠距離での減衰がやや強まり分布はやや偏りが戻った。それでも導入前の1-49と比べれば
明確な改善）。

### 25.5 パフォーマンスへの影響（`sim_scale_bench.py` 実測）

`sim_scale_bench.py --sizes 8,50,100 --steps 50` の結果（導入前 → 導入後）:

| room_size | 導入前 (sec/step) | 導入後 (sec/step) |
|---|---|---|
| 8   | 0.0160 | 0.0239 |
| 50  | 0.1982 | 0.2220 |
| 100 | 1.3269 | 1.4487 |

絶対値としてはやや増加している。`radius_neighbors()` の殻走査はセルサイズを小さく
保つ代償として、実際の候補数が少ない場合でも走査半径分のセルを律儀に辿るための
固定オーバーヘッドを持つため（本ベンチのユニット配置は均一分散でカットオフ半径内の
密度が低く、真の絞り込み効果が体感しにくいケース）。ただし `_select_target_fuzzy()`
のファジィ推論コストが `room_size=50/100` の80〜90%を占めるという既知の支配的
ボトルネック（24章参照）を踏まえると、この増分（10〜20%程度）はステップ全体で見れば
無視できる範囲であり、本Issueの主目的（無限遠まで一定という非現実的な挙動の解消と、
ユニット密度が高い場面で発生しうる真のO(N²)の解消）は達成できている。

### 25.6 テスト

`backend/tests/unit/test_potential_field.py` に以下を追加した:

- `test_threat_enemy_repulsion_no_decay_within_scale`: `THREAT_REPULSION_DECAY_SCALE`
  以内では距離によらず基準係数どおりの一定斥力になること
- `test_threat_enemy_repulsion_decays_beyond_scale`: `THREAT_REPULSION_DECAY_SCALE` を
  超えると 1/dist^2 で減衰すること
- `test_threat_enemy_repulsion_cutoff_beyond_radius`: `THREAT_REPULSION_CUTOFF_RADIUS`
  を超えた高脅威敵からは斥力が働かないこと

`backend/tests/unit/test_spatial_grid.py` に `UnitSpatialGrid.radius_neighbors()` の
テストを追加した:

- `test_radius_neighbors_empty_grid_returns_nothing`: 空グリッドでは常に空を返すこと
- `test_radius_neighbors_finds_unit_far_beyond_single_cell`: セルサイズより大きい
  半径でも、セルサイズを固定したまま半径内の候補を拾えること
- `test_radius_neighbors_matches_brute_force_over_random_layout`: ランダム配置において、
  半径内の集合がO(N)総当たりの結果を過不足なく含むこと（セル単位の過剰検出はありうる
  前提で、厳密な距離判定は呼び出し側の責務とする設計を検証）

既存の `tests/unit` 全体（750件）が変更後もすべてパスすることを確認済み。

## 26. Issue #454: ターゲット選定のファジィ推論コスト削減（重複呼び出し排除・キャッシュ）

### 26.1 概要

22章（Issue #446）〜25章（Issue #453）の一連の対応で候補列挙（索敵・ターゲット選定・
ポテンシャルフィールド計算）のO(N²)構造は解消したが、`room_size=50/100` 規模で
`cProfile` により再計測したところ、依然として `BattleSimulator.step()` の80〜90%を
`FuzzyEngine` の推論処理（`infer_with_debug()` / `_centroid_for_variable()` を含む重心デファジィフィケーション）が占めていた。
本Issueはこの真のボトルネックに直接対応する。

原因は2つある:

1. `_select_target_fuzzy()`（`targeting.py`）が1ユニット・1ステップあたり最大3回
   呼ばれる（`ai_decision.py` から2回、`action_handler.py` から1回）。呼び出しの間で
   実際に状態が変わるかを調査せず毎回フルにファジィ推論をやり直していた
2. 索敵済み候補1件ごとに `FuzzyEngine.infer_with_debug()`（重心デファジフィケーション、
   200点の数値積分）を実行しており、候補数が増えるほどコストが積み上がる

### 26.2 `_select_target_fuzzy()` の呼び出し元調査と結論

`app/engine/simulation.py` の `step()` は次の順でフェーズを実行する:

```
1. _detection_phase()            索敵
2. _strategy_phase()             戦略評価（ユニットごとに1回のみ）
3. _ai_decision_phase(unit) ×N   [呼び出し1] angle_to_target 計算用
4. _update_body_heading(unit,dt) ×N  [呼び出し2] ATTACK/ENGAGE_MELEE 時のみ
5. _action_phase(unit, dt) ×N    [呼び出し3] 実際の攻撃・移動対象決定
6. _retreat_check_phase()
7. _refresh_phase(dt)
```

呼び出し1（フェーズ3）と呼び出し2（フェーズ4）の間では、HP・位置・武器クールダウンの
いずれも変化しない（ダメージ・移動処理はすべてフェーズ5に閉じている）。一方、呼び出し3
（フェーズ5）は行動ユニットごとに逐次実行され、**同一ステップ内で先に処理されたユニットの
攻撃・移動が、まだ処理されていない後続ユニットの候補（HP・位置）に影響しうる**。つまり
呼び出し1・2はステップ内で安全に結果を共有できるが、呼び出し3の時点では対象が既に
撃破されている可能性がある。

### 26.3 実装: ステップ内キャッシュ + 撃破時の即時無効化

`TargetingMixin._select_target_fuzzy()` をキャッシュ付きの薄いラッパーにし、実処理は
`_select_target_fuzzy_uncached()` に切り出した（`app/engine/targeting.py`）。

```python
def _select_target_fuzzy(self, actor):
    unit_id = str(actor.id)
    cached = self._fuzzy_target_cache.get(unit_id)
    if cached is not None:
        cached_step, cached_target = cached
        if cached_step == self._step_count and (
            cached_target is None or cached_target.current_hp > 0
        ):
            return cached_target
    target = self._select_target_fuzzy_uncached(actor)
    self._fuzzy_target_cache[unit_id] = (self._step_count, target)
    return target
```

- キャッシュキーは `unit_id`、値は `(計算時点の _step_count, 選択結果)`。ステップが
  進めば `_step_count` が変わるため、明示的なキャッシュクリアは不要（`_movement_grid`
  のような毎ステップリセットは行っていない）
- キャッシュ対象のターゲットが撃破されていた場合（`current_hp <= 0`）は、上記26.2の
  リスクに対応するため無条件で再計算する。これにより「フェーズ5で先行ユニットに
  倒された相手をキャッシュ経由で攻撃対象にし続ける」誤りを防ぐ
- 位置変化（フェーズ5内の移動）による候補スコアの微小な差異はキャッシュ後も残り得るが、
  26.5節の実測で勝敗・撃墜数分布への有意な影響がないことを確認した

`_select_target_fuzzy()` は呼び出しのたびに `_log_target_selection()` でログを記録する
実装だったため、キャッシュヒット時はログを追加しない（毎ステップ最大1回のログになる）。
既存テスト `test_select_target_fuzzy_logs_fuzzy_scores_in_target_selection` は
`len(target_logs) >= 1` という緩い条件で検証しており、この変更と両立する。

### 26.4 `FuzzyEngine` の重心デファジフィケーションを numpy でベクトル化

`_centroid_for_variable()` は「200点のサンプル点 × 発火中の集合数」を Python の
ネストしたループで評価しており（`_clip_and_combine()` が各サンプル点ごとに毎回
呼ばれ、その中でさらに集合ごとに `MembershipFunction.evaluate()` を呼ぶ）、この
Python レベルのループそのものがホットパスだった。`MembershipFunction` に配列版の
`evaluate_array()`（`TriangleMF`/`TrapezoidMF` で numpy の `np.where` を使い実装）を
追加し、`_centroid_for_variable()` を次のようにベクトル化した:

```python
xs = x_min + (np.arange(_DEFUZZ_RESOLUTION) + 0.5) * step
mu_combined = np.zeros(_DEFUZZ_RESOLUTION)
for set_name, activation in set_activations.items():
    if activation <= 0.0 or set_name not in mf_sets:
        continue
    mu_clipped = np.minimum(mf_sets[set_name].evaluate_array(xs), activation)
    np.maximum(mu_combined, mu_clipped, out=mu_combined)
area_sum = float(mu_combined.sum())
weighted_sum = float(np.dot(xs, mu_combined))
```

Python ループが「200点 × 発火集合数」から「発火集合数」（サンプル点はnumpy配列演算に
まとめて処理）に減り、数式自体は変更していないため出力値は変わらない（`infer()`/
`infer_with_debug()` の既存テストはすべて相対比較・型検証で、厳密な数値一致を
要求しておらずすべてパスする）。

`infer()` と `infer_with_debug()` は元々 `_fuzzify()`/`_evaluate_rules()`/
`_defuzzify_centroid()` という同一の内部処理を呼んでおり、両者の差は返り値に
`fuzzified`/`activations` の参照を含めるかどうかだけ（新たなコピーは発生しない）
だったため、「デバッグ情報の取得を分離する」こと自体による追加の高速化効果はない
と判断した（`infer()` を候補ループで使い `infer_with_debug()` を勝者だけに使う
実装にすると、勝者について推論を2回実行することになりむしろ悪化する）。実際の
コストは重心デファジフィケーションのアルゴリズム自体にあったため、本Issueでは
そちらのベクトル化を対応の中心とした。

### 26.5 パフォーマンスへの影響（`sim_scale_bench.py` 実測）

`sim_scale_bench.py --sizes 8,50,100 --steps 50` の結果（25章時点の最新状態 → 本Issue後）:

| room_size | 対応前 (sec/step) | 対応後 (sec/step) | 倍率 |
|---|---|---|---|
| 8   | 0.0239 | 0.0177 | 1.4x |
| 50  | 0.2220 | 0.0449 | 4.9x |
| 100 | 1.4487 | 0.1937 | 7.5x |

本Issueが狙う `room_size=50/100` 規模で大幅な改善が確認できた。`cProfile`
（`room_size=50`, 30ステップ）でも `FuzzyEngine.infer_with_debug()` の累積時間比率が
80〜90%から約34%まで低下したことを確認した（`radius_neighbors()`（25章）が次点の
コストとして相対的に浮上している）。

### 26.6 ゲームバランスへの影響（`sim_bench.BenchRunner` 実測）

8機（4vs4、味方3+敵4体制の合成ユニット）バトルを2つの乱数シードで各30ラウンド実行し、
対応前後を比較した:

| seed | 対応前 win_counts | 対応後 win_counts | 対応前 DESTROYED数 | 対応後 DESTROYED数 |
|---|---|---|---|---|
| 453 | PLAYER 17 / ENEMY 12 / DRAW 1 | PLAYER 13 / ENEMY 14 / DRAW 3 | 126 | 129 |
| 123 | PLAYER 16 / ENEMY 10 / DRAW 4 | PLAYER 13 / ENEMY 15 / DRAW 2 | 127 | 126 |

`action_distribution`（MOVE/MISS/ATTACK 等の発生回数）・撃墜数（DESTROYED）は各シードで
数%以内の差に収まっており、n=30という試行回数でのサンプリングノイズの範囲内と判断できる
（拮抗した組み合わせのため勝敗の内訳自体は試行ごとに揺れやすいが、どちらのシードでも
一方のチームへの著しい偏りが対応前後で新たに生じてはいない）。26.3節で説明した
「フェーズ5内で先行ユニットに撃破された対象をキャッシュ経由で参照しない」無効化が、
この統計的な同等性を保つ上で重要な役割を果たしている。

### 26.7 テスト

新規のユニットテストは追加せず、既存の `_select_target_fuzzy` 系テスト
（`tests/unit/test_simulation.py`）がキャッシュ導入後もすべてパスすることで
リグレッションがないことを確認した。特に `test_reaction_delay_fuzzy_suppresses_attack_on_detection_step`
は `sim._step_count` を手動でインクリメントしてから再度 `_select_target_fuzzy()` を
呼ぶテストであり、キャッシュがステップ単位で正しく無効化されることを間接的に検証している。

## 27. Issue #474: エリア収縮メカニクス

### 27.1 課題

バトルロワイヤル方式（および1vs1ソロミッションを含む全対戦形式）では、`map_bounds`
（Phase 6-5 フィールドスケーリング、16章）がバトル開始時に一度決まった後は変化せず、
境界には `_boundary_repulsion()`（`movement.py`）によるソフトな斥力があるのみで
リングアウト等の強制収束メカニクスが存在しなかった。そのため初回の接敵・交戦後、
生存ユニットが広いマップ（最大 `MAX_FIELD_SIZE=8000m` 四方）に散らばると再接近を
促す力学的インセンティブが乏しく、以降ほとんど接敵が発生しないままバトルが間延びし、
最悪の場合 `_MAX_STEPS=5000` 到達で引き分け終了してしまうことがあった。

### 27.2 設計

`BattleSimulator.step()` に「エリア収縮フェーズ」（`_area_shrink_phase()`）を新設し、
索敵フェーズより前に `self.map_bounds` を更新することで、そのステップの索敵・移動が
新しい境界を反映するようにした。

**収縮スケジュール**: `SHRINK_START_STEP`（既定300ステップ、dt=0.1sで約30秒）以降、
`SHRINK_INTERVAL_STEPS`（既定300ステップ）ごとに辺長へ `SHRINK_RATIO`（既定0.85）を
乗算する。`MIN_SHRUNK_FIELD_SIZE` を下回らせない（既定は `MIN_FIELD_SIZE` と同値の
2000m。理由は後述）。いずれの定数も `constants.py` にチューニング可能な値として定義した。

**収縮の基準点は固定中心**: 生存ユニットの重心に追従させる方式は、「移動→重心移動→
反発方向変化」という循環でオシレーションを起こすリスクがあり、`_boundary_repulsion()`
側の中心座標も毎ステップ再計算が必要になる。そのため `BattleSimulator.__init__()` で
一度だけ計算した固定中心（`self._map_center = side_len / 2.0`。初期の `map_bounds` の
中央で、スポーン領域が使う `SPAWN_ZONE_MAP_OFFSET` の基準点と同一）を採用し、収縮のたびに
`new_min = center - new_side_len/2, new_max = center + new_side_len/2` という対称な
再計算のみを行う。`_boundary_repulsion()`（`movement.py`）は元々 `self.map_bounds` を
毎回読み直す実装だったため、中心座標自体を変更する必要はなく、`map_bounds` の値のみ
更新すれば自動的に新しい境界に追従する。

**`MIN_SHRUNK_FIELD_SIZE` と `BOUNDARY_MARGIN` の関係**: `BOUNDARY_MARGIN`（200m、
`movement.py` の斥力発生距離）は既存の `MIN_FIELD_SIZE=2000m` と共存しており、これは
「マージンがフィールド辺長の10%」という現行アーキテクチャで動作実績のある比率である。
この実績比率を踏襲し、`MIN_SHRUNK_FIELD_SIZE = MIN_FIELD_SIZE` として、収縮後も
この下限を下回らせないことで、margin/field_size比が10%を超えて `_boundary_repulsion`
の効きが破綻する領域には踏み込まないようにした。

**残存ユニット数が少ない場合の停止**: いずれかのチームの生存数が
`SHRINK_PAUSE_ALIVE_THRESHOLD`（既定1）以下になった場合、そのチームを巡る決着直前の
不自然な圧縮を避けるため収縮を停止する。ただし**この判定は「消耗して少なくなった」
チームのみを対象とする**（`BattleSimulator.__init__()` で記録する
`self._initial_team_alive_counts`（開始時点のチーム人数）が `SHRINK_PAUSE_ALIVE_THRESHOLD`
を超えていたチームに限る）。1vs1ソロミッションのように開始時点からチーム人数が
1のケースをこの判定に含めてしまうと、最も頻度の高いバトル形式である1vs1で収縮が
一切発動しなくなってしまう（実装中にテストで実際にこの不具合を発見し修正した。
`tests/unit/test_area_shrink.py` の `test_shrink_not_paused_for_1v1_from_start` /
`test_shrink_pauses_when_team_depleted_from_larger_start` で両ケースを区別して検証している）。

**ログ方式**: 収縮判定はチーム生存数という状態に依存するため、毎ステップのスナップショット
ではなく、`map_bounds` の値が実際に変化した（または低生存数により変化がスキップされた）
イベント発生時のみ `BattleLog` に記録する（`action_type="AREA_SHRINK"`, `details`に
`{step, old_bounds, new_bounds, reason}`。`reason` は `"scheduled_shrink"` /
`"paused_low_survivors"`）。5000ステップ全量を出すとリプレイログが肥大化する一方、
収縮は `SHRINK_INTERVAL_STEPS` ごとの離散イベントであり、ビューア側は直近イベント値を
保持する形で `map_bounds` の推移を再構成できる。停止イベントは状態が変わらない限り
重複記録しないよう `self._shrink_paused` フラグで一度だけに制限している
（`STRATEGY_CHANGED` ログ（4章）が状態遷移時のみ記録するパターンを踏襲）。

### 27.3 今回スコープ外とした事項

- **生存ユニット重心への追従方式**: 27.2節の理由により固定中心をMVPとして採用した。
  再接触率の改善効果が不十分な場合、Phase2として別Issueで検討する。
- **フロントエンド（BattleViewer）でのフィールド境界収縮の可視化**: バックエンドの
  ログ設計（イベント単位の`AREA_SHRINK`ログ）は将来の対応を見据えているが、実際の
  描画対応は別Issueとする。
- **境界外に取り残されたユニットへの追加ペナルティ**: `_boundary_repulsion()` の
  押し戻し力を強化する、あるいはダメージを与える等の追加対応は行っていない。既存の
  斥力式（`3.0 * direction / max(dist, 1.0)`）が収縮後の境界でも機能することを
  `tests/unit/test_area_shrink.py` で確認済みだが、極端な収縮直後にユニットが
  大きく境界外に取り残されるケースの挙動チューニングは今後の課題とする。

### 27.4 テスト

`tests/unit/test_area_shrink.py` で以下を検証:

1. `SHRINK_START_STEP` に到達するまでは `map_bounds` が変化しないこと
2. `SHRINK_START_STEP` 以降、`SHRINK_INTERVAL_STEPS` ごとに `SHRINK_RATIO` を乗算した
   辺長へ段階的に収縮すること（2回分の収縮を検証）
3. 収縮が固定中心（`self._map_center`）を基準に対称であること
4. `MIN_SHRUNK_FIELD_SIZE` を下回らないこと（多数の収縮間隔を経過させて検証）
5. 開始時3機だったチームが1機まで消耗した場合は収縮が停止すること、および
   1vs1ソロミッションでは開始時点から人数が少なくても収縮が正常に発動すること
6. `AREA_SHRINK` ログがイベント単位（毎ステップではなく）で記録されること、
   停止イベントも一度だけ記録されること

いずれのテストも、ステップ経過中にバトルが決着してしまうと収縮ロジックを検証できない
ため、テスト用ユニットの HP を大きく確保している（`_make_large_sim()` 参照）。
既存の `tests/unit/test_field_scaling.py`・`test_phase_6_3_field_init.py`・
`test_spawn_detection_avoidance.py`・`test_potential_field.py`・`test_simulation.py`
がすべて変更なくパスすることを確認し、初期化時の `map_bounds` 計算（16章）や
スポーン領域生成にリグレッションがないことを確認した。

既存の `tests/unit` 全体が変更後もすべてパスすることを確認済み。
