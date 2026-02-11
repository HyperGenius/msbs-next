# パイロットスキルシステム実装レポート

## 概要

パイロットのレベルアップ時に獲得できる「スキルポイント (SP)」を消費して、戦闘を有利にする「パッシブスキル」を習得・強化できるシステムを実装しました。

## 実装内容

### 1. Backend実装

#### データモデル拡張 (`backend/app/models/models.py`)
```python
class Pilot(SQLModel, table=True):
    skill_points: int = Field(default=0, description="未使用のスキルポイント")
    skills: dict[str, int] = Field(
        default_factory=dict, sa_column=Column(JSON), description="習得済みスキル"
    )
```

#### スキルマスターデータ (`backend/app/core/skills.py`)
以下の4つのスキルを定義：
- **命中率向上** (`accuracy_up`): +2% / Lv（最大Lv10）
- **回避率向上** (`evasion_up`): +2% / Lv（最大Lv10）
- **攻撃力向上** (`damage_up`): +3% / Lv（最大Lv10）
- **クリティカル率向上** (`crit_rate_up`): +1% / Lv（最大Lv10）

スキル習得コスト: 一律1 SP

#### データベースマイグレーション
`backend/alembic/versions/7b8c9d0e1f2a_add_pilot_skill_fields.py`
- `skill_points`カラム追加（デフォルト値: 0）
- `skills`カラム追加（JSON型）

#### PilotServiceの拡張 (`backend/app/services/pilot_service.py`)
1. **レベルアップ時のSP付与**
   - `add_rewards`メソッド内でレベルアップごとに1 SP付与
   
2. **スキル習得メソッド**
   ```python
   def unlock_skill(self, pilot: Pilot, skill_id: str) -> tuple[Pilot, str]:
   ```
   - SPの検証
   - 最大レベルチェック
   - スキルレベルの更新

#### APIエンドポイント (`backend/app/routers/pilots.py`)
1. `GET /api/pilots/skills`
   - 利用可能なスキル一覧を取得
   
2. `POST /api/pilots/skills/unlock`
   - スキルを習得または強化
   - リクエスト: `{"skill_id": "accuracy_up"}`
   - レスポンス: 更新後のパイロット情報とメッセージ

#### 戦闘シミュレーション (`backend/app/engine/simulation.py`)
`BattleSimulator`を拡張してパイロットスキルを適用：

1. **初期化時にスキル情報を受け取る**
   ```python
   def __init__(self, player, enemies, player_skills: dict[str, int] | None = None)
   ```

2. **命中率計算時にスキル効果を適用**
   - プレイヤー攻撃時: `accuracy_up`スキルで命中率向上
   - 敵の攻撃時: `evasion_up`スキルで回避率向上（敵の命中率減少）

3. **ダメージ計算時にスキル効果を適用**
   - `damage_up`スキルでダメージ増加
   - `crit_rate_up`スキルでクリティカル率向上

#### バトルエンドポイントの更新 (`backend/main.py`)
`/api/battle/simulate`エンドポイントでパイロットスキルを取得し、シミュレーターに渡すように修正。

### 2. Frontend実装

#### 型定義 (`frontend/src/types/battle.ts`)
```typescript
interface Pilot {
    skill_points: number;
    skills: Record<string, number>;
}

interface SkillDefinition {
    id: string;
    name: string;
    description: string;
    effect_per_level: number;
    max_level: number;
}
```

#### API関数 (`frontend/src/services/api.ts`)
```typescript
export function useSkills() // スキル一覧取得フック
export async function unlockSkill(skillId: string) // スキル習得関数
```

#### パイロット画面 (`frontend/src/app/pilot/page.tsx`)
- パイロットステータス表示（Lv, EXP, Credits, SP）
- 経験値プログレスバー
- スキルカード表示（4スキル）
  - スキル名、説明
  - 現在レベル / 最大レベル
  - 効果量表示
  - 強化ボタン（SP消費）
- エラー/成功メッセージ表示

#### ヘッダー更新 (`frontend/src/components/Header.tsx`)
- パイロット情報エリアを`<Link>`でラップ
- SP（スキルポイント）の表示を追加
- クリックで`/pilot`画面に遷移

### 3. テスト実装

#### ユニットテスト (`backend/tests/unit/test_pilot_skills.py`)
以下のケースをテスト：
- スキル習得の成功ケース
- スキルレベルアップ
- SP不足時のエラー
- 最大レベル時のエラー
- 無効なスキルID
- レベルアップ時のSP付与（単一・複数）

### 4. 品質保証

#### リンティング
- Backend: Ruff（チェック・フォーマット） ✅
- Frontend: ESLint ✅

#### セキュリティスキャン
- CodeQL分析: 脆弱性0件 ✅

#### コードレビュー
- 指摘事項: 1件（i18nに関する提案のみ、機能には影響なし）

## 使用方法

### 1. データベースマイグレーション
```bash
cd backend
alembic upgrade head
```

### 2. バックエンドの起動
```bash
cd backend
uvicorn main:app --reload
```

### 3. フロントエンドの起動
```bash
cd frontend
npm run dev
```

### 4. スキル習得の流れ
1. バトルに勝利してレベルアップ → 1 SP獲得
2. ヘッダーのパイロット情報をクリック → `/pilot`画面に遷移
3. 習得したいスキルの「強化 (-1 SP)」ボタンをクリック
4. スキルレベルが上昇し、SPが1減少
5. 次回のバトルからスキル効果が適用される

## 動作確認項目

### Backend
- [x] パイロットモデルに新フィールドが追加されている
- [x] レベルアップ時にSPが付与される
- [x] スキル習得APIが正常に動作する
- [x] SP不足時にエラーが返される
- [x] 最大レベル時にエラーが返される
- [x] バトルシミュレーションでスキル効果が適用される

### Frontend
- [x] `/pilot`画面が表示される
- [x] パイロットステータスが正しく表示される
- [x] スキル一覧が表示される
- [x] スキル強化ボタンが動作する
- [x] SP不足時はボタンが無効化される
- [x] ヘッダーにSPが表示される
- [x] ヘッダーのパイロット情報がクリック可能

### Tests
- [x] ユニットテストが全て成功する
- [x] リンティングエラーがない
- [x] セキュリティ脆弱性がない

## 技術的な実装ポイント

### 1. スキル効果の適用タイミング
スキル効果は戦闘開始時にパイロット情報から読み込まれ、各計算時に適用されます。
- 命中率: 攻撃判定時に加算
- 回避率: 防御側の機動性として扱い、攻撃側の命中率を減算
- ダメージ: 基礎ダメージ計算後に乗算
- クリティカル率: 乱数判定の閾値を加算

### 2. データの整合性
- スキルマスターデータはバックエンドで一元管理
- フロントエンドはAPIから取得した定義を使用
- スキルレベルはJSON形式でDBに保存（柔軟性確保）

### 3. ユーザビリティ
- ヘッダーでSPが確認できる
- SPがある場合は目立つように紫色で表示
- スキル画面で現在の効果量が一目で分かる
- ボタンの状態で操作可否が明確

## 今後の拡張案

1. **追加スキル**
   - 移動速度向上
   - HP増加
   - 装甲強化
   - センサー範囲拡大

2. **スキルツリー**
   - 前提スキルの実装
   - スキル系統の分岐

3. **スキルリセット機能**
   - クレジット消費でスキルをリセット

4. **ビジュアル改善**
   - スキルアイコンの追加
   - エフェクトアニメーション

## まとめ

パイロットスキルシステムの実装により、以下の目的を達成しました：

✅ レベルアップに対する報酬感の提供  
✅ 育成の選択肢の提供  
✅ 戦闘シミュレーションへのパイロット個性の反映  

全てのテストとセキュリティチェックに合格しており、本番環境へのデプロイが可能な状態です。
