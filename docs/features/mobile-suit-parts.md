# 命中後の部位判定レイヤーと部位別HP/装甲データモデル（Issue #503）

## 概要

#501（部位別フィードバック導入）の Phase 2。命中判定（`_calculate_hit_chance()`）が成功した後に「どの部位に命中したか」を決定するレイヤーを新設し、部位別のHP/装甲データモデルを追加した。

**本フェーズの部位選択ロジックは暫定実装（簡易ロジック）である。** 戦術設定・角度・距離に基づく本格的な確率算出は Phase 4（#TBD）で `determine_hit_part()` ごと置き換える前提。

---

## データモデル

### 部位の種類

頭部（`HEAD`）・胴体（`TORSO`）・右腕（`RIGHT_ARM`）・左腕（`LEFT_ARM`）・右脚（`RIGHT_LEG`）・左脚（`LEFT_LEG`）の6種類（`app/models/models.py` の `ALL_PART_NAMES`）。

### `MobileSuit` への追加フィールド

| フィールド | 型 | 説明 |
|---|---|---|
| `missing_parts` | `list[str]` | 欠損部位のリスト（例: 脚部のないMSは `["RIGHT_LEG", "LEFT_LEG"]`）。ここに含めた部位は `parts` に生成されず、命中部位の選択対象からも除外される |
| `parts` | `dict[str, PartState]` | 部位別HP/装甲状態。未設定（空dict）の場合は `max_hp`/`armor`/`missing_parts` から自動生成される |

`PartState`（`app/models/models.py`）:

```python
class PartState(SQLModel):
    max_hp: int
    current_hp: int
    armor: int = 0       # 現状は機体全体のarmorをそのまま踏襲（Phase 4で個別調整を検討）
    destroyed: bool = False
```

**既存の `max_hp`/`current_hp`/`armor`（機体全体値）はそのまま維持し、`parts` はそれとは別に並行管理される。** 全体HPが戦闘終了・撃破判定の正であり続けるため、既存のバトルバランス・撃破ロジックへの回帰は無い。

### 部位ごとのHP配分比率

```python
PART_HP_RATIOS = {
    "HEAD": 0.10,
    "TORSO": 0.30,
    "RIGHT_ARM": 0.15,
    "LEFT_ARM": 0.15,
    "RIGHT_LEG": 0.15,
    "LEFT_LEG": 0.15,
}
```

頭部は被弾面積が小さいため低め、胴体は中枢機構が集中するため最も高く設定した。欠損部位がある場合、その分の配分比率は単純に無視される（残りの部位の合計はMSの `max_hp` を下回る）。この配分は暫定値であり、Phase 4で見直す前提。

### `missing_parts` の指定方法

`MasterMobileSuitSpec.missing_parts`（管理者用マスター機体スペック）、およびショップ購入・スターター機体生成時に読み込む `specs.missing_parts`（`app/routers/shop.py`、`app/routers/pilots.py`、`app/services/pilot_service.py`）で指定できる。未指定時は `[]`（欠損部位なし）。

---

## SQLModelの `table=True` クラスでは `@model_validator(mode="after")` が使えない

`parts` の自動生成を当初 `MobileSuit` の `@model_validator(mode="after")` で実装しようとしたが、SQLModel の `table=True` クラスは `__init__`/`model_validate()` のいずれでも after-validator が正しく動作しないことが判明した（SQLAlchemyのインスツルメンテーション状態 `_sa_instance_state` がまだ無いタイミングで `self.x = ...` のようなフィールド代入を行おうとして `AttributeError` になる、または単に無視される）。これは `current_hp` の既存の `field_validator` に残る "Logic to sync max_hp is better handled in application logic or @model_validator" というコメントが示唆していた制約と一致する。

代わりに `MobileSuit.normalize_parts()` という**明示的に呼び出すメソッド**を追加した:

```python
def normalize_parts(self) -> None:
    """parts列をPartState辞書として正規化する。
    - 生dict(ORM読み込み時)ならPartStateへ変換
    - 空ならmax_hp/armor/missing_partsから自動生成
    """
```

このメソッドは `MobileSuit.weapons`（`list[Weapon]`）が既存コードで各所において `Weapon(**w) if isinstance(w, dict) else w` という形で明示的に変換されているのと同じ設計パターンを踏襲している（`weapons` も同じくSQLAlchemyのORM読み込み時は生dictのまま返る）。

### `normalize_parts()` の呼び出し箇所

- `app/engine/simulation.py` の `BattleSimulator.__init__()` — 全ユニット（`self.units`）に対して一括呼び出し。**戦闘エンジンが実際に部位へアクセスする直前の単一の安全網**であり、他の呼び出し元での呼び出し漏れがあってもここで担保される
- `app/services/matching_service.py` の `_coerce_suit_json_fields()` — NPC/エースのバトル参加準備時
- `main.py` の `simulate_battle()` — プレイヤー機体・敵機体の準備時
- `scripts/run_batch.py` の `_convert_snapshot_to_mobile_suit()` — バトルルームバッチ実行時
- `app/models/models.py` の `MobileSuitResponse.from_mobile_suit()` — MS取得APIレスポンス生成時

新たに `MobileSuit` を構築してバトルエンジンやAPIレスポンスに渡すコードパスを追加する場合、`normalize_parts()` の呼び出しが必要かどうか確認すること（`BattleSimulator.__init__()` を経由するパスであれば安全網でカバーされる）。

---

## 命中後の部位決定レイヤー

`app/engine/combat.py` に `determine_hit_part(attacker, target, weapon, attack_sector, distance) -> str | None` を追加し、`CombatMixin._process_hit()`（命中判定成功後、ダメージ計算の前）で呼び出す。

Issue #503（Phase 2）時点では `attack_sector` のみを使った簡易重み付けの暫定実装だったが、Issue #505（Phase 4）で「武器の狙う部位配分 × セクタ露出係数 × 距離減衰」を掛け合わせた本実装に置き換えた。詳細は下記「武器ごとの狙う部位配分と距離減衰（Phase 4, Issue #505）」を参照。

```python
_part_hit_rng = random.Random()  # 部位選択専用のRNG（下記参照）

def determine_hit_part(attacker, target, weapon, attack_sector, distance) -> str | None:
    eligible_parts = [name for name, part in target.parts.items() if not part.destroyed]
    if not eligible_parts:
        return None
    aim_distribution = getattr(weapon, "aim_distribution", None) or DEFAULT_AIM_DISTRIBUTION
    sector_weights = PART_HIT_WEIGHTS.get(attack_sector, PART_HIT_WEIGHTS["FRONT_SIDE"])
    weights = [
        aim_distribution.get(name, 0.0)
        * sector_weights.get(name, DEFAULT_PART_HIT_WEIGHT)
        * _part_distance_decay(name, distance)
        for name in eligible_parts
    ]
    if sum(weights) <= 0.0:
        weights = [1.0] * len(eligible_parts)  # 全配分が欠損部位向けの縮退ケースの安全策
    return _part_hit_rng.choices(eligible_parts, weights=weights, k=1)[0]
```

- 欠損部位（`target.parts` に存在しない）・既に破壊済みの部位は選択対象から除外される
- `attacker` は将来のパイロットスキル補正等を見据えてシグネチャに残しているが、現状は未使用
- `attack_sector`（既存の `calculate_attack_sector()`、Phase E-3）による露出係数（`PART_HIT_WEIGHTS`, `app/engine/constants.py`）: 前面ほど正面装甲（頭部・胴体・腕）に、背面ほど無防備な脚部に露出しやすい、という傾向を表す。Phase 2時点は単体の重みテーブルだったが、Phase 4では aim_distribution・距離減衰と掛け合わせる一要素として再利用している
- 狙う部位配分に含まれる欠損部位の配分は、`eligible_parts` に含まれないため重み計算の対象外になり、`random.choices` が残りの重みを相対比で正規化することで自動的に他の実在部位へ比例再配分される（明示的な再配分処理は不要）

### 武器ごとの狙う部位配分と距離減衰（Phase 4, Issue #505）

- `WeaponSpecBase.aim_distribution: dict[str, float]`（`app/models/models.py`）: 武器が狙う部位配分（部位名→配分割合、合計1.0）。初期値は `DEFAULT_AIM_DISTRIBUTION`（胴体50% / 右腕10% / 左腕10% / 右脚10% / 左脚10% / 頭部10%）。マスター武器・`PlayerWeapon.base_snapshot` の両方に含まれる
- `WeaponCustomStats.aim_distribution: dict[str, float] | None`: ユーザーが武器インスタンス単位で上書きする戦術設定。`power_bonus`/`accuracy_bonus` と異なりクレジットを消費しない無償の設定。`None` の場合は `base_snapshot` 側の値（マスター初期値）を使う。`WeaponService.apply_effective_spec()` が `custom_stats.aim_distribution` が設定されていればそれを、無ければ `base_snapshot.aim_distribution` をそのまま実効値として採用する
- `WeaponService.update_aim_distribution()`（`app/services/weapon_service.py`）: 部位名の妥当性・非負・合計100%（許容誤差1%）を検証した上で `custom_stats.aim_distribution` を更新する。装備中の武器であれば `resync_mobile_suit_weapons()` で `MobileSuit.weapons` の実効スペックも合わせて再同期する。`PUT /api/player-weapons/{pw_id}/aim-distribution` から呼び出される
- `PART_HIT_DIFFICULTY` / `PART_DIFFICULTY_DECAY_RANGE` / `PART_DIFFICULTY_DECAY_FLOOR`（`app/engine/constants.py`）: 距離による命中難易度減衰。`_part_distance_decay()`（`app/engine/combat.py`）が、難易度の高い部位（頭部: 1.0、腕: 0.5、脚: 0.35）ほど距離0〜`PART_DIFFICULTY_DECAY_RANGE`(600m)にかけて重みを`PART_DIFFICULTY_DECAY_FLOOR`(0.1)まで減衰させる。難易度0の胴体は常に減衰なし（1.0）で、遠距離での命中の受け皿になる。これにより「遠距離では頭部狙いでもほとんど胴体に当たる」という直感的なリアリティを表現している
- フロントエンド: `frontend/src/app/garage/components/AimDistributionEditor.tsx`（`WeaponUpgradeModal.tsx` から呼び出される）で、部位ごとのスライダー（合計100%になるよう検証）から `updatePlayerWeaponAimDistribution()`（`frontend/src/services/weaponEngineering.ts`）経由で設定・保存できる

### 部位選択には共有 `random` モジュールとは独立したRNGを使う

命中判定・クリティカル判定・ダメージ乱数・格闘コンボは共有の `random` モジュールのグローバル状態を直接消費しており、`random.seed()` によるバトル結果の再現性（`sim_bench.py` 等のバランス検証ツール）がその消費順序に依存している。`determine_hit_part()` が同じグローバルストリームから乱数を消費すると、それ以降の乱数列がずれて既存の戦闘結果（クリティカル発生・ダメージ変動・コンボ発生等）に予期しない影響を与えてしまう（Copilotレビュー指摘, PR #508）。これを避けるため、`combat.py` モジュール直下に部位選択専用の `random.Random()` インスタンス（`_part_hit_rng`）を用意し、`determine_hit_part()` はこちらのみを使用する。

### ダメージ適用

`_process_hit()` で最終ダメージ（`final_damage`）確定後、決定された部位の `current_hp` を減算する（0未満にはならず、0に達すると `destroyed=True`）。**全体HP（`target.current_hp`）は従来通り独立してダメージを受け、撃破判定・戦闘終了条件も全体HPを正とする**（既存バトルバランスへの回帰を避けるため、部位HPが0になっても撃破処理は行わない）。

格闘コンボ（`_process_melee_combo()`）による追加ヒットは、現状は部位ダメージの対象外（全体HPのみ減算）。コンボ1回ごとの部位再判定はスコープ外とした。

### `BattleLog.hit_part`

`BattleLog`（`app/models/models.py`）に `hit_part: str | None` を追加し、`ATTACK` ログに命中部位を記録する。Phase 3（バトルログ出力・可視化）向けの土台として、ログスキーマだけ先行して整備した（表示UIは対象外）。

---

## APIレスポンス

`GET /api/mobile_suits` の `MobileSuitResponse` に `missing_parts`/`parts` を追加し、部位別HP/装甲を返すようにした（表示UIは本フェーズのスコープ外）。`frontend/src/types/mobileSuit.ts` にも対応する `PartName`/`PartState` 型と `MobileSuit.missing_parts`/`parts` を追加済み。

---

## マイグレーション

`backend/alembic/versions/c7d8e9f0a1b2_add_parts_to_mobile_suits.py` — `mobile_suits` に `missing_parts`（`JSON`, `server_default='[]'`）・`parts`（`JSON`, `server_default='{}'`）を追加。既存行は空のまま許容し、バックフィルは行わない（`normalize_parts()` が読み取り時に都度自動生成するため）。

---

## 関連ファイル

- `backend/app/models/models.py` — `PartState`, `PART_HP_RATIOS`, `ALL_PART_NAMES`, `build_default_parts()`, `MobileSuit.missing_parts`/`parts`/`normalize_parts()`, `MasterMobileSuitSpec.missing_parts`, `MobileSuitResponse.missing_parts`/`parts`, `BattleLog.hit_part`, `DEFAULT_AIM_DISTRIBUTION`, `WeaponSpecBase.aim_distribution`, `WeaponCustomStats.aim_distribution`（Issue #505）
- `backend/app/engine/combat.py` — `determine_hit_part()`, `_part_distance_decay()`, `_process_hit()` の部位ダメージ適用
- `backend/app/engine/constants.py` — `PART_HIT_WEIGHTS`, `DEFAULT_PART_HIT_WEIGHT`, `PART_HIT_DIFFICULTY`, `PART_DIFFICULTY_DECAY_RANGE`, `PART_DIFFICULTY_DECAY_FLOOR`（Issue #505）
- `backend/app/engine/simulation.py` — `BattleSimulator.__init__()` での `normalize_parts()` 一括呼び出し
- `backend/app/services/matching_service.py` — `_coerce_suit_json_fields()` の更新
- `backend/app/services/weapon_service.py` — `apply_effective_spec()` の aim_distribution マージ、`update_aim_distribution()`（Issue #505）
- `backend/app/routers/player_weapons.py` — `PUT /{pw_id}/aim-distribution`（Issue #505）
- `backend/main.py` / `backend/scripts/run_batch.py` — `normalize_parts()` 呼び出しの追加
- `backend/app/routers/shop.py` / `backend/app/routers/pilots.py` / `backend/app/services/pilot_service.py` — `missing_parts` の伝播
- `backend/alembic/versions/c7d8e9f0a1b2_add_parts_to_mobile_suits.py`
- `backend/tests/unit/test_hit_part_determination.py`, `backend/tests/unit/test_weapon_custom_stats.py`, `backend/tests/test_aim_distribution.py`
- `frontend/src/types/mobileSuit.ts` — `PartName`, `PartState`, `MobileSuit.missing_parts`/`parts`
- `frontend/src/types/weapon.ts` / `frontend/src/types/shop.ts` — `Weapon.aim_distribution`, `WeaponCustomStats.aim_distribution`, `AimDistributionUpdateRequest`（Issue #505）
- `frontend/src/services/weaponEngineering.ts` — `updatePlayerWeaponAimDistribution()`（Issue #505）
- `frontend/src/app/garage/components/AimDistributionEditor.tsx` / `WeaponUpgradeModal.tsx`（Issue #505）

## 今後の拡張（別Issue）

- バトルログ・BattleViewerでの部位ヒット表示（Phase 3、完了）
- 戦術設定・角度・距離に基づく本格的な部位命中確率算出（`determine_hit_part()` の置き換え、Phase 4、完了）
- 部位破壊による機能制限（腕破壊で近接武器使用不可、脚破壊で機動性低下 等、Phase 4以降）
- 部位別装甲値の個別調整（現状は機体全体の `armor` をそのまま踏襲、Phase 4以降）
- ガレージUIでの狙う部位配分プレビュー（セクタ別・距離別の実効命中率シミュレーション表示等）

---

## テスト

```bash
cd backend && python -m pytest tests/unit/test_hit_part_determination.py tests/unit/test_weapon_custom_stats.py tests/test_aim_distribution.py --tb=short
cd backend && python -m pytest tests/unit --tb=short
cd frontend && ./node_modules/.bin/tsc --noEmit
cd frontend && npx vitest run tests/unit/weaponEngineeringService.test.ts
```
