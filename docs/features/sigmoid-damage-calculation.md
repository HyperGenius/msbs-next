# シグモイドダメージ計算式 仕様書

**フェーズ:** Phase E-1  
**ステータス:** 実装済み  
**作成日:** 2026-05-17  
**対象ファイル:** `backend/app/engine/combat.py`, `backend/app/engine/constants.py`, `backend/app/engine/calculator.py`, `backend/app/engine/simulation.py`

---

## 1. 概要

### 1.1 背景・解決した問題

旧計算式（`max(1, weapon.power - target.armor)`）は純粋な減算だったため、高装甲 MS に対して
ダメージがほぼ 0 に張り付く「装甲支配」問題があった。

| armor 値（weapon.power=150 の場合） | 旧ダメージ | 旧与ダメ割合 |
|---|---|---|
| 50 | 100 | 67% |
| 100 | 50 | 33% |
| 140 | 10 | 7% |
| 149 | 1 | 0.7% |
| 200 | 1（下限） | 0.7% |

### 1.2 解決策

シグモイド関数を用いた攻撃・防御補正率を導入し、以下を実現する：

- **攻撃補正率の上限 50%**：最大ダメージを `weapon.power × 1.5` 以内に収める
- **防御軽減率の上限 50%**：どんな高装甲でも必ず 50% のダメージが通る
- **パイロット能力 (SHT/MEL/TOU) の統合**：パイロットの専門性がダメージに反映される

---

## 2. 計算式

### 2.1 最終ダメージ（非クリティカル）

```
最終ダメージ = max(1, int(weapon.power × (1 + 攻撃力補正率) × (1 - 防御軽減率)))
```

| 条件 | 最終倍率 |
|---|---|
| 攻撃補正なし・防御軽減なし | ×1.00（ベースライン） |
| 攻撃最大（SHT=∞）・防御なし | ×1.50（上限） |
| 攻撃なし・防御最大（armor=∞） | ×0.50（下限） |
| 最大攻撃 vs 最大防御 | ×0.75 |

### 2.2 攻撃力補正率（シグモイド）

```
攻撃力補正率 = MAX_ATTACK_BONUS / (1 + exp(-k_atk × (合計攻撃力 - midpoint_atk)))
```

| 武器種別 | 合計攻撃力 |
|---|---|
| 射撃武器 | `_shooting_aptitude_score(MS) + pilot.sht` |
| 格闘武器 | `_melee_aptitude_score(MS) + pilot.mel` |

> **Phase E-1 注記:** `_shooting_aptitude_score` / `_melee_aptitude_score` は現在 `0.0` を返す
> スタブ実装（MS 適性の二重カウント防止）。Phase E-2 で正式実装予定。
> 現フェーズでは `pilot.sht` / `pilot.mel` のみがシグモイド入力に寄与する。

### 2.3 防御軽減率（シグモイド）

```
防御軽減率 = MAX_DEFENSE_REDUCTION / (1 + exp(-k_def × (合計防御力 - midpoint_def)))
```

```
合計防御力 = MS装甲(armor) + パイロット耐久(TOU)
```

---

## 3. 定数（`constants.py`）

```python
# ダメージ計算シグモイド定数 (Phase E-1)
MAX_ATTACK_BONUS: float = 0.50          # 攻撃力補正率の上限（50%）
MAX_DEFENSE_REDUCTION: float = 0.50    # 防御軽減率の上限（50%）
ATTACK_SIGMOID_K: float = 0.05         # 攻撃シグモイドの傾き（初期値）
ATTACK_SIGMOID_MIDPOINT: float = 50.0  # 攻撃補正率が MAX/2 になる合計攻撃力値（初期値）
DEFENSE_SIGMOID_K: float = 0.05        # 防御シグモイドの傾き（初期値）
DEFENSE_SIGMOID_MIDPOINT: float = 100.0  # 防御軽減率が MAX/2 になる合計防御力値（初期値）
```

> `k` および `midpoint` は `balance-cli-tools` でチューニングすること。

---

## 4. 数値例（weapon.power = 150）

### 4.1 pilot.sht = pilot.mel = pilot.tou = 0（NPC デフォルト）

| armor 値 | 防御軽減率 | 攻撃補正率 | 新ダメージ | 旧ダメージ |
|---|---|---|---|---|
| 0 | ≈0.3% | ≈3.8% | ≈155 | 150 |
| 50 | ≈6.0% | ≈3.8% | ≈145 | 100 |
| 100 | 25.0% | ≈3.8% | ≈120 | 50 |
| 150 | ≈40.0% | ≈3.8% | ≈95 | 1 |
| 200 | ≈47.0% | ≈3.8% | ≈84 | 1（下限） |

### 4.2 pilot.sht = 50 のプレイヤー vs armor = 100 の敵

| SHT | 攻撃補正率 | 防御軽減率 | 最終倍率 | ダメージ |
|---|---|---|---|---|
| 0 | ≈3.8% | 25.0% | ×0.783 | ≈117 |
| 50 | 25.0% | 25.0% | ×0.938 | ≈141 |
| 80 | ≈40.0% | 25.0% | ×1.05 | ≈157 |

---

## 5. パフォーマンス：キャッシュ戦略

シグモイド計算（`math.exp()` 呼び出し）はパイロット・MS のステータスが戦闘中に変化しないため、
**シミュレーション開始時に全ユニット分を一括計算してキャッシュ**する。

`BattleSimulator.__init__()` の最後に `_build_combat_multiplier_cache()` を呼び出す。

キャッシュされるキー（`unit_resources[unit_id]` に格納）：

| キー | 型 | 説明 |
|---|---|---|
| `cached_ranged_attack_bonus` | `float` | 射撃攻撃補正率（0.0〜0.50） |
| `cached_melee_attack_bonus` | `float` | 格闘攻撃補正率（0.0〜0.50） |
| `cached_defense_reduction` | `float` | 防御軽減率（0.0〜0.50） |

---

## 6. 互換性・例外処理

| ケース | 扱い |
|---|---|
| クリティカルヒット | 防御軽減率を無視（`weapon.power × 1.2`）。現行仕様維持 |
| MELEE 武器 | ビーム耐性・実弾耐性を無視する現行仕様を維持。防御軽減率は適用される |
| armor=0 かつ tou=0（NPC） | 防御軽減率 ≈ 0.3%（ほぼ影響なし）。旧式の `weapon.power × aptitude` と近似 |
| キャッシュ未設定ユニット | `resources.get("cached_*", 0.0)` でデフォルト 0.0 にフォールバック（安全） |

---

## 7. 新追加 PilotStats フィールド（`calculator.py`）

`PilotStats` に以下のフィールドを追加した：

| フィールド | 型 | デフォルト | 説明 |
|---|---|---|---|
| `sht` | `int` | `0` | 射撃精度 (SHT) - 射撃攻撃力補正率のシグモイド入力値 |
| `mel` | `int` | `0` | 格闘技巧 (MEL) - 格闘攻撃力補正率のシグモイド入力値 |

---

## 8. 実装変更一覧

| ファイル | 変更内容 |
|---|---|
| `alembic/versions/t3u4v5w6x7y8_add_sht_mel_drop_dex.py` | DB マイグレーション: `sht`/`mel` 追加、既存 `dex` 値をコピー後に `dex` 削除 |
| `app/models/models.py` | `Pilot` モデルから `dex` 削除、`sht`/`mel` 追加 |
| `constants.py` | シグモイド定数 6 件を追加 |
| `calculator.py` | `PilotStats` から `dex` 削除、`sht`/`mel` フィールドに更新 |
| `combat.py` | `_sigmoid_attack()`, `_sigmoid_defense()`, `_shooting_aptitude_score()`, `_melee_aptitude_score()` を module-level 関数として追加。`CombatMixin._build_combat_multiplier_cache()` を追加。`_calculate_hit_base_damage()` を新計算式に更新 |
| `simulation.py` | `unit_pilot_stats` 辞書の初期化、`_build_combat_multiplier_cache()` 呼び出しを `__init__` 末尾に追加 |
| `main.py` | `PilotStats` 構築を `sht`/`mel` に更新 |
| `app/routers/pilots.py` | `bonus_dex` → `bonus_sht`/`bonus_mel`、`StatusAllocateRequest` 更新 |
| `app/services/pilot_service.py` | `allocate_status_points` の引数・ロジックを `sht`/`mel` に更新 |
| `frontend/src/types/pilot.ts` | `dex` 削除、`sht`/`mel` 追加 |
| `frontend/src/components/pilot/ParameterTuningPanel.tsx` | SHT/MEL の表示・割り振り UI に更新 |
| `frontend/src/data/backgrounds.json` | `DEX` → `SHT`/`MEL`（値はコピー） |

---

## 9. 後続フェーズとの関係

| フェーズ | 依存関係 | 内容 |
|---|---|---|
| **Phase E-1（本実装）** | 独立 | シグモイド計算式・SHT/MEL/TOU の統合 |
| Phase E-2 (#3.5) | E-1 に依存 | `_shooting_aptitude_score` / `_melee_aptitude_score` を本格実装し、SHT/MEL を全ユニットに適用 |
| Phase E-3 | E-2 に依存 | `balance-cli-tools` で k・midpoint のチューニング |
