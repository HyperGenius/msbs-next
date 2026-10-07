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

**向きによる最高速度の割引（後退の減速、`backend/app/engine/facing.py`）**

胴体の向き（`body_heading_deg`）と移動の向き（`movement_heading_deg`）のずれ θ（0〜180°）に応じて、最高速度に係数を掛ける。
射撃機が、同じ速度の格闘機から引き撃ちで逃げ続けられないようにするため。「撃ち続けたいなら遅くなる」代償を後退に持たせ、詰める側を有利にする。

| θ | 係数（定数） | 動き |
|---|---|---|
| 0° | `FACING_SPEED_MODIFIER_FRONT`（1.0） | 前進 |
| 90° | `FACING_SPEED_MODIFIER_SIDE`（0.85） | 横移動（ストレイフ）。周回しながら撃つ動きの価値を残すため、割引を小さくする |
| 180° | `FACING_SPEED_MODIFIER_BACK`（0.6） | 敵を向いたまま真後ろへ下がる |

* 値はすべて暫定で、調整は総合バランス調整（#587）で行う
* 間の角度は 90° ごとの区間で、両端の傾きが 0 になる曲線（`(1 - cos)/2`）でつなぐ（`facing_speed_modifier()`）。向きのわずかな揺れで速度が変わらないようにするため
* 行動の種類では場合分けしない。胴体の向きは行動で決まる（`_update_body_heading()`）ので、ATTACK・ENGAGE_MELEE・DISENGAGE、射程内に敵がいる MOVE で敵から離れる動きは遅くなる。胴体が移動方向を向く移動は割り引かれない
* `effective_max_speed = max_speed × 地形適正・重力井戸の補正（_get_terrain_modifier()） × 向きの係数`。今の速度が上限を超えたときは、瞬時に止めず `deceleration` で徐々に落とす
* 同じ最高速度なら、前進で詰める格闘機は、後ろ 0.6 で下がる射撃機の約 1.7 倍の速さで近づける

**後退中のブースト禁止**

θ が `BACKPEDAL_ANGLE_DEG`（90°）を超えている間は「後退中」とみなす（`is_backpedaling()`）。

* 後退中はブーストを開始しない。`BOOST_DASH`（`_handle_boost_dash_action()`）と仕切り直しの開始（`_start_disengage()`）の両方で判定する
* ブースト中に後退へ入ったら、そのステップから速度倍率（`boost_speed_multiplier`）を掛けない（`_apply_inertia()`）。次のブースト終了判定（`_check_boost_cancel()`）でブーストを終え、`BOOST_END`（理由「後退中」）を記録する
* 仕切り直しは敵を向いたまま斜め後ろへ下がるため、始めた直後に後退中となりブーストを終える。BattleViewer の演出の追加は無く、後退する機体が前進する機体より遅く見える

**計測結果（`engagement_bench.py`、各条件 10 戦、変更前 → 変更後）**

「初格闘」は最初の格闘攻撃までの時間（p50）で、格闘機が相手に追いつくまでの時間の目安として追加した指標。

| シナリオ | 条件 | 初格闘 p50 | 距離 p50 | <150m | 戦闘時間 p50 |
|---|---|---|---|---|---|
| 格闘専用機 vs 射撃機（`melee_only_vs_ranged`） | AGGRESSIVE/BALANCED | 14.2s → 9.3s | 138m → 104m | 59% → 79% | 34s → 24s |
| 同上 | DEFENSIVE/BALANCED | 14.1s → 9.3s | 149m → 105m | 53% → 75% | 26s → 20s |
| 同上 | SNIPER/BALANCED | 16.6s → 9.8s | 133m → 123m | 59% → 77% | 37s → 23s |
| 同上 | ASSAULT/BALANCED | 9.8s → 8.4s | 122m → 86m | 73% → 83% | 22s → 26s |

* 射撃機同士（`ranged_gundam_zaku`・`ranged_gelgoog_gundam`）の射撃の最適比 p50 は 0.78〜1.20 で、#598 の目標帯（0.6〜1.3）に収まる（変更前 0.79〜1.20）
* 格闘機 vs 射撃機（`melee_vs_ranged`）では射撃機が下がりきれず、距離 p50 が 7〜37m 縮んだ（射撃の最適比 p50 0.79〜1.01 → 0.69〜0.85）
* 時間切れはどのシナリオでも 0% のまま

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
| 攻撃対象の敵 | 間合いのばね（2.3.4 参照） | `2.0`（`ATTACK_TARGET_ATTRACTION_COEFF`） | `current_action == "ATTACK"` かつターゲット選択済み |
| MOVE 行動時の最近敵 | 引力。索敵済みかつ射程内なら間合いのばね | `1.5`（`CLOSEST_ENEMY_ATTRACTION_COEFF`） | `current_action == "MOVE"` |
| 攻撃範囲外の高脅威敵 | 斥力（away_vec 方向に加算） | `1.5` | 脅威スコア（攻撃力/自機最大HP）> `HIGH_THREAT_THRESHOLD(0.5)` かつ射程外 |
| 敵ユニット（最小間隔） | 強い斥力（2.3.4 参照） | 最大 `10.0`（`ENEMY_SEPARATION_COEFF`） | 距離 < `ENEMY_MIN_SEPARATION(10m)` |
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

#### 2.3.4 交戦距離（間合い）の制御（Issue #598 実装済み）

ユニットは「目標交戦距離」を持ち、遠ければ近づき、近すぎれば離れる。射撃・格闘の両方が対象。
以前は ATTACK 中にターゲットへ一定の力で引き寄せられ続けたため、射撃機同士でも 0〜10m まで密着していた。

**目標交戦距離（`MovementMixin._engagement_range()`）**

| 項目 | 内容 |
|---|---|
| 基準武器 | `_get_reference_weapon()` が返す武器（移動判断の基準武器） |
| 目標距離 | `optimal_range × 戦略モード倍率`。許容幅の外側の端が射程を超えないよう `range / (1 + 許容幅の割合)` で上限を設ける |
| 戦略モード倍率 | `ENGAGEMENT_RANGE_STRATEGY_MULTIPLIERS`（SNIPER `1.2`、ASSAULT `0.8`、その他 `1.0`） |
| `tactics.range` | 戦略モード倍率を掛けた後に補正する。FLEE の射撃武器は射程の上限を目標にする。基準武器の選び方も変わる（34 章） |
| 許容幅 | 目標距離 × `ENGAGEMENT_RANGE_TOLERANCE_RATIO(0.2)` |
| 格闘武器の下限 | `MELEE_ENGAGEMENT_RANGE_MIN(20m)` |
| 間合いを持たない場合 | 武器が無い、または弾切れ・EN 不足で使えない場合は `None`。従来どおり一定の力で近づく。再使用待ちだけで使えない武器は基準として扱う |

計算結果は毎ステップ `unit_resources[unit_id]["engagement_range"]`（`EngagementRange(distance, tolerance)`）に残す。

**間合いのばね（`_engagement_spring()` / `_engagement_force()`）**

目標距離からのずれを許容幅で割った値を `x` とする（正なら遠い）。力はターゲット方向に `係数 × r(x)` で働く。
ターゲットへの射線が障害物で遮られているときは、ばねにせず従来どおり一定の力で近づく。射線が遮られたまま間合いを保つと、撃てず索敵も外れたまま止まるため（障害物の多い戦場で時間切れが急増した）。

| 範囲 | `r(x)` | 動き |
|---|---|---|
| `abs(x) ≤ 1`（許容幅の中） | `ENGAGEMENT_BAND_FORCE_RATIO(0.25) × x` | ストレイフ（係数 1.0）が主になり、ターゲットの周りを回る |
| `1 < abs(x) < 2` | 端の値から `±1` まで線形に強める | 許容幅へ戻る |
| `abs(x) ≥ 2` | `±1` | 遠ければ係数いっぱいで近づき、近ければ係数いっぱいで離れる |

* 境界の斥力は境界の数 m 手前でしか効かない。そのため後退の力（ターゲットから離れる向き）は、`BOUNDARY_MARGIN` 以内で境界へ向かう成分を 0 にする。壁際に追い込まれた機体は壁沿いに横へ逃げる
* 格闘武器はストレイフが無いため、許容幅を挟んで「踏み込んでは離れる」動きになる
* ポテンシャルフィールドは合力を正規化して向きだけを使い、慣性モデルは常に最高速まで加速する。そのため間合いの中で止まることはなく、周回または往復になる。機動力（速度）の差はそのまま残り、速い機体は遅い機体に追いつける（遅い格闘機は速い射撃機に引き撃ちされる）
* 敵を向いたまま離れる動き（後退）は、最高速度が割り引かれる（2.3.1「向きによる最高速度の割引」）。同じ速度なら、前進で詰める機体が追いつける

**MOVE 中の最近敵**

最近敵が索敵済み（`team_detected_units`）かつ基準武器の射程内にいて、射線が通るときだけ、同じばねにする。それ以外は従来どおり一定の力で引き寄せる。

ATTACK 中にターゲットを見失った（索敵済みの敵がいるが、ターゲット選定が `None` を返した）ときも、MOVE と同じ最近敵への引力で動く。以前はこの状態でターゲットへの力が何も働かず、漂っていた。

**敵との最小間隔（`_enemy_separation_repulsion()`）**

`ENEMY_MIN_SEPARATION(10m)` より近い敵から、距離 0 で `ENEMY_SEPARATION_COEFF(10.0)`、最小間隔で 0 になる斥力を受ける。行動の種類によらず働く。完全に重なった 2 機は ID の大小で逆向きに押し出す。

**格闘攻撃後の再配置（`ActionHandlerMixin._process_engage_melee()`）**

* `_process_attack()` は命中判定まで進んだかを `bool` で返す
* 攻撃したときだけ、ターゲットから `POST_MELEE_DISTANCE`（`MELEE_ENGAGEMENT_RANGE_MIN` と同じ 20m）の位置へ移し、速度を 0 にする
* 再使用待ちなどで攻撃しなかったときは、ATTACK として間合いの移動をする（以前は毎ステップ 10m 地点へ再配置し、密着したまま止まっていた）

**計測結果（`engagement_bench.py`、各条件 10 戦、交戦中の距離の中央値）**

| シナリオ | 戦略 | 変更前 | 変更後 | 最適距離との比（射撃 p50） |
|---|---|---|---|---|
| ガンダム[ライフル] vs ザクII[MG] | AGGRESSIVE / DEFENSIVE / SNIPER / ASSAULT | 4 / 1 / 2 / 5m | 318 / 313 / 333 / 274m | 0.99 / 0.79 / 0.83 / 0.83 |
| ゲルググ[ライフル] vs ガンダム[ライフル] | 同上 | 9 / 7 / 8 / 12m | 396 / 400 / 479 / 319m | 0.99 / 0.98 / 1.20 / 0.80 |
| 格闘機同士（ガンダム vs グフ） | 同上 | 15 / 16 / 16 / 15m | 150 / 159 / 192 / 150m | 50m 未満の割合 78〜86% → 0% |
| ガンダム[サーベル] vs ザクII[MG] | 同上 | — | 117 / 123 / 124 / 118m | 格闘機の勝率 100% |

* 射撃機同士の交戦距離は最適距離の 0.79〜1.20 倍に収まる（目標は 0.6〜1.3 倍）
* 時間切れは、ガンダム vs ザクII の DEFENSIVE・SNIPER（各 40%）が 0% になった。ゲルググ vs ガンダムの DEFENSIVE で 10%（1 戦）が新たに時間切れになった。両機の HP が下がって RETREAT（撤退ポイントが無いので MOVE）を選び続け、MOVE 中は攻撃しないまま間合いを保ったため。膠着の検知と仕切り直しは Sub-Issue 5（#599）で扱う
* 交戦距離が伸びたため、攻撃セクタはほぼすべて FRONT になる。回り込みは後続の Sub-Issue で扱う
* `engine_ci_smoke` と合成ユニットの多数機戦（障害物なし、2・8・20 機、各 10 戦）で、戦闘時間・時間切れ率に大きな変化は無い。敵同士が 10m 未満にいた割合は 0.1〜12% → 0% になった

**障害物の多い戦場（合成ユニット 8 機、障害物 DENSE、各 60 戦）**

| 条件 | 時間切れ | 戦闘時間 中央値 |
|---|---|---|
| 変更前（#615 適用済みの main） | 7% | 43s |
| 変更後 | 13% | 53s |

間合いを保つと射線が切れやすくなるため、障害物の多い戦場では戦闘がやや長引く。射線が遮られたときに近づく処理を入れる前は、時間切れが 90% に達した（#615 適用前、10 戦）。#615（射線喪失による索敵の除外をチーム単位にする）より前の main と比べると、変更前 23% → 変更後 43% だった。

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
| $k$ | 距離減衰指数。ミノフスキー濃度 $m$ に応じて `2 + m`（[29章](#29-ミノフスキー濃度の連続値化)） |

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

ミノフスキー粒子は索敵範囲を狭め、距離減衰指数 $k$ を大きくする。そのため近距離でも発見確率が下がる。
当初は「あり/なし」の2値だったが、Issue #575 で濃度（0.0〜1.0）の連続値に変わった。計算式は [29章](#29-ミノフスキー濃度の連続値化) を参照。
濃度 1.0（`special_effects: ["MINOVSKY"]`）のとき、索敵範囲 ×0.5・$k = 3.0$ になる。

### 15.5 新定数 (`constants.py`)

```python
# 確率的索敵定数 (Phase 6-4)
DETECTION_FALLOFF_EXPONENT: float = 2.0       # 通常環境の距離減衰指数
DETECTION_FALLOFF_EXPONENT_MINOVSKY: float = 3.0  # ミノフスキー濃度 1.0 時の減衰指数
```

### 15.6 発見ログの変更

発見ログに索敵確率パーセントを追加。

```
# 通常環境
"{actor_name}が{dist_label}に{target.name}を発見！（索敵確率 56%）"

# ミノフスキー濃度が MINOVSKY_DENSE_LOG_THRESHOLD（0.5）以上のとき
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

> Issue #531 で `events` は `attacks: AttackEvent[]` と `criticalTargetIds: Set<string>` に置き換えた
> （`docs/features/battle-viewer-feature.md` の「攻撃エフェクト（ヒット演出）」参照）。`attackingUnitIds` は変更なし。

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
| 攻撃対象の敵 | 間合いのばね | `2.0` | `ATTACK` かつターゲット選択済み（2.3.4 参照） |
| MOVE 行動時の最近敵 | 引力（索敵済み・射程内なら間合いのばね） | `1.5` | `MOVE` |
| 攻撃範囲外の高脅威敵 | 斥力 | `1.5` | 脅威スコア > `0.5` かつ射程外 |
| 敵ユニット（最小間隔） | 強い斥力 | 最大 `10.0` | 距離 < `ENEMY_MIN_SEPARATION(10m)` |
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
   通り、この経路は新規実装しない）。Issue #615 以降は、ユニットごとではなく
   チーム×発見済みの敵ごとに 1 回判定し、チームの誰からも LOS が通らないときだけ
   外す（`_drop_detections_without_team_los()`）
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
4. _update_body_heading(unit,dt) ×N  [呼び出し2] ATTACK/ENGAGE_MELEE 時と MOVE 時
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

> 注: Issue #596 で、フェーズ4と5を 1 つのループにまとめた（ユニットごとに胴体向き更新 → 行動）。
> 呼び出し2も呼び出し3と同じく、先に行動したユニットの影響を受ける。撃破時に再計算する無効化条件は
> そのまま有効。詳細は 31 章。

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
`backend/tests/unit/test_area_shrink.py` の `test_shrink_not_paused_for_1v1_from_start` /
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
  `backend/tests/unit/test_area_shrink.py` で確認済みだが、極端な収縮直後にユニットが
  大きく境界外に取り残されるケースの挙動チューニングは今後の課題とする。

### 27.4 テスト

`backend/tests/unit/test_area_shrink.py` で以下を検証:

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
既存の `backend/tests/unit/test_field_scaling.py`・`test_phase_6_3_field_init.py`・
`test_spawn_detection_avoidance.py`・`test_potential_field.py`・`test_simulation.py`
がすべて変更なくパスすることを確認し、初期化時の `map_bounds` 計算（16章）や
スポーン領域生成にリグレッションがないことを確認した。

既存の `tests/unit` 全体が変更後もすべてパスすることを確認済み。

---

## 28. Issue #519: `test_boost_start_occurs_with_full_field` の残存 flaky 対策

### 28.1 概要

Issue #385（20章）でモンテカルロ的アサーションを複数回試行（`attempts=3`）に変更する対策を
行ったにもかかわらず、`TestScenarioFullField::test_boost_start_occurs_with_full_field` が
単体実行でも約15%の確率で3回中0回のまま失敗するケースが残っていた（PR #517 の CI で顕在化）。

### 28.2 調査

- 6障害物・3チーム戦という複雑な統合シナリオでは、ファジィ推論によるAIの行動選択次第で
  `ENGAGE_MELEE` が選ばれず `BOOST_START` が自然発火しないケースが一定確率で存在し、
  試行回数を増やす対策だけでは flaky を解消しきれない。
- 一方、`BOOST_START` の発火メカニズム自体は `TestBoostDashIntegration::test_boost_start_triggered_via_engage_melee`
  が `current_action` を直接 `ENGAGE_MELEE` に設定してファジィ推論をバイパスし、決定論的に
  検証済みである。
- 同ファイル内の類似テスト `TestScenarioBoostDashApproach::test_boost_start_occurs` も、
  Phase E-3 の攻撃角度セクタ補正により自然発火しなくなった際、削除ではなく `xfail` 化する
  方針が既に採用されていた。

### 28.3 対応内容

- `test_boost_start_occurs_with_full_field` を削除せず、`@pytest.mark.xfail(reason=..., strict=False)`
  を付与した。`reason` には flaky になった理由と、機構自体を保証する代替テスト名を明記している。
- `strict=False` のため、BOOST_START が発生すれば XPASS、発生しなければ XFAIL となり、
  いずれの場合も CI は失敗しない。統合シナリオとしての検証意図はテストとして残しつつ、
  CI の安定性を確保した。
- 同様の flaky なモンテカルロ的アサーションに遭遇した場合の判断基準を `backend/CLAUDE.md`
  の「テスト規約」に追記した。

---

## 29. ミノフスキー濃度の連続値化

Issue #575（Epic #573「戦域ローテーションと環境効果」の Sub-Issue 2）。

### 29.1 概要

ミノフスキー粒子を「あり/なし」から、0.0〜1.0 の連続値（濃度 $m$）に変えた。
濃度は索敵と射撃の命中率に影響する。高濃度では近接が有利になり、低濃度では遠距離が有利になる。

### 29.2 濃度の決め方

`BattleSimulator(..., minovsky_density: float | None = None)` で渡す。`self.minovsky_density` は次の順で決まる。

1. 引数で渡された場合はその値（[0, 1] にクランプ）
2. 渡されず、`special_effects` に `"MINOVSKY"` がある場合は 1.0（ソロミッションの従来の挙動）
3. どちらでもない場合は 0.0

濃度 0.0 のとき、索敵・命中率は導入前と完全に同じ結果になる。
定期バトルのルームの濃度をシミュレーターへ渡すのは Sub-Issue 4（[theater-rotation.md](theater-rotation.md)）。

### 29.3 索敵への影響

`TargetingMixin._minovsky_detection_params()`（`backend/app/engine/targeting.py`）で計算する。

$$d_{\text{eff}} = \text{sensor\_range} \times (1 - 0.5m), \qquad k = 2 + m$$

| m | 索敵範囲 | 指数 k |
|---|---|---|
| 0.0 | ×1.00 | 2.0 |
| 0.3 | ×0.85 | 2.3 |
| 0.6 | ×0.70 | 2.6 |
| 1.0 | ×0.50 | 3.0 |

発見確率は従来どおり $P = \max(0, 1 - (d / d_{\text{eff}})^k)$（15.2節）。

### 29.4 射撃の命中率への影響

`CombatMixin._get_minovsky_hit_multiplier()`（`backend/app/engine/combat.py`）で倍率を計算する。

$$f = 1 - 0.4 \cdot m \cdot \min\left(1, \frac{d}{600\text{m}}\right)$$

* $d$ はターゲットまでの距離
* 対象は射撃武器（`weapon_type` が `MELEE` でなく、`is_melee` が false）。格闘武器は常に 1.0
* `_calculate_hit_chance()` で、距離補正乗数（`_get_accuracy_modifier()`）の後、セクタ補正の前に掛ける

| m | 150m | 300m | 600m以上 |
|---|---|---|---|
| 0.0 | ×1.00 | ×1.00 | ×1.00 |
| 0.3 | ×0.97 | ×0.94 | ×0.88 |
| 0.6 | ×0.94 | ×0.88 | ×0.76 |
| 1.0 | ×0.90 | ×0.80 | ×0.60 |

ファジィ推論の武器選択・ターゲット選択は命中率を入力に使わないため、影響を受けない。
管理画面の攻撃シミュレーション（`combat_preview.py`）は環境効果を対象外としているため、濃度を反映しない。

### 29.5 定数（`backend/app/engine/constants.py`）

| 定数 | 値 | 用途 |
|---|---|---|
| `MINOVSKY_SENSOR_RANGE_REDUCTION` | 0.5 | 索敵範囲の倍率 `1 − 係数·m` |
| `MINOVSKY_FALLOFF_EXPONENT_BONUS` | 1.0 | 減衰指数 `DETECTION_FALLOFF_EXPONENT + 係数·m` |
| `MINOVSKY_RANGED_ACCURACY_PENALTY` | 0.4 | 射撃の命中率倍率の係数 |
| `MINOVSKY_RANGED_PENALTY_REF_DISTANCE` | 600.0 | 射撃ペナルティが最大になる距離 (m) |
| `MINOVSKY_DENSE_LOG_THRESHOLD` | 0.5 | 索敵ログを「濃密なミノフスキー粒子の中、」にする濃度 |

`SPECIAL_ENVIRONMENT_EFFECTS["MINOVSKY"]` と `DETECTION_FALLOFF_EXPONENT_MINOVSKY` は濃度 1.0 のときの値として残している。
admin-tool で係数を調整できるようにするかは Epic #573 の検討事項（未確定）。

### 29.6 ログ

* 索敵ログ: 濃度が `MINOVSKY_DENSE_LOG_THRESHOLD` 以上のとき「濃密なミノフスキー粒子の中、」の文言にする（15.6節）
* 攻撃ログ: 射撃の `ATTACK` / `MISS` ログに、デバッグ用フィールド `minovsky_hit_multiplier`（命中率の倍率、小数第3位に丸め）を載せる
  * 倍率が 1.0 未満のときだけ値を入れる。それ以外は `null`
  * Sub-Issue 9 の敗因集計で使う
  * DB 保存時は `strip_debug_fields()`（`backend/app/engine/battle_utils.py`）で除去する
* バトルログの表示（フロントエンド）は変えていない

### 29.7 テスト

`backend/tests/unit/test_minovsky_density.py`

* 濃度の決め方（引数・`special_effects`・クランプ）
* 濃度 0.0 / `["MINOVSKY"]` で索敵パラメータが導入前と一致する（回帰）
* 濃度ごとの索敵範囲・減衰指数・射撃の命中率倍率（上の表）
* 格闘武器の命中率が濃度の影響を受けない
* 索敵ログの文言のしきい値
* 攻撃ログの `minovsky_hit_multiplier` と、`strip_debug_fields()` での除去

---

## 30. 環境タイプの効果と地形適正

Issue #576（Epic #573「戦域ローテーションと環境効果」の Sub-Issue 3）。

### 30.1 概要

環境タイプ（`MasterEnvironment`、[theater-rotation.md](theater-rotation.md)）の効果パラメータを戦闘に反映する。
あわせて、地形適正を速度だけでなく命中・回避にも効かせ、機体マスターに地形適正を持たせる。
狙いは「その環境の特化機 ＞ 汎用機 ＞ 環境に合わない特化機」という勝ち筋を作ること。

### 30.2 `EnvironmentProfile`

エンジンは DB を参照しない。呼び出し側が `MasterEnvironment` からプロファイルを作り、`BattleSimulator(..., environment_profile=...)` で渡す。

定義は `backend/app/engine/environment.py`。

| 項目 | 既定値 | 用途 |
|---|---|---|
| `environment_id` | — | 環境タイプID。指定すると `BattleSimulator.environment` をこの値にする |
| `sensor_range_multiplier` | 1.0 | 索敵範囲の倍率 |
| `ranged_accuracy_penalty` | 0.0 | 射撃の命中率ペナルティの係数 α |
| `ranged_penalty_ref_distance` | 400.0 | ペナルティが最大になる距離 D (m) |
| `default_obstacle_density` | `MEDIUM` | 戦域が障害物密度を指定しないときの密度 |
| `default_terrain_grade` | `A` | 機体の `terrain_adaptability` にこの環境のキーが無いときのランク |

`MasterEnvironment` からの変換は `TheaterService.environment_profile()` / `resolve_environment_profile()`（`backend/app/services/theater_service.py`）。
定期バトルでプロファイルを渡すのは Sub-Issue 4。

プロファイルを渡さない場合（ソロミッション、admin-tool のシミュレーション）は効果なしとして扱い、挙動は導入前と変わらない。
地形適正の既定ランクは `A`（`DEFAULT_TERRAIN_GRADE`）。

### 30.3 索敵範囲

`TargetingMixin._detection_phase()` で、ミノフスキーの倍率（29.3節）に `sensor_range_multiplier` を掛け合わせる。

$$d_{\text{eff}} = \text{sensor\_range} \times (1 - 0.5m) \times \text{sensor\_range\_multiplier}$$

距離減衰指数 $k$ は環境タイプの影響を受けない。

### 30.4 射撃の命中率

`CombatMixin._get_environment_hit_multiplier()`（`backend/app/engine/combat.py`）で倍率を計算する。

$$f_{\text{env}} = 1 - \alpha \cdot \min\left(1, \frac{d}{D}\right)$$

* ミノフスキーの倍率と同じ位置（距離補正乗数の後、セクタ補正の前）で掛け合わせる
* 格闘武器は対象外（常に 1.0）

森林（α = 0.2、D = 400m）: 200m で ×0.9、400m 以上で ×0.8。

### 30.5 障害物密度

`BattleField.obstacle_density` を明示していない `BattleField` を渡したとき、`default_obstacle_density` を使う。
「明示したか」は pydantic の `model_fields_set` で判定する（`_resolve_battlefield()`、`backend/app/engine/simulation.py`）。

* 戦域が密度を指定したとき: `TheaterService.battlefield_for(theater)` が `BattleField(obstacle_density=...)` を返し、その値を使う
* `battlefield` を渡さない場合: 従来どおり障害物を生成しない

森林は障害物が `DENSE` のため、既存の LOS システムで遠距離の射線が切れやすい。

### 30.6 地形適正

ランクは `terrain_adaptability[environment]`。キーが無ければ `default_terrain_grade`（`MovementMixin._get_terrain_grade()`）。

| ランク | 速度（`TERRAIN_ADAPTABILITY_MODIFIERS`） | 命中・回避（`TERRAIN_ADAPTABILITY_HIT_BONUS`） |
|---|---|---|
| S | ×1.2 | +1 |
| A | ×1.0 | 0 |
| B | ×0.8 | −0.5 |
| C | ×0.6 | −1 |
| D | ×0.4 | −1.5 |

* 速度: `_get_terrain_modifier()` の係数を最大速度に掛ける（従来どおり）。キーが無いときの既定ランクだけを変えた
* 命中・回避: `_calculate_hit_chance()` で `hit_chance += 攻撃側の値 − 防御側の値` を加算する。`accuracy_bonus` / `evasion_bonus` と同じく乗算補正の後に加算する

命中・回避の補正値は暫定値。パイロットの技量・スキルとあわせて Sub-Issue 11（#587）で確定する。

Issue の初期案は 1 ランク 5 ポイント（S +5 〜 D −15）だったが、30.9節の結果から S +1 / B −0.5 / C −1 / D −1.5 に下げた。
戦闘中の命中率は中央値 3.5% 程度と低い。5 ポイントの差を付けると不利な側の命中率が 0% に張り付き、S 対 A の同一機体戦で S が全勝したため。

ソロミッションは所持機体の列（`SPACE`/`GROUND`/`COLONY` は全機 A）を使うため、速度・命中・回避は変わらない。
定期バトルはエントリー時にマスターの地形適正をスナップショットに入れる（30.7節）。
プロファイルを渡す前（Sub-Issue 4 より前）でも環境は `SPACE` なので、ゲルググ（S）・ドム・グフ（C）には宇宙の補正が掛かる。

### 30.7 機体マスターの地形適正

`MasterMobileSuitSpec.terrain_adaptability: dict[str, str]`（省略可、既定は空）。値は `S`〜`D` に限る（バリデーションあり）。
`master_mobile_suits.specs` の JSON に入るため、マイグレーションは不要。

地形適正は機体マスターを正とする。所持機体の `mobile_suits.terrain_adaptability` はショップ購入時に設定されず、全機デフォルトのため使わない。

| 場所 | 処理 |
|---|---|
| エントリーのスナップショット（`POST /api/entries`、チームエントリー） | `MobileSuitService.build_entry_snapshot()` で、マスターの値で `terrain_adaptability` を上書きする |
| ガレージ（`GET /api/mobile_suits` など） | 機体名で引いたマスターの値を返す |
| ショップ（`GET /api/shop/listings`） | `specs.terrain_adaptability` を返す（無ければ空） |

* マスターは `master_mobile_suit_id` で引き、無ければ機体名で引く。どちらでも引けない機体（スターター機など）は空の辞書になり、全環境で既定ランクになる
* NPC（`MatchingService._create_npc_mobile_suit()`）はマスターを参照しないため、既定ランク（汎用機扱い）になる
* admin-tool の機体マスター編集フォームは地形適正を送らない。更新 API は既存の specs とマージするため、保存しても消えない

初期値（`backend/data/master/mobile_suits.json`。`GROUND`/`COLONY`/`UNDERWATER` は従来のデフォルト A/A/C）:

| 機体 | 宇宙 | 森林 | 意図 |
|---|---|---|---|
| ザク II（`zaku_ii`） | A | A | 汎用 |
| ジム（`gm`） | A | A | 汎用 |
| ガンダム（`gundam`） | A | A | 汎用（高性能） |
| ゲルググ（`gelgoog`） | S | B | 宇宙寄り |
| ドム（`dom`） | C | B | 地上（ホバー）用 |
| グフ（`gouf`） | C | S | 地上・格闘特化 |

ザク II F型は `mobile_suits.json` に無い。本番DBにある場合は汎用（A/A）として扱う（キーが無ければ既定ランク A）。

### 30.8 定数（`backend/app/engine/constants.py`）

| 定数 | 値 | 用途 |
|---|---|---|
| `TERRAIN_ADAPTABILITY_HIT_BONUS` | S 1 / A 0 / B −0.5 / C −1 / D −1.5 | 地形適正による命中・回避の補正値 (%) |
| `DEFAULT_TERRAIN_GRADE` | `A` | プロファイルが無いときの既定ランク |

### 30.9 バランス確認

`backend/scripts/simulation/terrain_balance_bench.py`（DB 不要。使い方は [balance-cli-tools.md](balance-cli-tools.md)）で 1対1 を繰り返した。

* 最大 3000 ステップ（定期バトルと同じ）。決着しないときは残り HP の割合が高い方を勝ちとする。両者とも無傷（交戦なし）は引き分け
* スポーン位置の偏りを消すため、試行ごとに PLAYER 側を入れ替える
* 勝率は引き分けを除いた値。1 組 60 試行のため、±7 ポイント程度の誤差がある

#### 補正値の決め方

同一機体（ザク II）で地形適正ランクだけを変えた 1対1 の A 側勝率（`--rounds 60`）。

| 補正値（S / B / C / D） | 森林 S 対 A | 森林 A 対 C | 宇宙 S 対 A | 宇宙 A 対 C |
|---|---|---|---|---|
| +5 / −5 / −10 / −15（初期案） | 100%（n=48） | — | — | — |
| +1 / −1 / −2 / −3 | 75.7% | 79.5% | 55.4% | 94.9% |
| +0.5 / −0.5 / −1 / −1.5 | 44.4% | 68.0% | 39.0% | 57.6% |
| +1 / −0.5 / −1 / −1.5（採用） | 70.0% | 53.3% | 67.8% | 65.5% |

* 初期案は不利な側の命中率が 0% に張り付き、有利な側が全勝した
* 速度補正だけ（命中・回避の補正なし）では、宇宙 A 対 C の A の勝率は 38%。速い機体が有利にはならない
* 1 ランク 0.5 ポイントでは、速度補正の不利を打ち消せず S が A に勝てない
* 採用値は S の加点を 1 ポイントに保ち、A 未満の減点を半分にした。特化機 ＞ 汎用機 ＞ 不向きな機体 の順になり、不向きな機体も 2〜5 割勝てる

#### 採用値での結果

#### 同一機体のランク差（FOREST・ミノフスキー 0.6）

| A | B | A 勝 | B 勝 | 引分 | A 勝率 |
|---|---|---|---|---|---|
| zaku_ii[S] | zaku_ii[A] | 35 | 15 | 10 | 70.0% |
| zaku_ii[S] | zaku_ii[C] | 34 | 7 | 19 | 82.9% |
| zaku_ii[A] | zaku_ii[C] | 24 | 21 | 15 | 53.3% |

#### 特化機と汎用機（FOREST・ミノフスキー 0.6）

| A | B | A 勝 | B 勝 | 引分 | A 勝率 |
|---|---|---|---|---|---|
| dom | zaku_ii | 18 | 23 | 19 | 43.9% |
| dom | gm | 15 | 31 | 14 | 32.6% |
| gouf | zaku_ii | 51 | 0 | 9 | 100.0% |
| gouf | gm | 48 | 1 | 11 | 98.0% |
| gelgoog | zaku_ii | 45 | 1 | 14 | 97.8% |
| gelgoog | gm | 41 | 0 | 19 | 100.0% |

#### 同一機体のランク差（SPACE・ミノフスキー 0.3）

| A | B | A 勝 | B 勝 | 引分 | A 勝率 |
|---|---|---|---|---|---|
| zaku_ii[S] | zaku_ii[A] | 40 | 19 | 1 | 67.8% |
| zaku_ii[S] | zaku_ii[C] | 48 | 10 | 2 | 82.8% |
| zaku_ii[A] | zaku_ii[C] | 38 | 20 | 2 | 65.5% |

#### 特化機と汎用機（SPACE・ミノフスキー 0.3）

| A | B | A 勝 | B 勝 | 引分 | A 勝率 |
|---|---|---|---|---|---|
| dom | zaku_ii | 6 | 51 | 3 | 10.5% |
| dom | gm | 3 | 56 | 1 | 5.1% |
| gouf | zaku_ii | 55 | 0 | 5 | 100.0% |
| gouf | gm | 58 | 0 | 2 | 100.0% |
| gelgoog | zaku_ii | 59 | 0 | 1 | 100.0% |
| gelgoog | gm | 59 | 0 | 1 | 100.0% |

#### 考察

* 同一機体では、森林・宇宙とも 特化機（S）＞ 汎用機（A）＞ 不向きな機体（C）の順になった
* 機体マスターどうしでは、地形適正より基本性能の差が大きい。グフ・ゲルググは地形に関わらず汎用機にほぼ全勝し、ドムはほぼ全敗する
* ドムの汎用機への勝率は、森林（B）で 33〜44%、宇宙（C）で 5〜11%。地形適正の差は勝率に出ている
* 機体ごとの基本性能、パイロットの技量・スキルを含めたバランス調整は、Epic の実装が進んだ段階で Sub-Issue 11（#587）で行う
  * 方針: 地形適正の影響は機体性能の差を上回ってよい。パイロットの技量・スキルの差をどこまで出すかを決めてから、計算式に反映する
  * パイロットスキル `accuracy_up` / `evasion_up` も命中率への固定値の加算のため、命中率が低い現状では効きすぎる可能性がある
  * 本ベンチはパイロットステータスをすべて 0 で回している
* 引き分けの多くは交戦しないまま終わった戦闘。森林はミノフスキー 0.6 と索敵 ×0.8 で索敵範囲が約 0.56 倍になり、引き分けが増える

### 30.10 テスト

`backend/tests/unit/test_environment_profile.py`

* プロファイルの倍率で索敵範囲が変わり、ミノフスキーの倍率と掛け合わさる
* 射撃の命中率倍率（距離ごと・格闘武器は対象外・プロファイルなし）
* 障害物密度の既定値（明示した密度が優先される）
* 地形適正ランクごとの速度・命中・回避、既定ランクへのフォールバック
* プロファイルなしの戦闘が、効果なしのプロファイルと同じ結果になる（回帰）

`backend/tests/test_terrain_adaptability.py`

* 機体マスターの地形適正（省略可・ランクの検証・シードデータ）
* エントリーのスナップショットがマスターの値を使う（ID・機体名・マスターなし）
* ショップ・ガレージの API が地形適正を返す
* `MasterEnvironment` からのプロファイル作成、`battlefield_for()`

`backend/tests/unit/test_admin_mobile_suits.py`: admin API で地形適正を登録でき、specs の部分更新で消えない

## 31. 側面の敵への旋回と SNIPER の近距離行動

Issue #596（Epic #594「交戦距離の制御と膠着の解消」の Sub-Issue 2）。

### 31.1 背景

SNIPER 同士の 1 対 1 が、毎回 500 秒の時間切れ引き分けになっていた。原因は 2 つある。

1. MOVE 中の胴体が移動方向を向く。ファジィルール `arc_002` / `arc_003`（側面・背面の敵 → MOVE）は「旋回して正面に収める」意図だが、実際は敵の方へ旋回しない。密着した両機が互いの周りを回り続け、対目標角が FLANK のまま変わらない
2. SNIPER は近距離（`CLOSE`）の敵に MOVE しか選ばない（旧 `snp_rule_002` / `snp_rule_008`）。ATTACK のルールはすべて MID / FAR が条件。MOVE は最寄りの敵へ引き寄せられるため距離も開かず、敵を正面に捉えても撃たない

### 31.2 変更内容

**胴体の向き（`AiDecisionMixin._update_body_heading()`）**

| 行動 | 胴体の目標方向 |
|---|---|
| ATTACK / ENGAGE_MELEE（ターゲットあり） | ターゲット |
| MOVE（ターゲットが装備武器の最大射程内） | ターゲット（追加） |
| 上記以外 | `movement_heading_deg` |

射程外の敵へ移動しているときは、従来どおり移動方向を向く。全戦略に効く。

**胴体を向けるタイミング（`BattleSimulator.step()`）**

胴体向きの更新を、全ユニット分まとめて行動フェーズの前に行うのをやめた。各ユニットの行動の直前に、その時点の位置で向ける。

まとめて向けると、先に行動した敵の移動が反映されない。距離 5m 前後では敵が 1 ステップ（8m）で反対側へ抜ける。後から行動するユニットから見て射撃弧（30°）の外になり、撃てないまま時間切れになっていた。
MOVE 中も敵を向くようにしたことで、側面・背面からの命中で決着していた戦闘がこの膠着に陥りやすくなった（`test_los_obstacle.py::test_full_simulation_without_obstacles_unchanged` が 56% の確率で失敗した）。この変更で失敗は 0/300 回になった。

**SNIPER のルール（`sniper.json`）**

| ルール | 条件 | 出力 |
|---|---|---|
| `sniper_arc_004`（追加） | FRONTAL かつ HP HIGH かつ CLOSE | ATTACK |
| `sniper_arc_005`（追加） | FRONTAL かつ HP MEDIUM かつ CLOSE | ATTACK |
| `snp_rule_002`（削除） | CLOSE | MOVE |
| `snp_rule_008`（削除） | CLOSE かつ HP MEDIUM | MOVE |

近距離の敵は、正面なら撃ち、側面・背面なら `sniper_arc_002` / `sniper_arc_003` で旋回する。HP LOW のときは従来どおり RETREAT が勝つ。
DEFENSIVE / RETREAT の `arc_001`（FRONTAL かつ HIGH かつ CLOSE → ATTACK）と同じ形にそろえた。
SNIPER が近距離で距離を取る動きは、#598（交戦距離の制御）で扱う。

### 31.3 計測結果

`engagement_bench.py`（各 10 試行、シード 595〜604、`tactics.range` は BALANCED×BALANCED）。値は「変更前 → 変更後」。

| シナリオ | 戦略 | 戦闘時間 p50 | 時間切れ | A 勝率 |
|---|---|---|---|---|
| 格闘機同士（ガンダム vs グフ） | SNIPER | 500s → 44s | 100% → 0% | 0% → 90% |
| | DEFENSIVE | 500s → 50s | 90% → 0% | 0% → 90% |
| | AGGRESSIVE | 36s → 36s | 0% → 0% | 100% → 100% |
| | ASSAULT | 42s → 41s | 0% → 0% | 100% → 100% |
| ガンダム vs ザクII | SNIPER | 500s → 19s | 100% → 40% | 0% → 60% |
| | DEFENSIVE | 98s → 49s | 0% → 40% | 60% → 60% |
| | AGGRESSIVE | 261s → 14s | 50% → 0% | 50% → 100% |
| | ASSAULT | 73s → 13s | 20% → 0% | 80% → 100% |
| ゲルググ vs ガンダム | SNIPER | 500s → 70s | 100% → 0% | 0% → 20% |
| | DEFENSIVE | 382s → 84s | 40% → 0% | 0% → 0% |
| | AGGRESSIVE | 62s → 36s | 0% → 0% | 0% → 0% |
| | ASSAULT | 95s → 91s | 0% → 0% | 20% → 30% |
| グフ vs ガンダム | SNIPER | 500s → 52s | 100% → 0% | 0% → 0% |
| | DEFENSIVE | 500s → 62s | 90% → 0% | 10% → 0% |
| | AGGRESSIVE | 43s → 48s | 0% → 0% | 30% → 0% |
| | ASSAULT | 43s → 46s | 0% → 0% | 0% → 0% |

* 時間切れは 16 条件中 7 条件で減り、1 条件（ガンダム vs ザクII の DEFENSIVE）で増えた
* 後から行動するユニットも撃てるようになり、決着が早くなった（ガンダム vs ザクII の AGGRESSIVE 261s → 14s など）
* MOVE 中の機体も敵を向くため、攻撃セクタの FRONT 比率が上がった（例: ゲルググ vs ガンダムの DEFENSIVE で 60% → 97%）
* 残る時間切れ（ガンダム vs ザクII の SNIPER・DEFENSIVE 各 40%）は奇数シードだけで起きる。距離 1〜2m で両機が毎ステップすれ違い、互いが交互に背面へ回る。HP LOW のザクII は RETREAT（撤退ポイントがないため MOVE）を選び続ける。#598 の最小間隔で解消する見込み

### 31.4 テスト

* `backend/tests/unit/test_phase_6_1_fire_arc.py`: MOVE 中の胴体が、射程内の敵には旋回し、射程外の敵では移動方向に追従する。後から行動するユニットが、先に動いた敵の移動後の位置へ向く
* `backend/tests/unit/test_sniper_close_range.py`: SNIPER の行動選択（近距離で正面 → ATTACK、側面 → MOVE、HP LOW → RETREAT）と、SNIPER 同士の 1 対 1 が時間切れにならないこと

---

## 32. 膠着検知と仕切り直し（DISENGAGE）

Issue #599（Epic #594「交戦距離の制御と膠着の解消」の Sub-Issue 5）。

### 32.1 背景

行動判断がその瞬間の値だけで決まるため、外れ続ける格闘を同じように繰り返していた。
格闘機同士（ガンダム vs グフ）では、格闘ミスが 15〜33 秒続く戦闘があった。
攻撃が正面（セクタ倍率 ×0.35）に集中し、グフのヒートロッドは命中率 5〜15% 程度しかない。

そこで、ユニットごとに相手との「交戦記録」を持たせる。
記録から膠着度と優勢度を求めて行動判断の入力にし、互角の攻防が続いたら距離を取って攻撃方法を切り替える行動 DISENGAGE（仕切り直し）を追加した。

### 32.2 交戦記録（`backend/app/engine/engagement.py`）

記録の更新と膠着度・優勢度の計算は、エンジンの状態に依存しない独立モジュールにした（将来のマニューバ層へ移しやすくするため）。
記録は `unit_resources[unit_id]["engagement"]`（`EngagementRecord`）に置く。

| フィールド | 内容 |
|---|---|
| `opponent_id` | 相手のユニット ID |
| `started_at` | 交戦開始時刻（相手が `ENGAGEMENT_RECORD_RANGE` 以内に入った時刻） |
| `last_in_range_at` | 最後に `ENGAGEMENT_RECORD_RANGE` 以内にいた時刻 |
| `attacks` / `hits` | 自分の攻撃回数・命中数 |
| `attacked` / `attacked_hits` | 相手からの被攻撃回数・被命中数 |
| `damage_dealt` / `damage_taken` | 与えたダメージ・受けたダメージ |
| `last_hit_at` / `attacks_since_hit` | 自分の最後の命中時刻と、それ以降の攻撃回数 |

- **開始・継続・リセット**（`track_engagement()`）: 行動判断のたびに、現在のターゲットとの距離で更新する。ターゲットが変わったら記録を捨てる。`ENGAGEMENT_RECORD_RANGE` の外に `ENGAGEMENT_RECORD_RESET_SEC` いたら記録を捨てる
- **多対多**: 現在のターゲットとの記録だけを持つ。複数の相手を同時に記録すると、どの相手との膠着かを行動に結び付けにくいため
- **攻撃の記録**（`record_attack()`）: `CombatMixin._process_attack()` が命中・ミスの処理の後に `_record_attack_exchange()` を呼ぶ。攻撃側と防御側のうち、記録の相手が一致する側だけを更新する。ダメージは攻撃前後の HP の差で数える（格闘コンボと LUK の完全回避を含めるため）。命中はダメージが入った攻撃とする
- 攻撃のたびに、両機の `last_attack_exchange_at` も更新する（32.6 の「撃たない膠着」に使う）

### 32.3 膠着度・優勢度

**優勢度（-1〜1）**（`dominance()`）: `与ダメ ÷ 相手の最大 HP − 被ダメ ÷ 自分の最大 HP`。正なら優勢。

**膠着度（0〜1）**（`stalemate()`）: 次の 3 つのうち最も低い値（ファジィの AND と同じ min）。

| 要素 | 1 になる条件 |
|---|---|
| 攻撃回数 | 自分の最後の命中から `STALEMATE_FULL_ATTACKS`（3）回以上攻撃した |
| 経過時間 | 自分の最後の命中（無ければ交戦開始）から `STALEMATE_FULL_ELAPSED_SEC`（5s）以上たった |
| 互角さ | 優勢度の絶対値が `STALEMATE_DOMINANCE_EVEN`（0.15）以下。`STALEMATE_DOMINANCE_LIMIT`（0.3）で 0 |

攻撃回数と経過時間を「自分の最後の命中から」数えるのは、自分の攻め方が通じていないことを測るため。
交戦開始から数えると、序盤に一度当てただけで優勢度の差が残り、その後に外し続けても膠着と判定されなかった。
相手だけが当てている場合は、優勢度の低下として扱う。

どちらも行動判断のファジィ入力 `stalemate` / `dominance` として渡す（`AiDecisionMixin._compute_engagement_inputs()`）。
ルールとメンバーシップ関数は `fuzzy-engine.md` 6.5 節を参照。

### 32.4 行動判断（`AiDecisionMixin._decide_action()`）

活性化度が最も高い行動を選ぶ処理に、仕切り直しの状態管理を加えた。

1. 実行中の仕切り直しがあれば、終える条件を満たすまで DISENGAGE を続ける（最低継続時間）
2. 仕切り直しを始められないときは、活性化度から DISENGAGE を除いて選び直す
3. 既存の制約ガード（`_resolve_final_action()`）を適用する
4. DISENGAGE になったら仕切り直しを始める

**始められる条件**（`_can_start_disengage()`）

- RETREAT 戦略中でない（既存の撤退を優先する）
- 格闘武器を持っている。射撃武器しか持たない機体には切り替える攻撃方法が無く、仕切り直しが後退するだけになるため。計測では、ザクII（MG のみ）が格闘専用機から下がり続け、HP が減ると RETREAT（撤退ポイントが無いため MOVE）で間合いを保って逃げ切る戦闘が 400 秒を超えた
- 交戦記録がある
- 前の仕切り直しから `DISENGAGE_COOLDOWN_SEC` たっている
- ターゲットとの距離が目標距離より近い

**続ける条件**（`_should_continue_disengage()`）

- ターゲットとの距離が目標距離未満で、開始から `DISENGAGE_MAX_SEC` 未満
- RETREAT 戦略になった、または撤退ポイントがあって RETREAT が最も高い活性化度のときは終える
- ターゲットが変わった、索敵済みの敵がいなくなったときも終える

### 32.5 仕切り直しの実行

**開始**（`_start_disengage()`）

- 目標距離（`_disengage_target_distance()`）: 射撃武器の目標交戦距離（#598 の間合い）を `DISENGAGE_DISTANCE_MIN`〜`DISENGAGE_DISTANCE_MAX` に収める。射撃武器が無ければ下限
- 自分の交戦記録は捨てる。相手の記録は優勢度の累計だけ 0 に戻す（`restart_bout()`）。昔の命中による優勢が残ると、相手がいつまでも膠着とみなさないため。最後の命中からの数えは残す
- ブーストが使えれば使う（`MovementMixin._start_boost()`）。最大継続時間・EN 枯渇で止まり、仕切り直しを終えるときにも止める。後退中（2.3.1）は始めず、ブースト中に後退へ入ったときも止める。仕切り直しは敵を向いたまま下がるので、ブーストは下がり始めるまでの短い間しか効かない
- `DISENGAGE` ログを記録する（32.7）

**移動**（`MovementMixin._disengage_force()`）: ターゲットから離れる向きを `DISENGAGE_LATERAL_ANGLE_DEG`（35°）横へ傾けた力（`DISENGAGE_REPULSION_COEFF`）。真後ろに下がると、追ってくる相手との距離が開かないため。左右はユニット ID で固定する（ストレイフと同じ `_unit_side_sign()`）。マップ境界の手前では境界へ向かう成分を消す（#598 の間合いと同じ `_suppress_boundary_approach()`）。

**胴体**: ターゲットを向いたまま下がる（`_update_body_heading()`）。背を向けると背面から撃たれるため。

**攻撃**（`ActionHandlerMixin._handle_disengage_action()`）: 射撃武器が射程内なら撃つ。格闘武器では攻撃しない。

**仕切り直しの後**（`_end_disengage()`）

- `DISENGAGE_RANGED_PREFERENCE_SEC` の間、射撃武器を優先する（`_prefers_ranged()`）。この間に命中させたら、その時点で終える
  - 武器選択（`_select_weapon_fuzzy()`）は、使える射撃武器があれば射撃武器だけから選ぶ
  - ENGAGE_MELEE は ATTACK にする
  - 持ち替えポリシー BALANCED は、格闘武器から射撃武器へ必ず持ち替える（候補が射撃武器だけになり、スコア差では判断できないため）。NEVER / RACK_ONLY / AGGRESSIVE の意味は変えない
  - 移動の基準武器（`_get_reference_weapon()`）は、射撃武器が再使用待ちの間も射撃武器のままにする。格闘武器を基準にすると、撃つたびに格闘の間合いへ詰めてしまうため
- 射撃武器を持たない機体は、この期間にターゲットの側面（胴体の向きに対して自機に近い側、`DISENGAGE_REENTRY_FLANK_OFFSET` 先）へ引き寄せられて再突入する（`_reentry_flank_attraction()`）

### 32.6 撃たない膠着（撤退先の無い RETREAT と MOVE）

#598 の後、射撃機同士の 1 対 1 で新しい膠着が見つかった（Issue コメント）。
両機の HP が下がり、DEFENSIVE の `def_rule_002`（HP LOW → RETREAT）で両機とも RETREAT を選ぶ。
撤退ポイントが無いと RETREAT は MOVE になり、MOVE は撃たないため、間合いを保って周回したまま時間切れになる。

`_resolve_final_action()` で、撤退先の無い RETREAT は次のように決める（`_is_idle_stalemate()`）。

- 武器の射程内に敵がいるのに、`IDLE_STALEMATE_SEC` 攻撃のやり取り（自分の攻撃・被攻撃）が無ければ ATTACK にする
- 一度そう判定したら、`IDLE_STALEMATE_ATTACK_SEC` は ATTACK を続ける。1 発撃つたびに判定が解けて撃たなくなるのを防ぐため
- それ以外は従来どおり MOVE

撤退ポイントが無い戦場での RETREAT 自体の見直しは、逃走度（#623）・逃走モード（#624）で扱う。

#601 で、同じ判定を MOVE にも使うようにした。FLEE（34 章）で射程ぎりぎりを保つと、DEFENSIVE のファジィ規則は 400m 以上を FAR とみなして MOVE を選ぶ。
両機とも撃たずに周回し、ゲルググ vs ガンダム（DEFENSIVE・FLEE×FLEE）が全戦時間切れになったため。

### 32.7 ログ・セリフ・BattleViewer

**`DISENGAGE` ログ**（`BattleLog.action_type`）: 仕切り直しの開始時に 1 件記録する。

| フィールド | 内容 |
|---|---|
| `target_id` | 仕切り直した相手 |
| `message` | 例: 「[アムロ]のガンダムはグフとの攻防を互角と見て距離を取り、仕切り直す」（劣勢のときは「劣勢と見て」） |
| `chatter` | 性格ごとのセリフ（`BATTLE_CHATTER[...]["disengage"]`、例: 「互角か…一度引く！」）。他のセリフと同じく 30% の確率で付く |
| `details` | `reason`（`STALEMATE` / `DISADVANTAGE`）、`stalemate`、`dominance`、`target_distance`、交戦記録の攻撃・命中・被攻撃・被命中の回数 |

`AI_DECISION` ログのメッセージにも膠着度・優勢度を追加した。

**BattleViewer**（`battle-viewer-feature.md` 参照）: ログ一覧で太字の紫で表示する。3D シーンでは DISENGAGE の後 1.5 秒、機体の上に「↩ 仕切り直し」を出す。自機の仕切り直しはチャプタートラックにも出す。

### 32.8 定数（`backend/app/engine/constants.py`）

値はすべて暫定で、調整は総合バランス調整（#587）で行う。

| 定数 | 値 | 内容 |
|---|---|---|
| `ENGAGEMENT_RECORD_RANGE` | 250m | 交戦記録を始める距離 |
| `ENGAGEMENT_RECORD_RESET_SEC` | 5s | 記録の距離の外にこの時間いたら記録を捨てる |
| `STALEMATE_FULL_ATTACKS` | 3 | 膠着度が最大になる、自分の最後の命中からの攻撃回数 |
| `STALEMATE_FULL_ELAPSED_SEC` | 5s | 膠着度が最大になる、自分の最後の命中からの経過時間 |
| `STALEMATE_DOMINANCE_EVEN` / `STALEMATE_DOMINANCE_LIMIT` | 0.15 / 0.3 | 互角とみなす優勢度の幅と、膠着度を 0 にする優勢度 |
| `IDLE_STALEMATE_SEC` / `IDLE_STALEMATE_ATTACK_SEC` | 10s / 5s | 撃たない膠着とみなす時間と、その後 ATTACK を続ける時間 |
| `DISENGAGE_LATERAL_ANGLE_DEG` | 35° | 後退の向きを真後ろから横へずらす角度 |
| `DISENGAGE_REPULSION_COEFF` | 4.0 | 後退の力の係数 |
| `DISENGAGE_DISTANCE_MIN` / `DISENGAGE_DISTANCE_MAX` | 150m / 300m | 目標距離の下限・上限 |
| `DISENGAGE_MAX_SEC` | 3s | 仕切り直しの最大継続時間 |
| `DISENGAGE_RANGED_PREFERENCE_SEC` | 5s | 仕切り直しの後に射撃武器を優先する時間 |
| `DISENGAGE_COOLDOWN_SEC` | 5s | 次の仕切り直しを始められるまでの時間 |
| `DISENGAGE_REENTRY_FLANK_OFFSET` / `DISENGAGE_REENTRY_FLANK_COEFF` | 100m / 2.0 | 射撃武器の無い機体が再突入で目指す側面の位置と、引力の係数 |

### 32.9 計測結果

`engagement_bench.py`（各 10 試行、シード 595〜604、`tactics.range` は BALANCED×BALANCED）。値は「変更前（main）→ 変更後」。

| シナリオ | 戦略 | 格闘ミス最長 | 持ち替え/分 | 戦闘時間 p50 | 時間切れ | A 勝率 |
|---|---|---|---|---|---|---|
| 格闘機同士（ガンダム vs グフ） | AGGRESSIVE | 23.3s → 7.4s | 7.5 → 5.9 | 26s → 18s | 0% → 0% | 100% → 100% |
| | DEFENSIVE | 14.8s → 0.0s | 6.3 → 3.5 | 24s → 23s | 0% → 0% | 100% → 100% |
| | SNIPER | 33.0s → 13.3s | 0.6 → 2.5 | 40s → 28s | 0% → 0% | 100% → 100% |
| | ASSAULT | 14.3s → 25.8s | 8.8 → 8.3 | 27s → 23s | 0% → 0% | 100% → 100% |
| 格闘専用機 vs 射撃機（ガンダム[サーベル] vs ザクII） | AGGRESSIVE | 13.2s → 15.7s | - | 26s → 31s | 0% → 0% | 100% → 100% |
| | DEFENSIVE | 7.7s → 14.7s | - | 27s → 26s | 0% → 0% | 100% → 100% |
| | SNIPER | 8.8s → 10.6s | - | 34s → 35s | 0% → 0% | 100% → 100% |
| | ASSAULT | 6.6s → 6.6s | - | 21s → 22s | 0% → 0% | 100% → 100% |
| ゲルググ vs ガンダム | DEFENSIVE | - | - | 63s → 50s | 10% → 0% | 60% → 50% |

* 射撃機同士（ガンダム vs ザクII）は全指標が変わらない。射撃武器しか持たない機体は仕切り直さないため
* グフ vs ガンダム（射撃機）は、ASSAULT の戦闘時間 p50 が 23s → 24s になった以外は変わらない
* ゲルググ vs ガンダムは DEFENSIVE だけが変わった。時間切れ（10%）は、32.6 の撃たない膠着の対策で 0% になった
* 格闘機同士の 150m 未満の割合は、AGGRESSIVE・DEFENSIVE・ASSAULT で 46〜50% → 31〜42% に下がった（仕切り直しで距離を取る時間が増えたため）。SNIPER は 16% → 20%

**格闘ミス最長 8 秒以内（完了条件）について**: AGGRESSIVE（7.4s）と DEFENSIVE（0.0s）は達成した。SNIPER（13.3s）と ASSAULT（25.8s）は未達。

* 残る長い連続は、どちらも 1〜2 戦の外れ値。正面への攻撃（×0.35）では、サーベルでも約 30%、ヒートロッドは約 15%、ライフル・MG は 5〜25% しか当たらない。格闘ミスの連続は「その機体が何かを命中させる」まで途切れないため、射撃に切り替えても射撃も外し続けると、次の格闘ミスまでが 1 つの連続として数えられる
* 例: ASSAULT のシード 596 では、ガンダムが接近のたびにサーベルを 1 回外し、間のライフルも外し続けて 25.8s（格闘ミス 3 回）になった
* 主要な定数（攻撃回数 2〜3、経過時間 3〜5s、射撃優先 3〜8s、再使用までの時間 3〜5s）を 20 シードで振ったが、全戦略で 8 秒以内に収まる組み合わせは無く、最悪値は外れ値で入れ替わった。そのため Issue の例の値（3 回・5 秒・5 秒）のままにした
* 命中率の底上げ（正面のセクタ倍率など）は総合バランス調整（#587）で扱う

### 32.10 テスト

* `backend/tests/unit/test_engagement_disengage.py`: 交戦記録の開始・継続・リセット、攻撃による更新、膠着度・優勢度の計算、ファジィ推論の DISENGAGE 選択（膠着・劣勢で選び、優勢では選ばない）、DISENGAGE の最低継続時間と終了条件・RETREAT の優先・再使用までの時間、射撃優先と持ち替え、射撃武器の無い機体の回り込み、後退の向き、撃たない膠着
* `frontend/tests/unit/battleChapters.test.ts` / `battleSnapshot.test.ts` / `logFormatter.test.ts`: 仕切り直しのチャプター・機体上の表示・ログの配色

## 33. 鍔迫り合い（正面同士の同時格闘）

Issue #600（Epic #594 Sub-Issue 6）。正面同士で両機がほぼ同時に格闘したとき、通常の命中判定をせず「鍔迫り合い」として両機を押し離す。
斬り合いの後に間合いが生まれ、射撃への切り替えや仕切り直し（32 章）につながる。

### 33.1 発生条件（`MeleeClashMixin._try_melee_clash()`、`backend/app/engine/melee_clash.py`）

行動フェーズは各ユニットを順に処理するため、同時攻撃は「先に行動した側」が検出する。
`CombatMixin._process_attack()` が格闘武器のリソースチェックを通した直後、命中判定の前に次をすべて確かめる。

| 条件 | 内容 |
|---|---|
| 自機の武器 | 格闘武器（`weapon_type == "MELEE"` または `is_melee`） |
| 相手のターゲット | 相手のステップ内のターゲット（`_select_target_fuzzy()` のキャッシュ）が自機 |
| 相手の格闘 | 相手が `MELEE_CLASH_WINDOW_SEC`（0.3 秒）以内に自機へ格闘を出す（`_pending_melee_weapon()`）。行動フェーズの武器の選び方に合わせ、ENGAGE_MELEE（`MELEE_BOOST_ARRIVAL_RANGE` 以内）は先頭の格闘武器、ATTACK / HIT_AND_AWAY は手持ちの武器（`active_weapon_id`）で判定する。持ち替え中・撃破済み・撤退済み・射程外は除く |
| 向き | 互いの攻撃セクタ（`calculate_attack_sector()`）がどちらも FRONT |
| 再発までの時間 | どちらの機体も、前回の鍔迫り合いから `MELEE_CLASH_COOLDOWN_SEC`（8 秒）以上たっている |
| 確率 | 上をすべて満たしたとき `MELEE_CLASH_CHANCE`（30%）で発生する。毎回起きると単調になるため |

* 先に行動した側が両機の格闘をまとめて解決するので、「先に動いた側の攻撃で相手が撃破され、相手の攻撃が消える」という処理順の偏りが起きない
* 相手の攻撃が同じステップで先に通常どおり解決された場合、相手の格闘は再使用待ちに入っているため、後から行動する側は鍔迫り合いにしない
* 乱数（`random`）は条件がすべてそろったときだけ引く。条件を満たさない戦闘（射撃機同士など）の乱数列は変わらない
* 再発までの時間は、鍔迫り合いで両機の格闘の再使用待ちがそろい、次の格闘も「同時」になって続けて起きやすいために入れた（入れないと格闘専用機同士の ASSAULT で 9 回/分になった）

### 33.2 効果（`_resolve_melee_clash()`）

* 両機の格闘は攻撃したものとして再使用待ちに入る（`_consume_attack_resources()`）。ダメージ・格闘コンボ・格闘命中後の再配置（`POST_MELEE_DISTANCE`）は無い
* 押し離す間隔を `MELEE_CLASH_SEPARATION_MIN`〜`MELEE_CLASH_SEPARATION_MAX`（80〜120m）から一様に選び、押す力の比で両機に分ける（`push_shares()`）。押す力の弱い側が大きく飛ばされる。1 機の受け持ちは `MELEE_CLASH_PUSH_SHARE_MAX`（70%）まで
  * 押す力（`_clash_power()`）= 武器の威力 × 機体の格闘適性（`melee_aptitude`）×（1 + パイロットの MEL × `MELEE_CLASH_MEL_WEIGHT`）
* 両機の速度（`velocity_vec`）を 0 にする。突進の速度が残ると押し離しを打ち消すため
* 交戦記録（32.2）には、両機が互いに 1 回ずつ外した攻撃として残す（`_record_attack_exchange()` をダメージ 0 で 2 回）。攻撃回数と最後の命中からの攻撃回数が増え、膠着度（32.3）が上がる

### 33.3 押し離しの移動（慣性モデル）

押し離しは瞬間移動ではなく、機体自身の速度とは別の速度（`unit_resources[unit_id]["knockback"]`、`Knockback`）として持つ。

* `start_knockback()`: `MELEE_CLASH_KNOCKBACK_SEC`（0.8 秒）で速度が 0 になり、合計で受け持ちの距離だけ進む初速と減速度を決める
* `MovementMixin._apply_inertia()` が機体自身の速度による移動に、`_advance_knockback()` の移動量を足す。1 ステップの移動量は速度の平均で求めるので、合計は受け持ちの距離に一致する
* マップの外へ出る分は境界で止める。`_boundary_repulsion()` では押し戻せない速さのため
* 押し離されている間に ENGAGE_MELEE の格闘が通っても、`POST_MELEE_DISTANCE` への再配置はしない（`_process_engage_melee()`）。再配置で押し離しを打ち消さないため

### 33.4 ログ・セリフ・BattleViewer

**`MELEE_CLASH` ログ**（`BattleLog.action_type`）: 鍔迫り合いを解決した側（先に行動した側）を `actor_id` にして 1 件記録する。

| フィールド | 内容 |
|---|---|
| `target_id` | 相手 |
| `weapon_name` / `weapon_id` | 自機の格闘武器 |
| `damage` | 0 |
| `message` | 例: 「[アムロ]のガンダムの[Beam Saber]とグフの[Heat Rod]が鍔迫り合い！ グフが押し負けて弾き飛ばされる」。受け持ちの差が 1.2 倍以内なら「両機が弾かれて間合いが開く」 |
| `chatter` | 性格ごとのセリフ（`BATTLE_CHATTER[...]["clash"]`、例: 「押し切ってやる！」）。他のセリフと同じく 30% の確率で付く |
| `details` | `target_weapon_name` / `target_weapon_id`（相手の格闘武器）、`actor_push_m` / `target_push_m`（各機が押し離される距離） |

**BattleViewer**（`battle-viewer-feature.md` 参照）: 射線は出さず、両機の武器名と、両機の中間に火花と「鍔迫り合い！」を出す。自機が絡む鍔迫り合いはチャプタートラックと HUD ログにも出す。

### 33.5 定数（`backend/app/engine/constants.py`）

値はすべて暫定で、調整は総合バランス調整（#587）で行う。

| 定数 | 値 | 内容 |
|---|---|---|
| `MELEE_CLASH_WINDOW_SEC` | 0.3s | 相手の格闘がこの時間以内に出せるなら同時の攻撃とみなす |
| `MELEE_CLASH_CHANCE` | 0.3 | 条件がそろったときに鍔迫り合いになる確率 |
| `MELEE_CLASH_COOLDOWN_SEC` | 8s | 鍔迫り合いの後、両機が次の鍔迫り合いを起こさない時間 |
| `MELEE_CLASH_SEPARATION_MIN` / `MELEE_CLASH_SEPARATION_MAX` | 80m / 120m | 押し離しで広がる両機の間隔 |
| `MELEE_CLASH_KNOCKBACK_SEC` | 0.8s | 押し離しの速度が 0 になるまでの時間 |
| `MELEE_CLASH_PUSH_SHARE_MAX` | 0.7 | 押し負けた側が受け持つ間隔の割合の上限 |
| `MELEE_CLASH_MEL_WEIGHT` | 0.05 | 押す力に掛ける、MEL 1 あたりの増分 |

### 33.6 計測結果

`engagement_bench.py`（各 30 試行、シード 595〜624、`tactics.range` は BALANCED×BALANCED）。変更前は鍔迫り合いを無効にした同じコード。
「鍔迫り合い/分」は両機あわせた回数、「格闘比」は格闘の攻撃（命中判定した格闘 + 鍔迫り合い 1 回につき 2 回）のうち鍔迫り合いになった割合。

| シナリオ | 戦略 | 鍔迫り合い/分 | 格闘比 | 1 戦あたり | 戦闘時間 p50 | 150m 未満 | A 勝率 |
|---|---|---|---|---|---|---|---|
| 格闘専用機同士（ガンダム[サーベル] vs グフ[ヒートロッド]） | AGGRESSIVE | 2.7 | 6% | 1.0 回 | 19s → 22s | 83% → 75% | 100% → 100% |
| | DEFENSIVE | 1.6 | 4% | 0.6 回 | 21s → 21s | 82% → 78% | 100% → 100% |
| | SNIPER | 1.9 | 5% | 0.7 回 | 20s → 22s | 79% → 68% | 93% → 100% |
| | ASSAULT | 4.6 | 10% | 1.7 回 | 16s → 21s | 86% → 80% | 100% → 100% |
| 格闘機同士（ガンダム[サーベル+ライフル] vs グフ[ヒートロッド+MG]） | ASSAULT | 0.1 | 1% | 0.0 回 | 23s → 23s | 40% → 39% | 100% → 100% |

* 格闘機同士（射撃武器あり）は、AGGRESSIVE・DEFENSIVE・SNIPER で 1 回も起きなかった。#598・#599 の後は、グフがほぼザクマシンガンを構えて撃ち合うため、両機が同時に格闘を出す場面が少ない
* 格闘専用機同士でも 1 戦あたり 0.6〜1.7 回で、格闘の 4〜10% にとどまる。多すぎないと判断した
* 確率と再発までの時間は、確率 0.3 / 0.5 × 時間 5 / 8 / 10 秒で比べた。確率 0.5・時間なしでは ASSAULT で 9.1 回/分・戦闘時間 p50 16s → 28s になった
* 射撃武器だけの機体が絡むシナリオ（`ranged_*`、`melee_vs_ranged`、`melee_only_vs_ranged`）は、相手が格闘を出さないため乱数列も含めて変わらない
* `tactics.range` の MELEE×MELEE は BALANCED×BALANCED と同じ結果になった（`tactics.range` の反映は Sub-Issue 7）

### 33.7 テスト

* `backend/tests/unit/test_melee_clash.py`: 発生条件（正面同士・時間差の範囲内／再使用待ち・移動中・持ち替え中・背後・ターゲット違い・射撃武器では起きない・確率に外れたら通常の命中判定・再発までの時間）、効果（ダメージなし・両機の再使用待ち・ログ・交戦記録）、押し離しの向きと距離（反対向き・弱い側が大きく飛ぶ・割合の上限・合計の移動量）、慣性モデルでの移動（少しずつ動く・マップ境界で止まる・ENGAGE_MELEE で再配置しない・シミュレーションを進めると間隔が開く）
* `backend/tests/unit/test_engagement_bench.py`: 鍔迫り合いの回数と格闘比の集計
* `frontend/tests/unit/battleHitEffects.test.ts` / `battleChapters.test.ts` / `logFormatter.test.ts`: 鍔迫り合いの演出・HUD ログ・チャプター・ログの配色

## 34. 戦術設定（tactics.range）とパイロット能力の反映

Issue #601（Epic #594 Sub-Issue 7）。ガレージの戦術設定 `tactics.range` と、パイロットの MEL / INT / REF を、間合い・膠着への粘り・離脱判断に反映する。
以前の `tactics.range` は保存時のチェック（`validate_tactics()`）でしか使われず、バトルエンジンは参照していなかった。

補正値の計算は、エンジンの状態に依存しない `backend/app/engine/engagement_style.py` にまとめた。
`tactics.range` が未設定・許容値外の機体は BALANCED として扱う（`tactics_range()`）。

### 34.1 `tactics.range` ごとの挙動

| 設定 | 目標交戦距離（2.3.4） | 間合いの基準武器 | 膠着への粘り | 格闘突入（ENGAGE_MELEE） | 仕切り直しの後の射撃優先 |
|---|---|---|---|---|---|
| MELEE | 変えない | 格闘武器 | ×1.5（粘る） | そのまま | ×0.4（すぐ再突入する） |
| RANGED | 変えない | 射撃武器 | ×0.6（粘らない） | ATTACK にする | ×1.6（射撃を続ける） |
| BALANCED | 変えない | 武器選択の結果（従来どおり） | ×1.0 | そのまま | ×1.0 |
| FLEE | 射撃武器は射程の上限 | 射撃武器 | ×0.6（粘らない） | ATTACK にする | ×2.0（距離を取り続ける） |

* **戦略モードとの優先関係**: 目標交戦距離は、戦略モードの倍率（`ENGAGEMENT_RANGE_STRATEGY_MULTIPLIERS`）を掛けた後に `tactics.range` で補正する。FLEE の射撃武器は、倍率によらず `range / (1 + 許容幅の割合)`（許容幅の外側の端が射程に一致する距離）を目標にする。格闘武器の目標距離は変えない
* **間合いの基準武器**（`MovementMixin._preferred_reference_weapon()`）: 武器選択（`_select_weapon_fuzzy()`）の結果が設定と合わないとき、合う種類の武器に選び直す。再使用待ちの武器も候補に含める（撃つたびに基準が入れ替わり、間合いが揺れるため）。候補が複数あれば射程の長いものを使う。仕切り直しの後の射撃優先中（32.5）は、設定によらず射撃武器を基準にする
  * MELEE は遠くでも格闘の間合いへ詰め、途中は射撃武器で撃つ
  * RANGED は近づかれても射撃の間合いを保つため、ばねの力で離れる
* **膠着への粘り**: 膠着度（32.3）が最大になる攻撃回数と経過時間（`STALEMATE_FULL_ATTACKS` / `STALEMATE_FULL_ELAPSED_SEC`）に倍率を掛ける（`stalemate()` の `patience`）。粘らない設定は、劣勢でなくても早めに仕切り直す
* **格闘突入**: RANGED / FLEE は、ファジィ推論が ENGAGE_MELEE を選んでも ATTACK にする（`AiDecisionMixin._keeps_range()`）
* **武器選択**: 格闘武器のスコア（0〜1）に `TACTICS_MELEE_WEAPON_SCORE_BIAS`（MELEE +0.1、RANGED −0.1、FLEE −0.2）を足す。持ち替えポリシー BALANCED の判断にも、足した後のスコアを使う
* **仕切り直しの後**: 射撃武器を優先する時間（`DISENGAGE_RANGED_PREFERENCE_SEC`）に倍率を掛ける。射撃武器の無い機体が側面から再突入する期間（32.5）も同じ長さになる

**装備と矛盾する設定**: 使える武器に合わせる。

| 設定 | 装備 | 挙動 |
|---|---|---|
| MELEE | 射撃武器だけ | 格闘武器の候補が無いため、射撃武器の間合いで戦う |
| RANGED / FLEE | 格闘武器だけ | 射撃武器の候補が無いため格闘武器を基準にし、ENGAGE_MELEE もそのまま選ぶ。膠着への粘りと射撃優先の倍率だけが効く |

**NPC**: `build_npc_tactics()`（`backend/app/core/npc_data.py`）が性格ごとに range を設定している（AGGRESSIVE → MELEE、CAUTIOUS → BALANCED、その他 → RANGED）。そのため NPC の挙動も変わる。

### 34.2 パイロット能力

影響は小さめから始める。1 あたりの増分に上限を設ける。

| 能力 | 効果 | 1 あたり | 上限 |
|---|---|---|---|
| MEL（格闘技巧） | 膠着への粘りの倍率を上げる（`stalemate_patience()`） | +2% | +40% |
| INT | 劣勢（優勢度が負）を大きく見積もる。離脱判断の入力 `dominance` に掛ける（`perceived_dominance()`）。優勢と互角は変えない | +2% | +40%（−1 で止める） |
| REF | 仕切り直しの最長時間（`DISENGAGE_MAX_SEC`）を短くする（`disengage_max_sec()`） | −1% | −30% |
| REF | 仕切り直し中の旋回速度（`max_turn_rate`）を上げる（`disengage_turn_multiplier()`） | +2% | +30% |

* INT による見積もりは、行動判断の入力・`AI_DECISION` ログ・`DISENGAGE` ログの `dominance` に出る。交戦記録の値は変えない
* REF による持ち替え時間の短縮は、既存の `calculate_weapon_switch_lock_sec()` のまま

### 34.3 定数（`backend/app/engine/constants.py`）

値はすべて暫定で、調整は総合バランス調整（#587）で行う。表に無い設定は補正しない（倍率 1.0、加算 0）。

| 定数 | 値 | 内容 |
|---|---|---|
| `TACTICS_STALEMATE_PATIENCE` | MELEE 1.5 / RANGED 0.6 / FLEE 0.6 | 膠着とみなすまでの攻撃回数と経過時間に掛ける倍率 |
| `TACTICS_RANGED_PREFERENCE_MULTIPLIERS` | MELEE 0.4 / RANGED 1.6 / FLEE 2.0 | 仕切り直しの後に射撃武器を優先する時間に掛ける倍率 |
| `TACTICS_MELEE_WEAPON_SCORE_BIAS` | MELEE +0.1 / RANGED −0.1 / FLEE −0.2 | 武器選択で格闘武器のスコアに足す値 |
| `PILOT_MEL_PATIENCE_PER_POINT` / `PILOT_MEL_PATIENCE_MAX` | 0.02 / 0.4 | MEL による粘りの増分と上限 |
| `PILOT_INT_CAUTION_PER_POINT` / `PILOT_INT_CAUTION_MAX` | 0.02 / 0.4 | INT による劣勢の見積もりの増分と上限 |
| `PILOT_REF_DISENGAGE_TURN_PER_POINT` / `PILOT_REF_DISENGAGE_TURN_MAX` | 0.02 / 0.3 | REF による仕切り直し中の旋回速度の増分と上限 |
| `PILOT_REF_DISENGAGE_SEC_REDUCTION_PER_POINT` / `PILOT_REF_DISENGAGE_SEC_REDUCTION_MAX` | 0.01 / 0.3 | REF による仕切り直しの最長時間の短縮率と上限 |

### 34.4 ガレージの表示

* `frontend/src/app/garage/components/TacticsSelector.tsx`: 選択肢の名前を挙動に合わせ（RANGED「射撃距離維持」、FLEE「射程限界から射撃」）、選んだ設定の説明を補足文に出す
* `frontend/src/components/Social/PlayerProfileModal.tsx`: 戦術の表記を同じ名前にそろえた（近接突撃 / 射撃距離維持 / バランス / 射程限界）

### 34.5 計測結果

`engagement_bench.py`（シード 595〜）。`--ranges` で両機に同じ設定を与え、`--pilot` でパイロット能力を変えた。「仕切り直し/分」は 1 機あたりの DISENGAGE の回数（今回追加した指標）。

**`tactics.range` ごとの差**（各 10 試行、パイロット能力はすべて 1。値は「変更前（main）→ 変更後」。変更前は設定によらず同じ値）

| シナリオ | 戦略 | 設定 | 距離 p50 | 150m 未満 | 仕切り直し/分 | 戦闘時間 p50 |
|---|---|---|---|---|---|---|
| 格闘機同士（ガンダム[サーベル+ライフル] vs グフ[ヒートロッド+MG]） | AGGRESSIVE | BALANCED | 171m → 187m | 42% → 38% | 3.1 → 3.7 | 18s → 25s |
| | | MELEE | 171m → 105m | 42% → 72% | 3.1 → 3.1 | 18s → 17s |
| | | RANGED | 171m → 318m | 42% → 0% | 3.1 → 0.0 | 18s → 11s |
| | | FLEE | 171m → 380m | 42% → 0% | 3.1 → 0.0 | 18s → 13s |
| | DEFENSIVE | BALANCED | 213m → 212m | 31% → 30% | 4.7 → 4.3 | 23s → 22s |
| | | MELEE | 213m → 106m | 31% → 70% | 4.7 → 2.6 | 23s → 14s |
| | | RANGED | 213m → 313m | 31% → 0% | 4.7 → 0.0 | 23s → 10s |
| | | FLEE | 213m → 380m | 31% → 0% | 4.7 → 0.0 | 23s → 13s |
| 格闘専用機同士（ガンダム[サーベル] vs グフ[ヒートロッド]） | AGGRESSIVE | BALANCED | 109m → 109m | 74% → 75% | 4.6 → 3.9 | 27s → 21s |
| | | MELEE | 109m → 108m | 74% → 74% | 4.6 → 2.9 | 27s → 24s |
| | | RANGED | 109m → 108m | 74% → 76% | 4.6 → 5.7 | 27s → 23s |
| | ASSAULT | MELEE | 93m → 96m | 81% → 81% | 4.2 → 3.4 | 22s → 18s |
| | | RANGED | 93m → 95m | 81% → 83% | 4.2 → 6.8 | 22s → 24s |
| ゲルググ vs ガンダム（射撃機同士） | DEFENSIVE | FLEE | 397m → 481m | 0% → 0% | 0.0 → 0.0 | 50s → 62s（時間切れ 0% → 0%） |

* 射撃武器を持つ格闘機同士では、設定どおりに間合いが分かれた（MELEE 約 100m、BALANCED 約 200m、RANGED 約 300m、FLEE は射程の上限の約 380m）。MELEE は粘るため仕切り直しが減り、RANGED / FLEE は格闘の間合いに入らないため仕切り直しが 0 になった
* 格闘専用機同士は、使える武器が格闘だけなので間合いは変わらない（装備と矛盾する設定）。粘りの差だけが仕切り直しの頻度に出た（MELEE で減り、RANGED / FLEE で増える）
* FLEE を入れた最初の実装では、ゲルググ vs ガンダムの DEFENSIVE・FLEE×FLEE が 10 戦すべて 1 発も撃たずに時間切れになった。32.6 の撃たない膠着の判定を MOVE にも使うようにして、時間切れは 0% になった
* グフ（MELEE）vs ガンダム[ライフル] は距離 p50 310m のまま変わらない。両機の速度が同じ（80）で、ガンダムが射撃の間合いを保とうと下がるため追いつけない（2.3.4「遅い格闘機は速い射撃機に引き撃ちされる」）。格闘機の接近手段は総合バランス調整（#587）で扱う
* BALANCED の値も変わったのは、パイロット能力 1 による補正（MEL・INT・REF がそれぞれ 2% 前後）と撃たない膠着の判定の変更で、乱数の消費順が変わったため
* 射撃機同士（ガンダム vs ザクII）の BALANCED / MELEE / RANGED は全指標が変わらない。射撃武器しか持たず、間合いの基準武器が変わらないため

**パイロット能力ごとの差**（各 20 試行、`--ranges BALANCED,MELEE`。基準は全能力 0、比べる能力だけ 20）

| シナリオ | 戦略・設定 | 仕切り直し/分（全能力 0） | MEL 20 | INT 20 | REF 20 |
|---|---|---|---|---|---|
| 格闘機同士 | AGGRESSIVE・BALANCED | 3.2 | 3.1 | 4.0 | 2.9 |
| | AGGRESSIVE・MELEE | 3.4 | 1.9 | 4.0 | 2.9 |
| | DEFENSIVE・MELEE | 3.6 | 2.2 | 3.7 | 3.6 |
| | ASSAULT・MELEE | 2.8 | 1.5 | 3.4 | 2.5 |
| 格闘専用機同士 | AGGRESSIVE・BALANCED | 3.5 | 2.4 | 5.9 | 3.9 |
| | DEFENSIVE・BALANCED | 4.6 | 3.8 | 5.6 | 5.6 |
| | ASSAULT・BALANCED | 3.9 | 2.9 | 4.9 | 4.6 |

* 両シナリオ・4 戦略・2 設定の 16 条件すべてで、MEL 20 は仕切り直しが減り、INT 20 は増えた（または同じ）
* REF は仕切り直しを始める判断には使わない。仕切り直しの長さと旋回の速さに効くため、頻度の増減はそろわない
* MEL は格闘の攻撃力、INT はクリティカル率と回避率、REF はイニシアチブにも効く。戦闘時間の差にはこれらの効果も含まれる

### 34.6 テスト

* `backend/tests/unit/test_tactics_range_engagement.py`: 補正値の計算（粘り・劣勢の見積もり・仕切り直しの時間と旋回・未設定の扱い）、膠着度・優勢度への反映（設定・MEL・INT）、目標交戦距離（FLEE）と間合いの基準武器（MELEE は遠くでも格闘、RANGED / FLEE は近くても射撃、RANGED は近づかれたら離れる）、格闘武器のスコア補正、格闘突入の制約、仕切り直しの後の射撃優先の長さ、REF による仕切り直しの短縮と旋回、装備と矛盾する設定、全設定と装備の組での戦闘、NPC（AGGRESSIVE）の戦術
* `backend/tests/unit/test_engagement_disengage.py`: 撃たない膠着で MOVE を攻撃にする
