# バトルエンジン高度化 機能仕様書

**バージョン:** 0.3.0  
**作成日:** 2026-04-27  
**ステータス:** Phase 1-1 実装済み

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

#### 2.3.2 ポテンシャルフィールド

ポテンシャルフィールド法で「目標方向ベクトル」を算出し、慣性モデルで実際の速度・位置を更新する。

| ソース | 種別 | 効果 |
|--------|------|------|
| 攻撃対象の敵 | 引力 | 近づく |
| 攻撃範囲外の敵（高脅威） | 斥力 | 離れる |
| 味方ユニット | 弱い斥力 | 密集を防ぐ |
| マップ境界 | 斥力 | フィールド外への逸脱防止 |
| 撤退ポイント | 強引力（RETREAT時） | 撤退経路への誘導 |

#### 2.3.3 撤退行動の制約

`RETREAT` 行動を選択したユニットは、フィールド上に設定された**撤退ポイント**（`RetreatPoint`）を目標引力として移動する。撤退ポイントが未設定のフィールドでは `RETREAT` はファジィルールの出力から除外される。

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
| `max_speed` | `float` | 最大速度 (m/s)。デフォルト: 80.0 |
| `acceleration` | `float` | 加速度 (m/s²)。デフォルト: 30.0 |
| `deceleration` | `float` | 減速度 (m/s²)。デフォルト: 50.0 |
| `max_turn_rate` | `float` | 最大旋回速度 (deg/s)。通常MS: 360、MA: 30 |

> **Note:** `current_action` / `target_id` は戦闘中の一時状態のため、`unit_resources` の `dict` に含めてDBには保存しない方針を基本とする（要検討）。

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
- [ ] `BattleViewer` を新ログスキーマに対応（Phase 1-4 で対応）
- [x] `FuzzyEngine` クラスの新規作成（Phase 1-2）
- [x] 中階層ファジィ推論の実装（Phase 1-2）
- [x] `aggressive.json` ルールセットの初期定義（Phase 1-2）
- [ ] ローカル実行スクリプト（`run_simulation.py`）の作成（Phase 1-3）

### Phase 2：低階層ファジィ推論

- [ ] ターゲット選択ファジィルール実装
- [ ] 武器選択ファジィルール実装
- [ ] `defensive.json` / `sniper.json` ルールセット追加

### Phase 3：移動の高度化

- [ ] 慣性モデルの実装（`max_speed` / `acceleration` / `deceleration` / `max_turn_rate`）
- [ ] ポテンシャルフィールドによる移動実装（目標方向ベクトル算出）
- [ ] `RETREAT` モード時の撤退ポイント引力計算
- [ ] バトルフィールドへの `RetreatPoint` 定義の追加
- [ ] 複数チーム（3チーム以上）対応の確認テスト

### Phase 4：戦略・戦術階層

- [ ] チームレベルの戦略モード切り替えロジック
- [ ] 戦況に応じた動的 `StrategyMode` 変更（劣勢時に `RETREAT` へ移行等）
- [ ] `assault.json` / `retreat.json` ルールセット追加

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
- [ADVANCED_BATTLE_LOGIC_REPORT.md](../reports/ADVANCED_BATTLE_LOGIC_REPORT.md) — Phase 2.5 実装レポート
