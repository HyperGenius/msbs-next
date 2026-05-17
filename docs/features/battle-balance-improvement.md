# バトルバランス改善 機能仕様書（ドラフト）

**バージョン:** 0.2.0（ドラフト）
**作成日:** 2026-05-17
**更新日:** 2026-05-17
**ステータス:** アイデア検討中

---

## 1. 概要

### 1.1 背景

現行バトルエンジン（`dynamic-combat-system.md` Phase A〜D 実装済み）では、ニアリアルタイムシミュレーション・ファジィ推論・ポテンシャルフィールドによる自律行動が実現されているが、以下の構造的バランス問題が残っている。

### 1.2 問題の全体像

| 問題カテゴリ | 症状 | 根本原因 |
|---|---|---|
| 装甲支配 | 高装甲MSへのダメージがほぼ 0 になる | 減算式 `weapon.power - target.armor` がゼロに張り付く |
| カスタム価値低下 | 装甲以外のパラメータを上げても戦果が変わらない | 装甲が防御のほぼ唯一の実効指標になっている |
| 強MSの無リスク化 | 強いMSが有利に戦い続けられる | 「強い = 集中攻撃を受ける」戦略的コストがない |
| パイロット能力の希薄さ | パイロットのレベルアップが実感されない | 既存のパイロットステータス（DEX/INT 等）が NPC 戦闘に未適用 |

---

## 2. 問題の根本原因分析

### 2.1 装甲支配の原因

現在のダメージ計算式（`combat.py:664`）:

```python
base_damage = max(1, weapon.power - target.armor)
```

これは**純粋な減算**であるため、`target.armor >= weapon.power - 1` を満たすと実質ダメージが 1 に固定される。高装甲 MS は「ほぼ無敵」状態になり、他のパラメータ（回避率・機動性・射撃適性）の差異がバランスに影響しなくなる。

**数値例（weapon.power = 150 の場合）:**

| armor 値 | ダメージ | 与ダメ割合 |
|---|---|---|
| 50 | 100 | 67% |
| 100 | 50 | 33% |
| 140 | 10 | 7% |
| 149 | 1 | 0.7% |
| 200 | 1（下限） | 0.7% |

### 2.2 パイロット能力の未反映

`calculator.py` に `PilotStats`（DEX/INT/REF/TOU/LUK）が定義されているが、`combat.py` の適用ロジック（`_calculate_hit_chance`, `_process_hit`）は **`actor.side == "PLAYER"` の場合にのみ** ステータスを参照している。

```python
# combat.py 190〜191行
attacker_dex = self.player_pilot_stats.dex if actor.side == "PLAYER" else 0
defender_int = self.player_pilot_stats.intel if target.side == "PLAYER" else 0
```

NPC/Enemy 側のパイロット能力は常に 0 扱いとなるため、NPC 同士の戦闘ではパイロット差が生まれない。

また、現行の `DEX`（器用）は射撃・格闘のどちらにも効く汎用ステータスとして定義されているが、これを **射撃系と格闘系に分離**（→ 3.1・3.5 で詳述）することで、パイロットの専門性（射撃巧者 vs 格闘巧者）がゲームに反映されるようになる。

---

## 3. 改善方針

### 3.1 ダメージ計算式の改善：シグモイドによる攻撃・防御補正

#### 課題

減算式 `max(1, weapon.power - target.armor)` はダメージが線形に減り、高装甲 MS でゼロに張り付く。またパイロット能力と MS 性能を統合した攻撃・防御の評価が存在しない。

#### 改善案：シグモイド式ダメージ計算

$$
\text{最終ダメージ} = \text{武器の攻撃力} \times (1 + \text{攻撃力補正率}) \times (1 - \text{防御軽減率})
$$

**ダメージレンジの設計方針:**

- 攻撃力補正率の上限を **50%** に設定し、最大ダメージを `weapon.power × 1.5` 以内（2 倍上限の設計余裕）に収める
- 防御軽減率の上限を **50%** に設定し、どんな高装甲でも必ず 50% のダメージが通る

| 条件 | 最終倍率 |
|---|---|
| 攻撃補正なし・防御軽減なし（基準値） | ×1.00 |
| 攻撃最大・防御なし | ×1.50（上限） |
| 攻撃なし・防御最大 | ×0.50（下限） |
| 最大攻撃 vs 最大防御 | ×0.75 |

---

#### 攻撃力補正率（シグモイド）

$$
\text{攻撃力補正率} = \frac{MAX\_ATTACK\_BONUS}{1 + e^{-k_{\text{atk}} \times (\text{合計攻撃力} - \text{midpoint}_{\text{atk}})}}
$$

| パラメータ | 値 | 説明 |
|---|---|---|
| `MAX_ATTACK_BONUS` | `0.50`（50%） | 補正率の上限。最大ダメージを `weapon.power × 1.5` に抑える |
| `k_atk` | バランス検証ツールで調整 | シグモイドの傾き。小さいほど緩やか、大きいほど急峻 |
| `midpoint_atk` | バランス検証ツールで調整 | 補正率が 25%（MAX の半分）になる合計攻撃力値 |

**合計攻撃力の定義（武器種別により参照スタットが異なる）:**

| 武器種別 | 合計攻撃力 |
|---|---|
| 射撃武器 | `MS射撃適性スコア + パイロット射撃精度 (SHT)` |
| 格闘武器 | `MS格闘適性スコア + パイロット格闘技巧 (MEL)` |

> **SHT / MEL について:** 現行の `DEX`（器用）を射撃系・格闘系に分離した新ステータス。詳細は 3.5 を参照。

---

#### 防御軽減率（シグモイド）

$$
\text{防御軽減率} = \frac{MAX\_DEFENSE\_REDUCTION}{1 + e^{-k_{\text{def}} \times (\text{合計防御力} - \text{midpoint}_{\text{def}})}}
$$

| パラメータ | 値 | 説明 |
|---|---|---|
| `MAX_DEFENSE_REDUCTION` | `0.50`（50%） | 軽減率の上限。最大でも 50% のダメージが必ず通る |
| `k_def` | バランス検証ツールで調整 | シグモイドの傾き |
| `midpoint_def` | バランス検証ツールで調整 | 軽減率が 25%（MAX の半分）になる合計防御力値 |

**合計防御力の定義:**

$$
\text{合計防御力} = \text{MS装甲} + \text{パイロット耐久 (TOU)}
$$

> **midpoint_def の設定指針:** 防御軽減率が 25% になる点を合計防御力の中央値と設定する。既存 MS データの `armor` 分布の中央値を確認して決定する（→ バランス検証ツールで可視化）。

---

#### 数値例（weapon.power = 150、各パラメータ midpoint に設定）

合計攻撃力が midpoint のとき攻撃力補正率 = 25%、合計防御力が midpoint のとき防御軽減率 = 25% とした場合。

| 合計攻撃力 | 攻撃力補正率 | 合計防御力 | 防御軽減率 | 最終ダメージ |
|---|---|---|---|---|
| 0（最低） | 0% | 0（最低） | 0% | 150（×1.00） |
| 0（最低） | 0% | midpoint | 25% | 113（×0.75） |
| 0（最低） | 0% | MAX | 50% | 75（×0.50） |
| midpoint | 25% | 0（最低） | 0% | 188（×1.25） |
| midpoint | 25% | midpoint | 25% | 141（×0.94） |
| MAX | 50% | 0（最低） | 0% | 225（×1.50） |
| MAX | 50% | MAX | 50% | 113（×0.75） |

---

#### 互換性・例外

| ケース | 扱い |
|---|---|
| クリティカルヒット | 防御軽減率を無視（装甲貫通）。現行仕様を維持 |
| MELEE 武器 | ビーム耐性・実弾耐性を無視する現行仕様を維持。防御軽減率（TOU 由来分）は引き続き適用 |
| 防御軽減率 = 0 の場合 | 従来の `weapon.power × aptitude` と同等のダメージ（ステータス未設定 NPC での後方互換） |

---

#### シグモイド係数のキャッシュ（パフォーマンス）

シグモイド計算（`exp()` 呼び出し）はステータスが戦闘中に変わらないため、**シミュレーション開始時に全ユニット分を一括計算してキャッシュ**する。攻撃判定ごとの `exp()` 呼び出しをゼロにする。

```python
# BattleSimulator.__init__() または _initialize_resources() で実行
def _build_combat_multiplier_cache(self) -> None:
    """全ユニットの攻撃・防御補正率を事前計算して unit_resources にキャッシュする."""
    for unit in self.units:
        uid = str(unit.id)
        pilot = self.unit_pilot_stats.get(uid, PilotStats())

        # 射撃攻撃補正率
        ranged_atk = _shooting_aptitude_score(unit) + pilot.sht
        # 格闘攻撃補正率
        melee_atk = _melee_aptitude_score(unit) + pilot.mel
        # 防御軽減率
        total_def = unit.armor + pilot.tou

        self.unit_resources[uid]["cached_ranged_attack_bonus"] = _sigmoid_attack(ranged_atk)
        self.unit_resources[uid]["cached_melee_attack_bonus"]  = _sigmoid_attack(melee_atk)
        self.unit_resources[uid]["cached_defense_reduction"]   = _sigmoid_defense(total_def)
```

**攻撃判定時の参照（`_calculate_hit_base_damage` 内）:**

```python
resources_actor = self.unit_resources[str(actor.id)]
is_melee = getattr(weapon, "weapon_type", "RANGED") == "MELEE"
attack_bonus = (
    resources_actor["cached_melee_attack_bonus"]
    if is_melee
    else resources_actor["cached_ranged_attack_bonus"]
)
resources_target = self.unit_resources[str(target.id)]
defense_reduction = resources_target["cached_defense_reduction"]

base_damage = int(weapon.power * (1.0 + attack_bonus) * (1.0 - defense_reduction))
```

#### 新定数（`constants.py`）

```python
# ダメージ計算シグモイド定数 (Phase E-1)
# k・midpoint は balance-cli-tools で検証後に設定する
MAX_ATTACK_BONUS: float = 0.50       # 攻撃力補正率の上限（50%）
MAX_DEFENSE_REDUCTION: float = 0.50  # 防御軽減率の上限（50%）

# 初期値（要チューニング）
ATTACK_SIGMOID_K: float = 0.05       # 攻撃シグモイドの傾き
ATTACK_SIGMOID_MIDPOINT: float = 50.0  # 攻撃補正率が MAX/2 になる合計攻撃力
DEFENSE_SIGMOID_K: float = 0.05      # 防御シグモイドの傾き
DEFENSE_SIGMOID_MIDPOINT: float = 100.0  # 防御軽減率が MAX/2 になる合計防御力
```

---

### 3.2 パイロットビジー状態（複数攻撃によるペナルティ）

#### 概要

同一ターン（タイムウィンドウ内）に複数のユニットから攻撃を受けた MS のパイロットが「ビジー状態」に陥り、回避率・防御力が低下する。

「強い MS ほど集中攻撃を受けやすい」（後述 3.3 参照）と組み合わせることで、強 MS にリスクが生まれる。

#### 被攻撃カウント管理

```python
# unit_resources に追加（DB 非保存）
"attackers_this_window": set[str]   # 今タイムウィンドウ内に攻撃してきた unit_id の集合
"pilot_busy_level": int             # ビジー段階 (0: 平常 / 1: 軽度 / 2: 中度 / 3: 重度)
"busy_window_elapsed": float        # 現ウィンドウの経過時間（s）
```

**タイムウィンドウ:** `BUSY_WINDOW_SEC = 2.0` s（要チューニング）。各ステップ `busy_window_elapsed` をインクリメントし、ウィンドウ終了時に `attackers_this_window` をリセット。

#### ビジーレベル判定

| 攻撃者数（ウィンドウ内） | pilot_busy_level | 説明 |
|---|---|---|
| 0〜1 | 0 | 平常 |
| 2 | 1 | 軽度ビジー |
| 3 | 2 | 中度ビジー |
| 4以上 | 3 | 重度ビジー（パニック状態） |

#### ビジー状態のペナルティ

| ビジーレベル | 回避率補正 | 受けダメージ補正 | 反撃優先（ターゲット選択ファジィ） |
|---|---|---|---|
| 0 | ×1.0 | ×1.0 | 通常 |
| 1 | ×0.85 | ×1.10 | わずかに反撃優先 |
| 2 | ×0.65 | ×1.25 | 強く反撃優先 |
| 3 | ×0.40 | ×1.50 | 最優先で反撃 |

**回避率補正の適用箇所（`_calculate_hit_chance` に追加）:**

```python
# 被攻撃側のビジー状態を考慮
busy_level = self.unit_resources[str(target.id)].get("pilot_busy_level", 0)
busy_evasion_multiplier = BUSY_EVASION_MULTIPLIERS[busy_level]  # [1.0, 0.85, 0.65, 0.40]
evasion_bonus = target.mobility * 10 * busy_evasion_multiplier
```

**ダメージ補正の適用箇所（`_process_hit` に追加）:**

```python
busy_damage_multiplier = BUSY_DAMAGE_MULTIPLIERS[busy_level]  # [1.0, 1.10, 1.25, 1.50]
base_damage = int(base_damage * busy_damage_multiplier)
```

#### ビジー状態によるターゲット選択変更

ビジー時はファジィ推論の `target_priority` 計算に「現在自分を攻撃している敵」への優先度ボーナスを付与する。

**ファジィ変数追加（target_selection 層）:**

| 変数名 | 範囲 | ファジィ集合 | 説明 |
|---|---|---|---|
| `is_current_attacker` | 0.0 or 1.0 | FALSE / TRUE | ターゲットが現在自分を攻撃しているか |
| `self_busy_level` | 0〜3 | CALM / MILD / MODERATE / SEVERE | 自機のビジーレベル |

**ルール追加例（全戦略モード共通）:**

```json
{
  "conditions": [
    { "variable": "is_current_attacker", "set": "TRUE" },
    { "variable": "self_busy_level", "set": "SEVERE" }
  ],
  "output": { "variable": "target_priority", "set": "HIGH" }
}
```

#### 新定数（`constants.py`）

```python
BUSY_WINDOW_SEC: float = 2.0
BUSY_EVASION_MULTIPLIERS: list[float] = [1.0, 0.85, 0.65, 0.40]
BUSY_DAMAGE_MULTIPLIERS: list[float]  = [1.0, 1.10, 1.25, 1.50]
```

---

### 3.3 戦略価値スコアによる集中攻撃（ファジィ推論拡張）

#### 概要

「強い MS = 戦略価値が高い = 複数ユニットに狙われる」というゲームループを実現するため、ターゲット選択ファジィにおける優先度計算に **MS の戦略価値スコア** を新たな入力変数として導入する。

#### 戦略価値スコア（Strategic Value Score）の定義

戦略価値は以下の要素から算出する複合スコア（0.0〜1.0）。

| 要素 | 重み | 計算方法 |
|---|---|---|
| 攻撃力 | 40% | `max(weapon.power for w in target.weapons) / MAX_WEAPON_POWER` |
| HP残量 | 20% | `target.current_hp / target.max_hp`（高 HP = 脅威が継続） |
| 装甲 | 20% | `target.armor / MAX_ARMOR`（装甲が高い = 将来の脅威度大） |
| 機動性 | 10% | `target.max_speed / MAX_SPEED`（高機動 = 回避が難しい） |
| エース判定 | 10% | `1.0 if target.is_ace else 0.0` |

```python
def calculate_strategic_value(target: MobileSuit) -> float:
    """ターゲットの戦略価値スコアを 0.0〜1.0 で返す."""
    atk_score  = min(1.0, max_weapon_power(target) / STRATEGIC_VALUE_MAX_WEAPON_POWER)
    hp_score   = target.current_hp / max(1, target.max_hp)
    armor_score = min(1.0, target.armor / STRATEGIC_VALUE_MAX_ARMOR)
    speed_score = min(1.0, target.max_speed / STRATEGIC_VALUE_MAX_SPEED)
    ace_score   = 1.0 if target.is_ace else 0.0

    return (
        atk_score   * 0.40
        + hp_score  * 0.20
        + armor_score * 0.20
        + speed_score * 0.10
        + ace_score   * 0.10
    )
```

#### ターゲット選択ファジィへの追加

**新ファジィ変数（target_selection 層）:**

| 変数名 | 範囲 | ファジィ集合 | 説明 |
|---|---|---|---|
| `target_strategic_value` | 0.0〜1.0 | LOW / MEDIUM / HIGH | ターゲットの戦略価値スコア |

**ルール追加例（AGGRESSIVE モード）:**

```json
{
  "conditions": [
    { "variable": "target_strategic_value", "set": "HIGH" },
    { "variable": "target_distance", "set": "CLOSE" }
  ],
  "output": { "variable": "target_priority", "set": "HIGH" }
}
```

**ルール追加例（DEFENSIVE モード — 脅威排除）:**

```json
{
  "conditions": [
    { "variable": "target_strategic_value", "set": "HIGH" },
    { "variable": "is_attacking_ally", "set": "TRUE" }
  ],
  "output": { "variable": "target_priority", "set": "HIGH" }
}
```

> **設計意図:** 戦略価値の高い MS（強い機体）が単純に「倒しやすい相手（HP低い・距離近い）」よりも優先されるシナリオを意図的に作る。結果として、強 MS は複数から狙われやすくなり、ビジー状態（3.2）と連動してリスクが生まれる。

#### 新定数（`constants.py`）

```python
STRATEGIC_VALUE_MAX_WEAPON_POWER: float = 500.0
STRATEGIC_VALUE_MAX_ARMOR: float = 300.0
STRATEGIC_VALUE_MAX_SPEED: float = 300.0
```

---

### 3.4 攻撃角度による命中率・ダメージ補正

#### 概要

現在は「ターゲットとの距離」だけが命中率に影響するが、「どの方向から攻撃するか」も現実の戦闘では極めて重要。後ろから攻撃すれば命中しやすく、防御が薄い背面を狙えばダメージも増大する。

この仕組みを実装することで「背後を取る戦術」の価値が生まれ、将来的な「背後を取られないための立ち回り」の基盤になる。

#### 角度セクタの定義

攻撃者とターゲットの相対角度（ターゲットの `heading_deg` を基準）でセクタを判定する。

```
前方   (FRONT):    |angle_diff| <= 60°
側面前 (FRONT_SIDE): 60° < |angle_diff| <= 120°
側面後 (REAR_SIDE): 120° < |angle_diff| <= 150°
後方   (REAR):     150° < |angle_diff| <= 180°
```

**角度差の計算方法:**

```python
def calculate_attack_sector(
    attacker_pos: np.ndarray,
    target_pos: np.ndarray,
    target_heading_deg: float,
) -> str:
    """攻撃者がターゲットのどのセクタから攻撃しているかを返す."""
    dx = attacker_pos[0] - target_pos[0]
    dz = attacker_pos[2] - target_pos[2]
    attack_dir_deg = math.degrees(math.atan2(dz, dx))

    # ターゲットの正面方向との角度差（絶対値）
    raw_diff = attack_dir_deg - target_heading_deg
    angle_diff = abs(((raw_diff + 180) % 360) - 180)

    if angle_diff <= 60:
        return "FRONT"
    elif angle_diff <= 120:
        return "FRONT_SIDE"
    elif angle_diff <= 150:
        return "REAR_SIDE"
    else:
        return "REAR"
```

#### セクタ別の補正値

| セクタ | 命中率補正（乗算） | ダメージ補正（乗算） | 設計意図 |
|---|---|---|---|
| FRONT | ×0.85 | ×0.90 | 正面は防御が固く、素直に回避もしやすい |
| FRONT_SIDE | ×1.00 | ×1.00 | 基準値（補正なし） |
| REAR_SIDE | ×1.15 | ×1.15 | 視野外から接近しており回避困難・防御が薄い |
| REAR | ×1.35 | ×1.30 | 完全に背後を取られた状態（最大ペナルティ） |

**適用箇所（`_calculate_hit_chance` 最後尾に追加）:**

```python
target_heading = self.unit_resources[str(target.id)].get("heading_deg", 0.0)
attack_sector = calculate_attack_sector(pos_actor, target.position.to_numpy(), target_heading)
sector_accuracy_modifier = SECTOR_ACCURACY_MODIFIERS[attack_sector]
hit_chance = hit_chance * sector_accuracy_modifier
```

**適用箇所（`_calculate_hit_base_damage` にセクタ引数を追加）:**

```python
sector_damage_modifier = SECTOR_DAMAGE_MODIFIERS[attack_sector]
base_damage = int(base_damage * sector_damage_modifier)
```

#### BattleLog への記録

```python
# BattleLog に追加フィールド
attack_sector: str | None = None  # "FRONT" / "FRONT_SIDE" / "REAR_SIDE" / "REAR"
```

#### 新定数（`constants.py`）

```python
SECTOR_ACCURACY_MODIFIERS: dict[str, float] = {
    "FRONT":      0.85,
    "FRONT_SIDE": 1.00,
    "REAR_SIDE":  1.15,
    "REAR":       1.35,
}
SECTOR_DAMAGE_MODIFIERS: dict[str, float] = {
    "FRONT":      0.90,
    "FRONT_SIDE": 1.00,
    "REAR_SIDE":  1.15,
    "REAR":       1.30,
}
SECTOR_FRONT_DEG:      float = 60.0
SECTOR_FRONT_SIDE_DEG: float = 120.0
SECTOR_REAR_SIDE_DEG:  float = 150.0
```

---

### 3.5 パイロット能力の全ユニット適用・スタット再定義

#### 3.5.1 概要

現在パイロットステータス（`PilotStats`）の戦闘補正は Player 側のみに適用されているが、NPC 側にも適用することでパイロットの個性と成長の実感を全ユニットに広げる。

あわせて、汎用的すぎる `DEX`（器用）を **射撃精度（SHT）** と **格闘技巧（MEL）** に分離する。これにより「射撃巧者」「格闘のスペシャリスト」というパイロット専門性がゲームに反映される。

#### 3.5.2 パイロットスタットの再定義

| 旧スタット | 新スタット | フィールド名 | 主な役割 |
|---|---|---|---|
| `DEX`（器用） | **射撃精度（SHT）** | `sht` | 射撃武器の攻撃力補正率シグモイド入力・命中率 |
| `DEX`（器用） | **格闘技巧（MEL）** | `mel` | 格闘武器の攻撃力補正率シグモイド入力・命中率 |
| `INT`（直感） | 直感（INT） | `intel` | クリティカル率・回避率（変更なし） |
| `REF`（反応） | 反応（REF） | `ref` | イニシアチブ・機動性乗算（変更なし） |
| `TOU`（耐久） | 耐久（TOU） | `tou` | 防御軽減率シグモイド入力・被クリ率低下（変更なし） |
| `LUK`（幸運） | 幸運（LUK） | `luk` | ダメージ乱数偏り・完全回避（変更なし） |

> **DEX の扱い:** 現行の `DEX` が持つ「距離減衰緩和」効果は `SHT` に引き継ぎ、「被ダメージカット」は `TOU` に統合する（旧 `DEX` フィールドは非推奨化）。

**`PilotStats` データクラスの変更（`calculator.py`）:**

```python
@dataclass
class PilotStats:
    sht:   int = field(default=0)  # 射撃精度 (SHT) — 射撃攻撃補正・命中
    mel:   int = field(default=0)  # 格闘技巧 (MEL) — 格闘攻撃補正・命中
    intel: int = field(default=0)  # 直感   (INT) — クリティカル率・回避率
    ref:   int = field(default=0)  # 反応   (REF) — イニシアチブ・機動性乗算
    tou:   int = field(default=0)  # 耐久   (TOU) — 防御補正・被クリ率低下
    luk:   int = field(default=0)  # 幸運   (LUK) — 乱数偏り・完全回避
```

**`Pilot` モデルへの追加フィールド（`models.py`）:**

```python
sht: int = Field(default=0, description="射撃精度 (SHT) - 射撃攻撃力補正・命中率")
mel: int = Field(default=0, description="格闘技巧 (MEL) - 格闘攻撃力補正・命中率")
```

#### 3.5.3 `PilotStats` の参照元

| ユニット種別 | 参照元 |
|---|---|
| Player | `self.player_pilot_stats`（既存。`sht`/`mel` を追加） |
| NPC（エース） | `Pilot` テーブルの全スタットフィールド |
| NPC（通常） | `personality` に基づくデフォルト値（下表） |

**パーソナリティ別デフォルト `PilotStats`:**

| `personality` | SHT | MEL | INT | REF | TOU | LUK | 特性 |
|---|---|---|---|---|---|---|---|
| `AGGRESSIVE` | 3 | 4 | 2 | 4 | 3 | 1 | 近距離格闘重視・速い判断 |
| `CAUTIOUS` | 3 | 1 | 4 | 2 | 2 | 3 | 中距離射撃・高回避・クリ狙い |
| `SNIPER` | 6 | 1 | 3 | 1 | 1 | 2 | 射撃精度特化・距離減衰緩和 |
| `None`（デフォルト） | 1 | 1 | 1 | 1 | 1 | 1 | 均等な素人パイロット |

**エースパイロット（`is_ace = True`）:** `Pilot` テーブルの実際のスタット値を使用。各スタット 5〜15 程度で通常 NPC との明確な差別化が生まれる。

#### 3.5.4 適用箇所の変更

`BattleSimulator` に全ユニット分の `PilotStats` を保持するテーブルを追加する。

```python
# unit_pilot_stats: {unit_id: PilotStats}
self.unit_pilot_stats: dict[str, PilotStats] = {}
```

`combat.py` のパイロットステータス参照を汎用化する：

```python
# 変更前（Player 専用）
attacker_dex = self.player_pilot_stats.dex if actor.side == "PLAYER" else 0

# 変更後（全ユニット対応）
attacker_stats = self.unit_pilot_stats.get(str(actor.id), PilotStats())
attacker_sht = attacker_stats.sht  # 射撃武器時
attacker_mel = attacker_stats.mel  # 格闘武器時
```

---

## 4. 各改善案の相互作用と設計意図

```
強い MS（高装甲・高火力・エース）
    ↓
戦略価値スコア [3.3] が高い
    ↓
複数のユニットからターゲット優先度 HIGH で狙われる
    ↓
ビジー状態 [3.2] が発生（複数攻撃）
    ↓
回避率低下・受けダメージ増加
    ↓
装甲が高くても防御軽減率上限 50% [3.1] でじわじわ削られる
    ↓
戦略的コスト（強 MS は集中砲火を引き付ける義務がある）
```

加えて攻撃角度 [3.4] とパイロット能力 [3.5] が組み合わさることで、同じ MS でも「パイロットの腕と機体の位取り」によって結果が変わる戦術的な深みが生まれる。

---

## 5. 未検討事項・ブラッシュアップが必要な箇所

以下は今後の議論・チューニングが必要な項目。

### 5.1 シグモイド係数のチューニング

シグモイドの傾き `k` と中央値 `midpoint` は `balance-cli-tools.md` のバランス検証ツールで可視化しながら調整する前提であり、コード上は `constants.py` の定数として管理する。

チューニング時に確認すべき観点：

- **midpoint の基準点:** 既存 MS データの `armor` 分布の中央値（P50）を `midpoint_def` の初期値として採用する
- **k の感度確認:** `k` が大きすぎるとステータス差が極端に出る。ステータス ±10 でのダメージ変化をグラフで確認する
- **クリティカルとの整合:** クリティカルヒットは防御軽減率を無視（装甲貫通）するため、クリティカル率を調整する際はシグモイドの影響を除外して評価する

### 5.2 ビジー状態のウィンドウ設計

- `BUSY_WINDOW_SEC = 2.0` は `dt = 0.1s` の 20 ステップ分。瞬間的な集中砲火と持続的な多面攻撃を区別する設計が必要
- ウィンドウのリセットタイミング（固定長 vs スライディングウィンドウ）

### 5.3 戦略価値スコアのバランス

- 「常に高装甲 MS = 高戦略価値」になると、低装甲 MS の存在意義が薄れる可能性がある
  - 状況依存の重み付け（近接戦では速度重視、遠距離戦では攻撃力重視 など）を検討
- StrategyMode ごとに重みを変えることも可能（JSONで外部化済みのファジィルールを活用）

### 5.4 攻撃角度の活用と AI 行動拡張

- 「後方を取る」ために積極的に回り込む AI 行動の追加は別 Issue として分離を推奨
  - ポテンシャルフィールドへの「側面・後方方向への引力」追加
  - ファジィルールに `target_sector` 変数を追加してフランキング行動を誘発
- 将来: 「背後を取られない立ち回り」（後方への斥力、振り向き優先行動）

### 5.5 パイロット能力のバランス

- エース以外の NPC パイロット能力をどこで定義・管理するか（`MobileSuit.personality` での一括設定 vs 個別 Pilot エンティティ）
- `SHT` / `MEL` が攻撃力補正に入る一方、命中率への影響も残る場合は二重に効くため、役割分担を明確にする
- パイロット能力の影響力が強すぎると MS のパラメータ差が薄れる懸念（→ シグモイド k で調整可能）

### 5.6 パフォーマンス影響

- 毎ステップ全ユニットの `attackers_this_window` を更新する処理コスト
- `calculate_strategic_value()` のキャッシュ戦略（ターゲット選択時に毎回計算 vs ステップ開始時に一括計算）

---

## 6. 実装ロードマップ（案）

| フェーズ | 内容 | 優先度 | 依存 |
|---|---|---|---|
| **Phase E-1** | シグモイドダメージ計算式の実装・キャッシュ [3.1] | 高 | なし |
| **Phase E-2** | `SHT`/`MEL` スタット追加・パイロット能力の全ユニット適用 [3.5] | 高 | E-1 |
| **Phase E-3** | 攻撃角度によるセクタ補正 [3.4] | 中 | heading_deg（既実装） |
| **Phase E-4** | ビジー状態システム [3.2] | 中 | E-3（ターゲット選択変更） |
| **Phase E-5** | 戦略価値スコアのターゲット選択統合 [3.3] | 中 | E-4 |
| **Phase E-6** | 各種チューニング・バランス検証 | 高 | E-1〜E-5 |

---

## 7. 関連ドキュメント

- [battle-engine-feature.md](./battle-engine-feature.md) — コアエンジン仕様
- [dynamic-combat-system.md](./dynamic-combat-system.md) — 近接戦闘・LOS・ブーストシステム
- [fuzzy-engine.md](./fuzzy-engine.md) — ファジィ推論エンジン
- [balance-cli-tools.md](./balance-cli-tools.md) — バランス調整 CLI ツール
