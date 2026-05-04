# ダイナミック近接戦闘システム 機能仕様書

**バージョン:** 0.3.0 (Phase A + Phase B 実装済み)
**作成日:** 2026-05-04
**ステータス:** Phase A・Phase B 実装済み

---

## 1. 概要

### 1.1 課題

現行バトルエンジン（`battle-engine-feature.md`）では、遠距離優先 AI の MS 同士が遠距離から一方的に撃ち合うだけの単調な展開になりやすい。

**根本原因:**

| 要因 | 詳細 |
|------|------|
| 近接戦闘のメリット欠如 | 近接武器は遠距離と同等扱いで、あえて近づく理由がない |
| 近接移行トリガーなし | AI が近距離戦に切り替える判断基準が存在しない |
| 一気に詰める手段なし | `max_speed` の範囲内でしか移動できず、遠距離から近接圏への切り込みが間に合わない |
| LOS 概念なし | 障害物が存在しないため、常に全 MS が互いを索敵・射撃できる |

### 1.2 ゴール

- MS がフィールドを高速で動き回り **視覚的に躍動感のあるバトル** を実現
- 遠距離・近接が状況に応じて切り替わる **メリハリのある戦闘展開**
- LOS と障害物を導入し、**隠れながら近づく** という戦術的行動を可能にする

---

## 2. 新システム一覧

| システム | 概要 |
|---------|------|
| [ブーストダッシュ](#3-ブーストダッシュシステム) | EN を消費して一時的に `max_speed` を超える超高速移動 |
| [近接戦闘トリガー](#4-近接戦闘トリガー) | 距離・弾薬残量に基づく近接移行条件 |
| [近接戦闘メリット](#5-近接戦闘メリット) | 格闘武器の耐性無視・コンボ・弾薬消費ゼロ・命中率補正 |
| [障害物システム](#6-障害物システム) | フィールド上の静的遮蔽物 |
| [LOS（視線遮断）](#7-los視線遮断) | 障害物による射撃・索敵の遮断 |
| [AI 行動拡張](#8-ai行動拡張) | 上記を利用した新 AI 行動・ファジィルール追加 |

---

## 3. ブーストダッシュシステム

> **実装状況:** ✅ Phase B 実装済み (`backend/app/engine/simulation.py`, `backend/app/models/models.py`)

### 3.1 概要

MS がターゲットへの一気の距離詰めを行う専用アクション。  
EN を消費する代わりに **`max_speed` の最大 2 倍** まで一時加速する。

### 3.2 パラメータ（`MobileSuit` フィールド）

| パラメータ | 型 | デフォルト値 | 説明 |
|---|---|---|---|
| `boost_speed_multiplier` | `float` | `2.0` | ブースト時の速度倍率（`max_speed × multiplier`） |
| `boost_en_cost` | `float` | `5.0` | ブースト中の EN 消費量（/s） |
| `boost_max_duration` | `float` | `3.0` | 1 回のブーストの最大継続時間（s） |
| `boost_cooldown` | `float` | `5.0` | ブースト終了後の再使用不可時間（s） |

DB マイグレーション: `alembic/versions/o9p0q1r2s3t4_add_boost_params_to_mobile_suits.py`

**ユニット種別ごとの目安値:**

| ユニット種別 | 通常 `max_speed` | ブースト時速度 | `boost_en_cost` |
|---|---|---|---|
| 通常 MS | 80 m/s | 160 m/s | 5.0 /s |
| 高機動型 MS | 150 m/s | 300 m/s | 8.0 /s |
| MA（モビルアーマー） | 300 m/s | 600 m/s | 12.0 /s |
| 大型機（ビグ・ザム等） | 40 m/s | 80 m/s | 3.0 /s |

### 3.3 `unit_resources` への追加状態

| キー | 型 | 初期値 | 説明 |
|---|---|---|---|
| `is_boosting` | `bool` | `False` | 現在ブースト中か |
| `boost_elapsed` | `float` | `0.0` | 現ブーストの継続時間（s） |
| `boost_cooldown_remaining` | `float` | `0.0` | 残クールダウン時間（s） |

### 3.4 ブースト中の速度計算

```
ブースト時有効最大速度 = max_speed × boost_speed_multiplier

速度更新（慣性モデルを維持したまま速度上限を差し替え）:
  IF is_boosting:
    effective_max_speed = max_speed × boost_speed_multiplier
  ELSE:
    effective_max_speed = max_speed
```

実装: `BattleSimulator._apply_inertia()` の `effective_max_speed` 計算部分。

### 3.5 ブースト終了条件

以下のいずれかで `is_boosting = False` に戻る：

1. `boost_elapsed >= boost_max_duration`
2. `current_en <= 0`（EN 切れ）
3. ターゲットが `MELEE_BOOST_ARRIVAL_RANGE`（`MELEE_RANGE × 2 = 100m`）内に入った
4. 慣性考慮キャンセル（「3.6 ブーストキャンセル判定」参照）

ブースト終了時: `boost_cooldown_remaining = boost_cooldown` をセットし、毎ステップデクリメントする。  
`boost_cooldown_remaining > 0` の間は `BOOST_DASH` アクションを選択できない。

### 3.6 ブーストキャンセル判定（慣性考慮）

ブースト中の各ステップで以下の計算を行い、遠距離攻撃が可能な位置で停止できると判断した場合はブーストをキャンセルして攻撃に切り替える。

**停止予想距離の計算:**

$$d_{stop} = \frac{v_{current}^2}{2 \times deceleration}$$

**判定ロジック:**

```
停止予想位置 = 現在位置 + 現在進行方向 × d_stop
停止予想位置からターゲットまでの距離 = d_to_target_from_stop

IF d_to_target_from_stop <= 使用予定の遠距離武器の最大射程:
    → ブーストキャンセル (is_boosting = False)
    → action = "ATTACK"（遠距離武器で攻撃）
ELSE:
    → ブースト継続
```

実装: `BattleSimulator._check_boost_cancel()`

> **補足:** 「使用予定の遠距離武器」は現在クールダウン中でなく弾薬が残っている最初の遠距離武器の `range` を参照する。EN / 弾薬が枯渇していて遠距離武器が使用不可の場合はブースト継続（格闘圏まで詰める）。

### 3.7 EN 消費・クールダウン更新

`BattleSimulator._refresh_phase(dt)` にて毎ステップ処理：

```
IF is_boosting:
    current_en -= boost_en_cost × dt
    boost_elapsed += dt
ELSE:
    current_en += en_recovery  # 通常の EN 回復
    boost_cooldown_remaining = max(0, boost_cooldown_remaining - dt)
```

### 3.8 BattleLog 記録

| action_type | タイミング | details フィールド |
|---|---|---|
| `BOOST_START` | ブーストダッシュ開始時 | — |
| `BOOST_END` | ブースト終了時 | `{"reason": "終了理由の文字列"}` |

`BOOST_START` / `BOOST_END` ログを BattleViewer でブーストエフェクト（推進炎等）に利用する（フロントエンド実装は別 issue）。

---

## 4. 近接戦闘トリガー

### 4.1 トリガー条件

AI の中階層ファジィ推論に `ENGAGE_MELEE` アクションを新設する。  
以下の **いずれか** の条件が満たされると、ファジィ推論で `ENGAGE_MELEE` が高スコアになる。

#### トリガー A：弾薬・EN 枯渇

| 変数 | 条件 | 説明 |
|---|---|---|
| `ranged_ammo_ratio` | `< 0.10` | 遠距離武器の残弾が 10% 未満 |
| `en_ratio` | `< 0.20` | EN が 20% 未満（ブースト不可、遠距離武器も使用困難） |

> **補足:** どちらかが枯渇していても、近接武器（格闘）は EN・弾薬消費ゼロのため戦闘継続可能。

#### トリガー B：距離近接＋HP 余裕あり

| 変数 | 条件 | 説明 |
|---|---|---|
| `distance_to_nearest_enemy` | `< DASH_TRIGGER_DISTANCE (800 m)` | 敵が一定距離内に入った |
| `hp_ratio` | `> 0.50` | 自機 HP が 50% 以上（余裕がある状態） |

> **戦略意図:** HP 余裕のある状態で敵が接近してきたら積極的に近接戦へ切り込む。

#### ファジィ変数追加（中階層）

| 変数名 | 範囲 | ファジィ集合 |
|---|---|---|
| `ranged_ammo_ratio` | 0.0〜1.0 | EMPTY / LOW / SUFFICIENT |
| `distance_to_nearest_enemy` | 0〜MAP_MAX | MELEE / CLOSE / MID / FAR |

**ルール例（AGGRESSIVE モード）:**

```
IF ranged_ammo_ratio IS EMPTY THEN action IS ENGAGE_MELEE
IF en_ratio IS LOW AND ranged_ammo_ratio IS LOW THEN action IS ENGAGE_MELEE
IF hp_ratio IS HIGH AND distance_to_nearest_enemy IS CLOSE THEN action IS ENGAGE_MELEE
```

### 4.2 距離定義

| 定数 | 値 | 説明 |
|---|---|---|
| `MELEE_RANGE` | `50 m` | 格闘武器の有効射程（外部パラメータ化済み） |
| `MELEE_BOOST_ARRIVAL_RANGE` | `MELEE_RANGE × 2 = 100 m` | BOOST_DASH の到達目標距離。ここでブースト終了し格闘へ移行 |
| `POST_MELEE_DISTANCE` | `10 m` | 格闘攻撃命中後、自機がターゲットと保つ距離（外部パラメータ化済み） |
| `CLOSE_RANGE` | `200 m` | 遠距離武器の命中率ペナルティ / 近距離ボーナス開始 |
| `DASH_TRIGGER_DISTANCE` | `800 m` | `ENGAGE_MELEE` のトリガー距離 |

---

## 5. 近接戦闘メリット

### 5.1 命中率の距離補正

遠距離武器は近すぎると当てにくくなり、近距離武器は近いほど命中しやすくなる。

**命中率補正式（乗算）:**

| 距離 `d` | 遠距離武器補正 | 近距離・格闘補正 |
|---|---|---|
| `d <= MELEE_RANGE (50m)` | × 0.4 | × 1.5 |
| `d <= CLOSE_RANGE (200m)` | × 0.7 | × 1.2 |
| `d > CLOSE_RANGE` | × 1.0 | × 0.8 |

> **武器種別判定:** `weapon.weapon_type` が `MELEE` / `CLOSE_RANGE` か否かで補正テーブルを選択。

### 5.2 格闘武器の耐性無視

`weapon.weapon_type == "MELEE"` の場合、ダメージ計算でターゲットの**ビーム耐性・実弾耐性を無視**する。

```
通常ダメージ = base_damage × (1 - target_resistance)
格闘ダメージ = base_damage × 1.0  # 耐性無視
```

### 5.3 格闘コンボシステム

格闘攻撃が命中したとき、一定確率で **コンボ（連続ヒット）** が発生しダメージが倍増する。

| パラメータ | 値 | 説明 |
|---|---|---|
| `combo_base_chance` | `0.30` | 初回コンボ発生確率（30%） |
| `combo_chain_decay` | `0.50` | 2 連目以降のコンボ継続確率倍率 |
| `combo_damage_multiplier` | `1.5` | コンボ命中 1 回あたりのダメージ倍率 |
| `combo_max_chain` | `3` | 最大コンボ連続回数 |

**コンボ計算例（base_damage = 100, 3 連コンボ発生時）:**

```
1 ヒット目: 100 ダメージ（通常命中）
コンボ発生（30% → 命中）: +100 × 1.5 = 150
コンボ継続（15% → 命中）: +100 × 1.5 = 150
コンボ継続（7.5% → 命中）: +100 × 1.5 = 150
合計: 550 ダメージ
```

### 5.3.1 コンボ BattleViewer 演出

コンボ発生時、`BattleLog` の `combo_message` フィールドに演出用文字列を格納する。  
フロントエンドの `BattleViewer` はこのフィールドを検出してコンボエフェクトを表示する。

**`combo_message` フォーマット:**

```
"{n}Combo {total_damage}ダメージ!!"
例: "2Combo 300ダメージ!!"
    "3Combo 550ダメージ!!"
```

**表示仕様（フロントエンド）:**
- コンボ数に応じてエフェクトの色・サイズを変化させる（1連 → 黄、2連 → オレンジ、3連 → 赤）
- 通常ダメージ表示に重ねてコンボカウンター（`×2`, `×3`）をアニメーション表示

### 5.4 格闘武器の弾薬・EN 消費ゼロ

`weapon.weapon_type == "MELEE"` の場合、攻撃時の弾薬・EN 消費を **ゼロ** にする。  
これにより弾切れ・EN 枯渇後も格闘で戦闘継続が可能。

---

## 6. 障害物システム

### 6.1 概要

フィールド上に静的・破壊不可の障害物を配置する。  
障害物は **LOS の遮断** と **ポテンシャルフィールドの斥力源** として機能する。

### 6.2 データモデル（`Obstacle`）

```python
@dataclass
class Obstacle:
    obstacle_id: str
    position: Vector3   # 球体中心座標（3D: x, y, z）
    radius: float       # 半径（m）。LOS 判定では 3D 球体として使用
    height: float       # 高さ（m）。BattleViewer の視覚的高さ表現用
```

### 6.3 フィールド定義への追加（`BattleField`）

```python
@dataclass
class BattleField:
    # 既存フィールド省略
    obstacles: list[Obstacle] = field(default_factory=list)
```

### 6.4 障害物配置ガイドライン

| 項目 | 推奨値 |
|---|---|
| 障害物数 | 5〜20 個 |
| 障害物半径 | 50〜300 m |
| 最小間隔 | `radius_a + radius_b + 100 m`（MS が通過できるスペースを確保） |
| 配置領域 | MAP_BOUNDS の中央 60% エリア（端に固まらないよう分散） |

**配置例（5000 m × 5000 m フィールド）:**

```
障害物 A: pos=(1000, 0, 1500), radius=200, height=400
障害物 B: pos=(2500, 0, 1000), radius=150, height=300
障害物 C: pos=(2500, 0, 2500), radius=300, height=600  # 中央大型岩礁
障害物 D: pos=(1500, 0, 3500), radius=100, height=200
障害物 E: pos=(3500, 0, 3000), radius=200, height=400
```

> **配置生成について:** 初期実装は静的定義のみとする。ランダム生成アルゴリズムはバックログとして管理する（参照: [issue_drafts/random-obstacle-placement.md](../issue_drafts/random-obstacle-placement.md)）。

### 6.5 ポテンシャルフィールドへの追加

障害物は **強い斥力源** としてポテンシャルフィールドに組み込む。

| ソース | 種別 | 係数 | 条件 |
|---|---|---|---|
| 障害物 | 斥力 | `4.0` | 距離 ≤ `obstacle.radius + OBSTACLE_MARGIN(50m)` |

```python
# 既存の _calculate_potential_field() に追加
for obs in obstacles:
    dist = np.linalg.norm(pos_unit - obs.position)
    if dist <= obs.radius + OBSTACLE_MARGIN:
        away_vec = (pos_unit - obs.position) / max(dist, 1.0)
        force_vec += OBSTACLE_REPULSION_COEFF * away_vec
```

---

## 7. LOS（視線遮断）

### 7.1 概要

**ハードブロック方式**を採用する。  
障害物が攻撃者とターゲットの間に存在する場合、射撃と索敵の両方を完全に遮断する。  
LOS 判定は **3D 球体（Y 軸を含む）** での Ray-Sphere 交差判定で行う。

### 7.2 LOS チェック関数

**パフォーマンス最適化:** LOS チェック対象を **射撃武器の最大射程内のユニット** に限定することで、計算量を O(N²M) から O(K×M)（K = 射程内ユニット数）に削減する。

```python
def _has_los(
    pos_a: np.ndarray,
    pos_b: np.ndarray,
    obstacles: list[Obstacle],
) -> bool:
    """
    pos_a から pos_b への視線が障害物に遮られていないか判定（3D Ray-Sphere 交差判定）。
    障害物を 3D 球体としてモデル化し、Y 軸（高度）も考慮する。
    a = |unit_dir|² = 1 なので簡略化。
    """
    direction = pos_b - pos_a
    dist = float(np.linalg.norm(direction))
    if dist < 1e-6:
        return True
    unit_dir = direction / dist

    for obs in obstacles:
        obs_center = np.array([obs.position.x, obs.position.y, obs.position.z])
        oc = pos_a - obs_center
        b = 2.0 * float(np.dot(oc, unit_dir))
        c = float(np.dot(oc, oc)) - obs.radius ** 2
        discriminant = b ** 2 - 4.0 * c
        if discriminant < 0:
            continue
        t = (-b - math.sqrt(discriminant)) / 2.0
        if 0.0 < t < dist:
            return False  # 視線遮断あり
    return True


def _get_units_in_weapon_range(
    unit: MobileSuit,
    all_units: list[MobileSuit],
    weapon_max_range: float,
) -> list[MobileSuit]:
    """
    LOS チェック対象を武器射程内のユニットに絞り込む。
    O(N²M) → O(K×M) に削減（K = 射程内ユニット数）。
    """
    pos = np.array([unit.position.x, unit.position.y, unit.position.z])
    result = []
    for other in all_units:
        if other.unit_id == unit.unit_id:
            continue
        other_pos = np.array([other.position.x, other.position.y, other.position.z])
        if float(np.linalg.norm(other_pos - pos)) <= weapon_max_range:
            result.append(other)
    return result
```

### 7.3 射撃への適用

`_process_attack()` にて、攻撃実行前に LOS チェックを追加する。

```
LOS チェック失敗（遮断あり）→ 攻撃スキップ、`BattleLog.action_type = "ATTACK_BLOCKED_LOS"` を記録
LOS チェック成功 → 従来の命中判定へ
```

### 7.4 索敵への適用

`_search_phase()` にて、センサー範囲内の敵ユニットを検出する際に LOS チェックを追加する。

```
センサー範囲内 かつ _has_los() = True → 敵発見
センサー範囲内 かつ _has_los() = False → 発見不可（障害物で隠れている状態）
```

**追跡（追尾）への影響:**  
一度発見した敵でも、LOS が失われた場合は `last_known_position` へ向かって移動するが追跡を継続できない。

| 状態 | 挙動 |
|---|---|
| LOS あり | 通常の索敵・攻撃 |
| LOS なし（初めて見失った） | `last_known_position` を記憶し、そこへ向かう |
| LOS なし（一度も発見していない） | 移動のみ（攻撃不可） |

---

## 8. AI 行動拡張

### 8.1 新アクション：`BOOST_DASH`

中階層ファジィ推論の出力に `BOOST_DASH` を追加する。

**発動フロー:**

```
1. 中階層で ENGAGE_MELEE が出力
2. ターゲットまでの距離 > MELEE_BOOST_ARRIVAL_RANGE（MELEE_RANGE × 2）→ BOOST_DASH を実行
3. is_boosting = True、boost_elapsed = 0.0 にセット
4. ポテンシャルフィールドでターゲット方向への強引力（+3.0）を適用
5. 毎ステップ「3.6 ブーストキャンセル判定」を実行
   → 停止予想位置から遠距離射撃可能 → ブーストキャンセル、ATTACK（遠距離）へ遷移
6. ターゲットが MELEE_BOOST_ARRIVAL_RANGE 内に入った → BOOST_DASH 終了
7. ATTACK（格闘武器）へ遷移 → 命中時に POST_MELEE_DISTANCE（10m）まで接近配置
```

**格闘攻撃後のポジショニング:**

格闘命中後、自機をターゲットから `POST_MELEE_DISTANCE` の距離に強制的に再配置する。  
これにより次のステップで再度格闘攻撃・コンボ継続が可能な状態を維持する。

```
格闘命中後:
  dir_away = normalize(pos_self - pos_target)
  pos_self  = pos_target + dir_away × POST_MELEE_DISTANCE
  velocity_vec = [0, 0, 0]  # 速度リセット（次ステップから再加速）
```

### 8.2 LOS が遮断された場合の行動

現在は `ATTACK` → ターゲットへ引力（+2.0）でまっすぐ向かうが、  
LOS が遮断されている場合は **障害物を迂回する行動** へ切り替える。

**実装方針（段階的）:**

| フェーズ | 実装内容 |
|---|---|
| 初期実装 | LOS 遮断時、`MOVE` にフォールバックし障害物の斥力で自然に迂回 |
| 拡張実装 | 障害物の端点を経由する迂回ウェイポイントを生成 |

```
LOS 遮断 AND action == "ATTACK":
  → action = "BOOST_DASH" (障害物を迂回しながら近づく)
  → ポテンシャルフィールドの障害物斥力が自然に迂回経路を形成
```

### 8.3 新ファジィ変数

**中階層に追加する入力変数:**

| 変数名 | 範囲 | ファジィ集合 | 説明 |
|---|---|---|---|
| `ranged_ammo_ratio` | 0.0〜1.0 | EMPTY / LOW / SUFFICIENT | 遠距離武器の残弾割合 |
| `los_blocked` | 0 or 1 | CLEAR / BLOCKED | 現ターゲットへの LOS 状態 |
| `boost_available` | 0 or 1 | AVAILABLE / UNAVAILABLE | ブースト可否（クールダウン中かどうか） |

**`ASSAULT` StrategyMode 向けルール例:**

```json
{
  "rules": [
    {
      "conditions": [
        { "variable": "ranged_ammo_ratio", "set": "EMPTY" }
      ],
      "output": { "variable": "action", "set": "ENGAGE_MELEE" }
    },
    {
      "conditions": [
        { "variable": "hp_ratio", "set": "HIGH" },
        { "variable": "distance_to_nearest_enemy", "set": "CLOSE" }
      ],
      "output": { "variable": "action", "set": "ENGAGE_MELEE" }
    },
    {
      "conditions": [
        { "variable": "los_blocked", "set": "BLOCKED" },
        { "variable": "boost_available", "set": "AVAILABLE" }
      ],
      "output": { "variable": "action", "set": "BOOST_DASH" }
    }
  ]
}
```

---

## 9. データモデル変更

### 9.1 `MobileSuit` への追加フィールド

| フィールド | 型 | デフォルト | 説明 |
|---|---|---|---|
| `boost_speed_multiplier` | `float` | `2.0` | ブースト時速度倍率 |
| `boost_en_cost` | `float` | `5.0` | ブースト中 EN 消費（/s） |
| `boost_max_duration` | `float` | `3.0` | ブースト最大継続時間（s） |
| `boost_cooldown` | `float` | `5.0` | ブーストクールダウン（s） |

### 9.2 `unit_resources` への追加状態（DB 非保存）

| キー | 型 | 初期値 | 説明 |
|---|---|---|---|
| `is_boosting` | `bool` | `False` | ブースト中フラグ |
| `boost_elapsed` | `float` | `0.0` | ブースト継続時間（s） |
| `boost_cooldown_remaining` | `float` | `0.0` | 残クールダウン（s） |
| `last_known_enemy_position` | `dict[str, Vector3]` | `{}` | unit_id → 最後に LOS があった座標 |

### 9.3 `BattleLog` への追加

| フィールド | 型 | 説明 |
|---|---|---|
| `action_type` の追加値 | `str` | `"BOOST_START"` / `"BOOST_END"` / `"ATTACK_BLOCKED_LOS"` / `"MELEE_COMBO"` / `"MELEE_POST_POSITION"` |
| `combo_count` | `int \| None` | コンボ連続回数（`MELEE_COMBO` 時のみ） |
| `combo_message` | `str \| None` | BattleViewer 演出用文字列（例: `"2Combo 300ダメージ!!"`） |
| `los_status` | `str \| None` | `"CLEAR"` / `"BLOCKED"` |

### 9.4 `BattleField` への追加

| フィールド | 型 | 説明 |
|---|---|---|
| `obstacles` | `list[Obstacle]` | フィールド上の障害物リスト |

### 9.5 新規モデル：`Obstacle`

```python
@dataclass
class Obstacle:
    obstacle_id: str
    position: Vector3   # 球体中心座標（3D: x, y, z）
    radius: float       # 半径（m）。LOS 判定では 3D 球体として使用
    height: float       # 高さ（m）。BattleViewer の視覚的高さ表現用
```

---

## 10. 定数追加（`constants.py`）

```python
# 距離定義（外部パラメータ化：constants.py から上書き可能）
MELEE_RANGE: float = 50.0                           # 格闘武器の有効射程（m）
MELEE_BOOST_ARRIVAL_RANGE: float = MELEE_RANGE * 2  # BOOST_DASH 終了距離（m）= 100.0
POST_MELEE_DISTANCE: float = 10.0                   # 格闘命中後の対象との距離（m）
CLOSE_RANGE: float = 200.0                          # 近距離判定閾値（m）
DASH_TRIGGER_DISTANCE: float = 800.0                # ENGAGE_MELEE トリガー距離（m）

# ブースト
DEFAULT_BOOST_SPEED_MULTIPLIER: float = 2.0
DEFAULT_BOOST_EN_COST: float = 5.0       # /s
DEFAULT_BOOST_MAX_DURATION: float = 3.0  # s
DEFAULT_BOOST_COOLDOWN: float = 5.0      # s

# 障害物
OBSTACLE_MARGIN: float = 50.0           # 障害物斥力の有効マージン（m）
OBSTACLE_REPULSION_COEFF: float = 4.0   # 障害物の斥力係数

# コンボ
COMBO_BASE_CHANCE: float = 0.30
COMBO_CHAIN_DECAY: float = 0.50
COMBO_DAMAGE_MULTIPLIER: float = 1.5
COMBO_MAX_CHAIN: int = 3

# 命中補正
MELEE_CLOSE_ACCURACY_BONUS: float = 1.5    # d <= MELEE_RANGE
MELEE_MID_ACCURACY_BONUS: float = 1.2     # d <= CLOSE_RANGE
RANGED_CLOSE_ACCURACY_PENALTY: float = 0.4 # d <= MELEE_RANGE
RANGED_MID_ACCURACY_PENALTY: float = 0.7  # d <= CLOSE_RANGE
```

---

## 11. 実装ロードマップ

### Phase A：LOS + 障害物（基盤）

- [x] `Obstacle` データクラスの追加（`backend/app/models/models.py`）
- [x] `BattleField.obstacles` フィールドの追加（`backend/app/models/models.py`）
- [x] `_has_los()` の実装（Ray-Sphere 交差判定、`backend/app/engine/simulation.py`）
- [x] `_get_units_in_weapon_range()` の実装（パフォーマンス最適化用ヘルパー）
- [x] `_detection_phase()` に LOS チェックを追加（LOS 遮断時は発見不可）
- [x] `_process_attack()` に LOS チェックを追加（射撃遮断、`ATTACK_BLOCKED_LOS` ログ）
- [x] `last_known_enemy_position` の管理ロジック（LOS 喪失時に座標を記憶）
- [x] ポテンシャルフィールドに障害物斥力を追加（`OBSTACLE_REPULSION_COEFF=4.0`）
- [x] `OBSTACLE_MARGIN` / `OBSTACLE_REPULSION_COEFF` を `constants.py` に追加
- [x] ユニットテスト追加（`backend/tests/unit/test_los_obstacle.py`、28 テスト）

### Phase B：ブーストダッシュ

- [ ] `MobileSuit` にブースト関連フィールドを追加
- [ ] DB マイグレーション追加
- [ ] `unit_resources` にブースト状態を追加
- [ ] `_apply_inertia()` でブースト時の速度上限切り替え
- [ ] EN 消費・クールダウン処理
- [ ] `BOOST_START` / `BOOST_END` ログ追加

### Phase C：近接戦闘トリガー + メリット

- [ ] 中階層ファジィ変数に `ranged_ammo_ratio` / `los_blocked` / `boost_available` 追加
- [ ] `ENGAGE_MELEE` / `BOOST_DASH` アクションの追加
- [ ] 命中率の距離補正を `_process_attack()` に実装
- [ ] 格闘武器の耐性無視ロジック追加
- [ ] 格闘武器の弾薬・EN 消費ゼロ化
- [ ] コンボシステムの実装（`MELEE_COMBO` ログ）
- [ ] `assault.json` ファジィルールの更新

### Phase D：AI 行動統合・チューニング

- [ ] LOS 遮断時の迂回行動（障害物斥力による自然迂回）
- [ ] ブーストダッシュの AI 発動条件チューニング
- [ ] フィールドに障害物を配置したテストシナリオ作成
- [ ] シミュレーション実行で視覚的な動きを確認・パラメータ調整

---

## 12. 決定済み事項（旧・未決定事項）

| 項目 | 決定内容 |
|---|---|
| `BOOST_DASH` の AI キャンセル条件 | 慣性考慮アルゴリズムを導入。停止予想距離（$v^2 / 2a$）から遠距離射撃可能なら即キャンセルし通常攻撃へ（Section 3.6） |
| 障害物の配置生成 | 初期実装は静的定義のみ。ランダム生成はバックログへ（[issue_drafts/random-obstacle-placement.md](../issue_drafts/random-obstacle-placement.md)） |
| LOS のパフォーマンス | 射撃武器の最大射程内ユニットのみに LOS チェックを限定し O(K×M) に削減（Section 7.2 `_get_units_in_weapon_range()`） |
| コンボの BattleViewer 表現 | `combo_message` フィールドに `"2Combo 300ダメージ!!"`形式で格納、フロントエンドでコンボエフェクトを表示（Section 5.3.1） |
| 格闘武器の射程定義 | BOOST_DASH 終了距離を `MELEE_RANGE × 2 = 100m` とし、格闘命中後は対象から `POST_MELEE_DISTANCE = 10m` に再配置。両定数は外部パラメータ化（Section 3.6, 8.1, 10） |
| 障害物の高さと 3D LOS | Y 軸を含む 3D Ray-Sphere 交差判定を採用。`Obstacle.position` は球体中心（3D座標）として扱う（Section 7.2） |

---

## 13. 関連ドキュメント

- [battle-engine-feature.md](./battle-engine-feature.md) — 現行バトルエンジン仕様（ポテンシャルフィールド・ファジィ推論）
- [fuzzy-engine.md](./fuzzy-engine.md) — ファジィエンジン詳細
- [issue_drafts/random-obstacle-placement.md](../issue_drafts/random-obstacle-placement.md) — バックログ: 障害物ランダム配置生成
