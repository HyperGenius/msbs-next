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
- `custom_stats`: **強化・改造による差分を持たせるための予約フィールド。現状は常に空 `{}` で、読み書きするロジックは未実装**（将来の武器改造機能で `base_snapshot + custom_stats` をマージして実効スペックを計算する設計を想定）
- `equipped_ms_id` / `equipped_slot`: 装備状態の正。`UniqueConstraint(equipped_ms_id, equipped_slot)` で1スロット1武器を担保

一方で `MobileSuit.weapons`（JSON列）は**バトルエンジンが直接参照するためのスナップショットのリスト**であり、装備操作のたびに `PlayerWeapon` の内容から書き込まれる（dual-write）。装備状態を問い合わせる/表示する処理は必ず `PlayerWeapon.equipped_ms_id`/`equipped_slot` を正として使うこと。

**既知の設計上の矛盾**: `EngineeringService`（`app/services/engineering_service.py`）の `weapon_power` 強化項目は、`PlayerWeapon` インスタンス単位ではなく `MobileSuit.weapons` の**全スロットに一律加算**する実装になっている（`_apply_weapon_power_upgrade`）。そのため武器を外す・付け替えると強化投資が失われ、`PlayerWeapon.custom_stats` を正とする将来の武器インスタンス単位の改造機能とは非互換。武器改造機能を実装する際は、この既存の `weapon_power` 強化との関係（統合するか、別軸の強化として維持するか）を先に決める必要がある。

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
