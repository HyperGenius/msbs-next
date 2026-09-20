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

`app/engine/combat.py` に `determine_hit_part(attacker, target, attack_sector, distance) -> str | None` を追加し、`CombatMixin._process_hit()`（命中判定成功後、ダメージ計算の前）で呼び出す。

```python
def determine_hit_part(attacker, target, attack_sector, distance) -> str | None:
    eligible_parts = [name for name, part in target.parts.items() if not part.destroyed]
    if not eligible_parts:
        return None
    sector_weights = PART_HIT_WEIGHTS.get(attack_sector, PART_HIT_WEIGHTS["FRONT_SIDE"])
    weights = [sector_weights.get(name, DEFAULT_PART_HIT_WEIGHT) for name in eligible_parts]
    return random.choices(eligible_parts, weights=weights, k=1)[0]
```

- 欠損部位（`target.parts` に存在しない）・既に破壊済みの部位は選択対象から除外される
- `attacker`/`distance` は本フェーズでは未使用だが、Phase 4での差し替え（`determine_hit_part(attacker, target, attack_sector, distance) -> PartName` というIssueのヒント記載シグネチャ）を見据えてシグネチャに含めている
- `attack_sector`（既存の `calculate_attack_sector()`、Phase E-3）を粗く使った簡易重み付け（`PART_HIT_WEIGHTS`, `app/engine/constants.py`）: 前面ほど正面装甲（頭部・胴体・腕）に、背面ほど無防備な脚部に命中しやすい、という直感的な傾向のみを反映

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

- `backend/app/models/models.py` — `PartState`, `PART_HP_RATIOS`, `ALL_PART_NAMES`, `build_default_parts()`, `MobileSuit.missing_parts`/`parts`/`normalize_parts()`, `MasterMobileSuitSpec.missing_parts`, `MobileSuitResponse.missing_parts`/`parts`, `BattleLog.hit_part`
- `backend/app/engine/combat.py` — `determine_hit_part()`, `_process_hit()` の部位ダメージ適用
- `backend/app/engine/constants.py` — `PART_HIT_WEIGHTS`, `DEFAULT_PART_HIT_WEIGHT`
- `backend/app/engine/simulation.py` — `BattleSimulator.__init__()` での `normalize_parts()` 一括呼び出し
- `backend/app/services/matching_service.py` — `_coerce_suit_json_fields()` の更新
- `backend/main.py` / `backend/scripts/run_batch.py` — `normalize_parts()` 呼び出しの追加
- `backend/app/routers/shop.py` / `backend/app/routers/pilots.py` / `backend/app/services/pilot_service.py` — `missing_parts` の伝播
- `backend/alembic/versions/c7d8e9f0a1b2_add_parts_to_mobile_suits.py`
- `backend/tests/unit/test_hit_part_determination.py`
- `frontend/src/types/mobileSuit.ts` — `PartName`, `PartState`, `MobileSuit.missing_parts`/`parts`

## 今後の拡張（Phase 4, 別Issue）

- 戦術設定・角度・距離に基づく本格的な部位命中確率算出（`determine_hit_part()` の置き換え）
- 部位破壊による機能制限（腕破壊で近接武器使用不可、脚破壊で機動性低下 等）
- 部位別装甲値の個別調整（現状は機体全体の `armor` をそのまま踏襲）
- バトルログ・BattleViewerでの部位ヒット表示（Phase 3）

---

## テスト

```bash
cd backend && python -m pytest tests/unit/test_hit_part_determination.py --tb=short
cd backend && python -m pytest tests/unit --tb=short
cd frontend && ./node_modules/.bin/tsc --noEmit
```
