# 次のステップ: 開発優先度ガイド

**作成日**: 2026年2月9日  
**現在のフェーズ**: Phase 2.5 完了、Phase 3 準備中

Phase 2.5（シミュレーションエンジンの高度化）が完了した今、次に取り組むべき項目を優先度順にまとめたドキュメントです。

---

## 📊 現在の状況

### ✅ 完了している主要機能
- ✅ Phase 0: Simulation Engine Core
- ✅ Phase 1: MVP (基本的なゲームサイクル)
- ✅ Phase 2: α版 (定期更新型 PvPvE)
- ✅ Phase 2.5: シミュレーションエンジンの高度化
  - 武器属性と相性システム
  - 地形適正と索敵（Fog of War）
  - 戦略AI
  - リソース管理（弾薬、EN、クールダウン）

### 🔧 課題
- Phase 2.5の高度な機能がFrontendに未反映
- エントリーシステムが実装済みだがバッチ処理が未稼働
- デプロイ環境が未構築
- E2Eテストが未整備

---

## 🎯 推奨する次のステップ

### 優先度 🔴 高 - ユーザー体験の向上

#### 1. フロントエンドのPhase 2.5対応 ⭐ 最優先
**目的**: バックエンドで実装済みの高度な機能をUIに反映し、ユーザーが戦略性の向上を体感できるようにする。

**作業時間**: 1-2日

**実装内容**:

##### 1.1 ガレージUIの拡張
現在のガレージ画面には基本ステータスのみ表示されているが、Phase 2.5で追加された以下の情報を追加する：

- **地形適正の表示**
  ```tsx
  <div className="mt-4 p-4 bg-gray-900 rounded border border-green-800">
    <h3 className="font-bold mb-2">地形適正</h3>
    <div className="grid grid-cols-4 gap-2 text-xs">
      <div>
        <div className="opacity-70">宇宙 (SPACE)</div>
        <div className={`text-lg font-bold ${getGradeColor(ms.terrain_adaptability?.SPACE)}`}>
          {ms.terrain_adaptability?.SPACE || 'A'}
        </div>
      </div>
      <div>
        <div className="opacity-70">地上 (GROUND)</div>
        <div className={`text-lg font-bold ${getGradeColor(ms.terrain_adaptability?.GROUND)}`}>
          {ms.terrain_adaptability?.GROUND || 'A'}
        </div>
      </div>
      <div>
        <div className="opacity-70">コロニー (COLONY)</div>
        <div className={`text-lg font-bold ${getGradeColor(ms.terrain_adaptability?.COLONY)}`}>
          {ms.terrain_adaptability?.COLONY || 'A'}
        </div>
      </div>
      <div>
        <div className="opacity-70">水中 (UNDERWATER)</div>
        <div className={`text-lg font-bold ${getGradeColor(ms.terrain_adaptability?.UNDERWATER)}`}>
          {ms.terrain_adaptability?.UNDERWATER || 'C'}
        </div>
      </div>
    </div>
    <div className="text-xs opacity-60 mt-2">
      S: 1.2倍 / A: 1.0倍 / B: 0.8倍 / C: 0.6倍 / D: 0.4倍
    </div>
  </div>
  ```

- **リソース情報の表示**
  ```tsx
  <div className="mt-4 p-4 bg-gray-900 rounded border border-green-800">
    <h3 className="font-bold mb-2">エネルギーシステム</h3>
    <div className="space-y-2 text-sm">
      <div className="flex justify-between">
        <span>最大EN:</span>
        <span className="font-mono">{ms.max_en || 1000}</span>
      </div>
      <div className="flex justify-between">
        <span>EN回復:</span>
        <span className="font-mono">{ms.en_recovery || 100}/ターン</span>
      </div>
      <div className="flex justify-between">
        <span>推進剤:</span>
        <span className="font-mono">{ms.max_propellant || 1000}</span>
      </div>
    </div>
  </div>
  ```

- **武器の詳細情報表示**
  ```tsx
  {ms.weapons?.map((weapon, idx) => (
    <div key={idx} className="p-3 bg-gray-900 rounded border border-green-700">
      <div className="font-bold">{weapon.name}</div>
      <div className="grid grid-cols-2 gap-2 text-xs mt-2">
        <div>威力: {weapon.power}</div>
        <div>射程: {weapon.range}m</div>
        <div>命中率: {weapon.accuracy}%</div>
        <div>タイプ: {weapon.type || 'PHYSICAL'}</div>
        <div>最適射程: {weapon.optimal_range || 300}m</div>
        <div>減衰率: {weapon.decay_rate || 0.05}</div>
        {weapon.max_ammo && (
          <div>弾数: {weapon.max_ammo}発</div>
        )}
        {weapon.en_cost > 0 && (
          <div>EN消費: {weapon.en_cost}</div>
        )}
        {weapon.cool_down_turn > 0 && (
          <div>CT: {weapon.cool_down_turn}ターン</div>
        )}
      </div>
    </div>
  ))}
  ```

##### 1.2 バトルビューアの拡張

現在のバトルビューアは基本的なHP表示のみだが、以下を追加：

- **リアルタイムリソースゲージ表示**
  - ENゲージ（青色）
  - 弾薬残量（オレンジ色）
  - 武器クールダウン状態（アイコン点滅）

- **索敵範囲の可視化**
  ```tsx
  // React Three Fiberで索敵範囲を円形で表示
  <mesh position={[pos.x, 0, pos.z]} rotation={[-Math.PI / 2, 0, 0]}>
    <ringGeometry args={[ms.sensor_range * 0.048, ms.sensor_range * 0.05, 32]} />
    <meshBasicMaterial color="#00ff0033" transparent opacity={0.2} />
  </mesh>
  ```

- **地形環境に応じた背景演出の強化**
  - SPACE: 星空 + 黒背景（現状維持）
  - GROUND: 地面テクスチャ + 緑がかった霧
  - COLONY: 建造物の影 + グリッド強調
  - UNDERWATER: 青いフォグ + 水面エフェクト

- **戦闘ログの詳細化**
  - 「弾切れ」「EN不足」「クールダウン中」などのリソース制限メッセージ
  - 地形補正の効果表示（「地形適正Aにより移動速度1.0倍」）
  - 武器属性と耐性の相性表示（「ビーム兵器 vs 対ビーム装甲20%」）

**ファイル**:
- `frontend/src/app/garage/page.tsx`
- `frontend/src/components/BattleViewer.tsx`
- `frontend/src/types/battle.ts` (型定義は既に対応済み)

**メリット**:
- ユーザーが戦略的な機体構成を検討できるようになる
- Phase 2.5の実装成果が可視化される
- 機体選択・武器選択の重要性が明確になる

---

#### 2. エントリーシステムの完全実装
**目的**: 定期更新型ゲームの核心機能を稼働させ、本格的なPvPvE体験を提供する。

**作業時間**: 2-3日

**実装内容**:

##### 2.1 フロントエンド改善

- **エントリー状態の視覚的フィードバック強化**
  ```tsx
  {entryStatus ? (
    <div className="bg-green-900/30 border-2 border-green-500 rounded-lg p-6">
      <h3 className="text-xl font-bold mb-2">✅ エントリー済み</h3>
      <p className="mb-4">
        次回バトルへのエントリーが完了しました。
        バトルは毎日21:00に自動実行されます。
      </p>
      <div className="bg-gray-900 p-4 rounded mb-4">
        <div className="text-sm opacity-70 mb-1">使用機体</div>
        <div className="font-bold">{entryStatus.mobile_suit_snapshot.name}</div>
      </div>
      <CountdownTimer targetTime="21:00" />
      <button
        onClick={handleCancelEntry}
        disabled={entryLoading}
        className="mt-4 px-6 py-2 bg-red-700 hover:bg-red-600 rounded"
      >
        エントリーをキャンセル
      </button>
    </div>
  ) : (
    <div className="bg-gray-900/30 border-2 border-gray-700 rounded-lg p-6">
      <h3 className="text-xl font-bold mb-2">次回バトルにエントリー</h3>
      <p className="mb-4">
        21:00の定期バッチで実行されるバトルロイヤルに参加できます。
      </p>
      <button
        onClick={handleEntry}
        disabled={entryLoading || !mobileSuits?.length}
        className="px-6 py-2 bg-green-700 hover:bg-green-600 rounded"
      >
        エントリーする
      </button>
    </div>
  )}
  ```

- **次回更新時刻の表示とカウントダウン**
  ```tsx
  const CountdownTimer = ({ targetTime }: { targetTime: string }) => {
    const [timeLeft, setTimeLeft] = useState('');
    
    useEffect(() => {
      const interval = setInterval(() => {
        const now = new Date();
        const target = new Date();
        const [hours, minutes] = targetTime.split(':').map(Number);
        target.setHours(hours, minutes, 0, 0);
        
        if (target < now) {
          target.setDate(target.getDate() + 1);
        }
        
        const diff = target.getTime() - now.getTime();
        const h = Math.floor(diff / 3600000);
        const m = Math.floor((diff % 3600000) / 60000);
        const s = Math.floor((diff % 60000) / 1000);
        
        setTimeLeft(`${h}時間 ${m}分 ${s}秒`);
      }, 1000);
      
      return () => clearInterval(interval);
    }, [targetTime]);
    
    return (
      <div className="text-center text-2xl font-mono font-bold text-green-400">
        次回バトルまで: {timeLeft}
      </div>
    );
  };
  ```

- **エントリー済みユーザー数の表示**（プライバシーに配慮し、名前は非表示）
  ```tsx
  // 新規API: GET /api/entries/count
  <div className="text-sm opacity-70 mt-4">
    現在のエントリー数: <span className="font-bold">{entryCount}</span> 人
  </div>
  ```

##### 2.2 バックエンド拡張

- **エントリー統計APIの追加**
  ```python
  # backend/main.py
  @app.get("/api/entries/count")
  async def get_entry_count(session: Session = Depends(get_session)) -> dict:
      """現在のエントリー数を取得."""
      count = session.exec(
          select(func.count(BattleEntry.id))
          .where(BattleEntry.room_id == None)
      ).one()
      return {"count": count}
  ```

##### 2.3 バッチスケジュールの有効化

- **GitHub Actions Workflowのcron有効化**
  ```yaml
  # .github/workflows/scheduled-battle.yaml
  on:
    workflow_dispatch:
    
    # 毎日 JST 21:00 = UTC 12:00 に実行
    schedule:
      - cron: '0 12 * * *'  # ← コメント解除
  ```

- **通知機能の追加**（オプション）
  ```yaml
  - name: Notify on success
    if: success()
    run: |
      echo "Batch completed successfully. ${{ steps.batch.outputs.battle_count }} battles executed."
      # Webhook通知やメール送信を追加可能
  ```

**ファイル**:
- `frontend/src/app/page.tsx`
- `backend/main.py`
- `.github/workflows/scheduled-battle.yaml`

**メリット**:
- 定期更新型ゲームとしての体験が完成する
- ユーザーが「次回のバトル」を楽しみに待つ仕組みができる
- プロジェクトの差別化要素（定期更新型）が明確になる

---

### 優先度 🟡 中 - システムの安定性と品質向上

#### 3. テストカバレッジの拡充
**目的**: Phase 2.5機能の品質保証と、リグレッションの防止。

**作業時間**: 2-3日

**実装内容**:

##### 3.1 Phase 2.5機能の統合テスト

- **地形適正テストの拡充**
  ```python
  # backend/tests/unit/test_terrain_and_detection.py
  def test_terrain_affects_combat_outcome():
      """地形適正が戦闘結果に影響することを確認."""
      # 地形適正Sの機体 vs 地形適正Dの機体
      # 移動速度差により、戦闘結果が変わることを検証
  ```

- **リソース管理の境界値テスト**
  ```python
  def test_ammo_depletion():
      """弾薬切れ時の動作を確認."""
      # 弾数制限のある武器で連続攻撃
      # 弾切れ後は攻撃不可になることを検証
  
  def test_en_management():
      """EN管理の動作を確認."""
      # ビーム兵器連射でEN枯渇
      # EN不足時は攻撃不可、回復後は再攻撃可能
  
  def test_weapon_cooldown():
      """クールダウンの動作を確認."""
      # CT付き武器で攻撃後、指定ターン数待機が必要
  ```

- **武器属性と耐性の相性テスト**
  ```python
  def test_weapon_type_vs_resistance():
      """武器属性と耐性の相性を確認."""
      # ビーム兵器 vs 対ビーム装甲50%
      # ダメージが半減されることを検証
  ```

##### 3.2 フロントエンドのE2Eテスト

Playwrightを使用したブラウザ自動テストの導入：

```bash
# セットアップ
cd frontend
npm install -D @playwright/test
npx playwright install
```

```typescript
// frontend/tests/e2e/garage.spec.ts
import { test, expect } from '@playwright/test';

test('ガレージで機体を選択して編集できる', async ({ page }) => {
  await page.goto('http://localhost:3000/garage');
  
  // 機体一覧が表示される
  await expect(page.locator('text=機体一覧')).toBeVisible();
  
  // 機体を選択
  await page.click('text=RX-78-2 ガンダム');
  
  // ステータス編集フォームが表示される
  await expect(page.locator('text=機体ステータス編集')).toBeVisible();
  
  // 名前を変更
  await page.fill('input[type="text"]', 'マイガンダム');
  
  // 保存
  await page.click('button:has-text("保存")');
  
  // 成功メッセージ
  await expect(page.locator('text=機体データを更新しました')).toBeVisible();
});

test('バトルを実行してリプレイを確認できる', async ({ page }) => {
  await page.goto('http://localhost:3000');
  
  // ミッション選択
  await page.selectOption('select', '1');
  
  // バトル開始
  await page.click('button:has-text("バトル開始")');
  
  // ローディング
  await page.waitForSelector('text=バトルログ', { timeout: 10000 });
  
  // 3Dビューアが表示される
  await expect(page.locator('canvas')).toBeVisible();
});
```

**ファイル**:
- `backend/tests/unit/test_terrain_and_detection.py`
- `backend/tests/unit/test_resource_management.py` (新規)
- `backend/tests/unit/test_weapon_attributes.py` (新規)
- `frontend/tests/e2e/` (新規ディレクトリ)

**メリット**:
- バグの早期発見
- リファクタリング時の安心感
- CI/CDパイプラインへの組み込み準備

---

#### 4. デプロイ環境の構築
**目的**: ローカル環境からクラウド環境へ移行し、外部アクセス可能にする。

**作業時間**: 3-5日

**実装内容**:

##### 4.1 Frontend: Vercel デプロイ

```json
// vercel.json
{
  "buildCommand": "cd frontend && npm run build",
  "outputDirectory": "frontend/.next",
  "framework": "nextjs",
  "env": {
    "NEXT_PUBLIC_API_URL": "@api_url"
  },
  "regions": ["hnd1"]
}
```

**手順**:
1. Vercelアカウント作成
2. GitHubリポジトリ連携
3. 環境変数設定（`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`）
4. デプロイ実行

##### 4.2 Backend: Render.com デプロイ

```yaml
# render.yaml
services:
  - type: web
    name: msbs-backend
    env: python
    region: singapore
    plan: free
    buildCommand: |
      cd backend
      pip install -r requirements.txt
    startCommand: |
      cd backend
      uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: NEON_DATABASE_URL
        sync: false
      - key: CLERK_JWKS_URL
        sync: false
      - key: CLERK_SECRET_KEY
        sync: false
```

**代替案**: Railway（より簡単、無料枠あり）
```toml
# railway.toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r backend/requirements.txt"

[deploy]
startCommand = "cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
```

##### 4.3 CI/CDパイプラインの整備

```yaml
# .github/workflows/deploy.yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Run tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest
  
  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
```

**ファイル**:
- `vercel.json`
- `render.yaml` または `railway.toml`
- `.github/workflows/deploy.yaml`

**メリット**:
- 本番環境での動作確認が可能
- 外部からのアクセスが可能（ポートフォリオとして公開可能）
- 継続的デリバリーの実現

---

### 優先度 🟢 中低 - 機能拡張（Phase 3の先取り）

#### 5. NPC永続化システム
**目的**: NPCに個性を持たせ、「あの時のザク」との再戦を可能にする。

**作業時間**: 3-4日

**実装内容**:

##### 5.1 データベーススキーマの拡張

現在、NPCは`MatchingService.generate_npcs()`で毎回生成されているが、これを永続化する：

```python
# backend/app/models/models.py
class Pilot(SQLModel, table=True):
    # ... 既存フィールド
    is_npc: bool = Field(default=False)  # 追加
    npc_personality: str | None = Field(default=None)  # 追加: "AGGRESSIVE", "DEFENSIVE", "BALANCED"
```

##### 5.2 NPC名前生成ロジック

ランダムな名前ではなく、記憶に残る名前を生成：

```python
# backend/app/services/npc_service.py
import random

FIRST_NAMES = ["ジョニー", "シン", "ランバ", "ガイア", "オルテガ", "マッシュ"]
LAST_NAMES = ["ライデン", "マツナガ", "ラル", "マッシュ", "オルテガ", "ガイア"]
RANKS = ["少尉", "中尉", "大尉", "少佐", "中佐"]

def generate_npc_name() -> str:
    """個性的なNPC名を生成."""
    rank = random.choice(RANKS)
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return f"{rank} {first}・{last}"
```

##### 5.3 NPC成長システムの基盤

バトル後、NPCも経験値を獲得：

```python
# backend/app/services/pilot_service.py
def apply_npc_battle_rewards(npc_pilot_id: str, victory: bool, kills: int):
    """NPC用の報酬処理."""
    pilot = session.get(Pilot, npc_pilot_id)
    if not pilot or not pilot.is_npc:
        return
    
    exp_gain = 50 if victory else 10
    exp_gain += kills * 5
    
    pilot.exp += exp_gain
    
    # レベルアップ判定
    while pilot.exp >= calculate_required_exp(pilot.level):
        pilot.level += 1
        pilot.exp -= calculate_required_exp(pilot.level - 1)
    
    session.commit()
```

##### 5.4 NPC再登場システム

次回バトルで、前回のNPCが再登場する確率を設定：

```python
# backend/app/services/matching_service.py
def select_npcs_for_room(room_id: str, count: int) -> list[Pilot]:
    """既存NPCと新規NPCをミックスしてルームに追加."""
    # 50%の確率で既存NPCを再登場させる
    existing_npcs = session.exec(
        select(Pilot)
        .where(Pilot.is_npc == True)
        .order_by(func.random())
        .limit(count // 2)
    ).all()
    
    new_npc_count = count - len(existing_npcs)
    new_npcs = [create_new_npc() for _ in range(new_npc_count)]
    
    return list(existing_npcs) + new_npcs
```

**ファイル**:
- `backend/app/models/models.py`
- `backend/app/services/npc_service.py` (新規)
- `backend/app/services/matching_service.py`

**メリット**:
- NPCに個性が生まれ、世界観が豊かになる
- 「あのNPCに勝ちたい」というモチベーション
- 将来的なNPC AI改善の基盤

---

#### 6. ランキングシステムの実装
**目的**: プレイヤー間の競争要素を導入し、リテンション向上。

**作業時間**: 3-4日

**実装内容**:

##### 6.1 データベーススキーマの追加

```python
# backend/app/models/models.py
class Season(SQLModel, table=True):
    __tablename__ = "seasons"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str  # "Season 1: 一年戦争"
    start_date: datetime
    end_date: datetime
    is_active: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Leaderboard(SQLModel, table=True):
    __tablename__ = "leaderboards"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    season_id: uuid.UUID = Field(foreign_key="seasons.id")
    user_id: str  # Clerk User ID
    
    total_points: int = Field(default=0)
    total_battles: int = Field(default=0)
    total_wins: int = Field(default=0)
    total_kills: int = Field(default=0)
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

##### 6.2 ポイント計算ロジック

```python
# backend/app/services/ranking_service.py
def calculate_battle_points(
    victory: bool,
    kills: int,
    rank: int,  # 1位, 2位, 3位...
    total_participants: int
) -> int:
    """バトル結果からポイントを計算."""
    base_points = 100 if victory else 20
    kill_bonus = kills * 10
    rank_bonus = max(0, (total_participants - rank) * 5)
    
    return base_points + kill_bonus + rank_bonus
```

##### 6.3 ランキングAPI

```python
# backend/main.py
@app.get("/api/rankings/current")
async def get_current_rankings(
    limit: int = 100,
    session: Session = Depends(get_session)
) -> list[dict]:
    """現在のシーズンのランキングを取得."""
    current_season = session.exec(
        select(Season).where(Season.is_active == True)
    ).first()
    
    if not current_season:
        raise HTTPException(404, "Active season not found")
    
    rankings = session.exec(
        select(Leaderboard, Pilot)
        .join(Pilot, Leaderboard.user_id == Pilot.user_id)
        .where(Leaderboard.season_id == current_season.id)
        .order_by(Leaderboard.total_points.desc())
        .limit(limit)
    ).all()
    
    return [
        {
            "rank": idx + 1,
            "pilot_name": pilot.name,
            "total_points": lb.total_points,
            "total_wins": lb.total_wins,
            "total_battles": lb.total_battles,
            "total_kills": lb.total_kills,
        }
        for idx, (lb, pilot) in enumerate(rankings)
    ]
```

##### 6.4 フロントエンドのランキング画面

```tsx
// frontend/src/app/rankings/page.tsx
export default function RankingsPage() {
  const { rankings, isLoading } = useRankings();
  
  return (
    <div className="min-h-screen bg-gray-900 text-green-400 p-8 font-mono">
      <Header />
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">ランキング</h1>
        
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-green-800">
              <th className="p-3 text-left">順位</th>
              <th className="p-3 text-left">パイロット名</th>
              <th className="p-3 text-right">ポイント</th>
              <th className="p-3 text-right">勝利数</th>
              <th className="p-3 text-right">撃墜数</th>
            </tr>
          </thead>
          <tbody>
            {rankings?.map((entry) => (
              <tr key={entry.rank} className="border-b border-green-900">
                <td className="p-3">{entry.rank}</td>
                <td className="p-3 font-bold">{entry.pilot_name}</td>
                <td className="p-3 text-right">{entry.total_points}</td>
                <td className="p-3 text-right">{entry.total_wins}</td>
                <td className="p-3 text-right">{entry.total_kills}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

**ファイル**:
- `backend/app/models/models.py`
- `backend/app/services/ranking_service.py` (新規)
- `backend/main.py`
- `frontend/src/app/rankings/page.tsx` (新規)

**メリット**:
- 競争要素の導入
- プレイヤーのモチベーション向上
- シーズン制による定期的なリセットで新規参入障壁を下げる

---

### 優先度 🔵 低 - コード品質とDX向上

#### 7. リファクタリング
**目的**: コードの保守性向上と技術的負債の解消。

**作業時間**: 継続的に実施

**実施項目**:

##### 7.1 Backend リファクタリング

- **BattleSimulatorの複雑度削減**
  - 現在500行超のクラスを複数のモジュールに分割
  - `SimulationPhase`、`CombatResolver`、`MovementController`等に分離

- **型ヒントの完全適用**
  ```python
  # mypy による型チェック
  cd backend
  mypy app/ --strict
  ```

- **Docstringの統一**（Google Style）
  ```python
  def calculate_damage(
      attacker: MobileSuit,
      defender: MobileSuit,
      weapon: Weapon
  ) -> int:
      """ダメージを計算する.
      
      Args:
          attacker: 攻撃側の機体
          defender: 防御側の機体
          weapon: 使用武器
      
      Returns:
          計算されたダメージ値
      
      Note:
          装甲と耐性による軽減を考慮する
      """
  ```

##### 7.2 Frontend リファクタリング

- **コンポーネントの細分化**
  ```
  frontend/src/components/
    ├── battle/
    │   ├── BattleViewer.tsx
    │   ├── BattleLog.tsx
    │   ├── TurnSlider.tsx
    │   └── MobileSuitStatus.tsx
    ├── garage/
    │   ├── MobileSuitList.tsx
    │   ├── MobileSuitEditor.tsx
    │   ├── WeaponList.tsx
    │   └── TacticsSelector.tsx
    └── common/
        ├── Button.tsx
        ├── Card.tsx
        └── LoadingSpinner.tsx
  ```

- **カスタムフックの整理**
  ```typescript
  // frontend/src/hooks/useBattle.ts
  export function useBattle() {
    const [isSimulating, setIsSimulating] = useState(false);
    const [battleResult, setBattleResult] = useState<BattleResult | null>(null);
    
    const startBattle = async (missionId: number) => {
      setIsSimulating(true);
      try {
        const result = await simulateBattle(missionId);
        setBattleResult(result);
      } finally {
        setIsSimulating(false);
      }
    };
    
    return { isSimulating, battleResult, startBattle };
  }
  ```

- **共通UIコンポーネントライブラリ化**（shadcn/ui または Tailwind UIの導入検討）

**メリット**:
- コードの可読性向上
- バグの混入リスク低減
- 新機能実装の効率化

---

#### 8. パフォーマンス最適化
**目的**: レスポンス速度の向上とサーバー負荷の軽減。

**作業時間**: 継続的に実施

**実施項目**:

##### 8.1 DBクエリの最適化

- **N+1問題の確認と修正**
  ```python
  # Bad: N+1問題
  battles = session.exec(select(BattleResult)).all()
  for battle in battles:
      pilot = session.get(Pilot, battle.user_id)  # N回クエリ
  
  # Good: JOIN で一括取得
  battles = session.exec(
      select(BattleResult, Pilot)
      .join(Pilot, BattleResult.user_id == Pilot.user_id)
  ).all()
  ```

- **インデックスの追加**
  ```python
  # backend/alembic/versions/xxxxx_add_indexes.py
  op.create_index('idx_battle_results_user_id', 'battle_results', ['user_id'])
  op.create_index('idx_battle_results_created_at', 'battle_results', ['created_at'])
  op.create_index('idx_pilots_user_id', 'pilots', ['user_id'])
  ```

##### 8.2 フロントエンドの最適化

- **バンドルサイズの削減**
  ```bash
  # 不要なライブラリの削除
  npm run build
  npx @next/bundle-analyzer
  ```

- **画像の最適化**（Next.js Image コンポーネントの活用）
  ```tsx
  import Image from 'next/image';
  
  <Image
    src="/images/gundam.png"
    alt="RX-78-2"
    width={200}
    height={200}
    priority
  />
  ```

##### 8.3 3Dレンダリングの最適化

- **LOD (Level of Detail) の実装**
  ```tsx
  // カメラから遠い機体は低ポリゴンで描画
  const distance = camera.position.distanceTo(msPosition);
  const detail = distance < 50 ? 'high' : distance < 100 ? 'medium' : 'low';
  ```

- **インスタンシング**（同じ機体が複数ある場合）
  ```tsx
  import { Instances, Instance } from '@react-three/drei';
  
  <Instances>
    <sphereGeometry />
    <meshStandardMaterial />
    {mobileSuits.map(ms => (
      <Instance key={ms.id} position={ms.position} color={ms.color} />
    ))}
  </Instances>
  ```

**メリット**:
- ページロード時間の短縮
- サーバーコストの削減
- ユーザー体験の向上

---

## 🚀 Quick Win（最も効果的で短時間で実装できるもの）

**推奨**: 「地形適正とリソース状態のUI表示」を最初に実装

**理由**:
- 作業時間: 2-4時間
- バックエンドの変更不要
- ユーザーが「Phase 2.5の高度化」を体感できる
- 他の機能への波及効果が少ない（独立性が高い）

**実装手順**:
1. `frontend/src/app/garage/page.tsx`のステータス表示部分に地形適正セクションを追加
2. リソース情報（EN、推進剤）の表示セクションを追加
3. 武器リストに詳細情報（弾数、EN消費、クールダウン）を追加
4. 色分けやアイコンでわかりやすく表示

**期待効果**:
- ユーザーが「どの機体をどの環境で使うべきか」を判断できるようになる
- Phase 2.5の実装成果が可視化され、達成感が得られる
- ショップで機体購入時の判断材料が増える

---

## 📝 実装の優先順位まとめ

| 優先度 | 項目 | 作業時間 | 効果 |
|--------|------|----------|------|
| 🔴 最優先 | フロントエンドのPhase 2.5対応 | 1-2日 | ユーザー体験向上 |
| 🔴 高 | エントリーシステムの完全実装 | 2-3日 | コア機能完成 |
| 🟡 中 | テストカバレッジの拡充 | 2-3日 | 品質保証 |
| 🟡 中 | デプロイ環境の構築 | 3-5日 | 外部公開可能 |
| 🟢 中低 | NPC永続化システム | 3-4日 | 世界観の深化 |
| 🟢 中低 | ランキングシステムの実装 | 3-4日 | 競争要素追加 |
| 🔵 低 | リファクタリング | 継続的 | 保守性向上 |
| 🔵 低 | パフォーマンス最適化 | 継続的 | UX向上 |

---

## 🎯 推奨ロードマップ（2週間プラン）

### Week 1: ユーザー体験の完成
- **Day 1-2**: フロントエンドのPhase 2.5対応（地形適正、リソース、武器詳細のUI）
- **Day 3-5**: エントリーシステムの完全実装（カウントダウン、バッチスケジュール有効化）
- **Day 6-7**: 動作確認とバグ修正

### Week 2: 品質向上とデプロイ
- **Day 8-10**: テストカバレッジの拡充（Phase 2.5機能の統合テスト、E2Eテスト）
- **Day 11-14**: デプロイ環境の構築（Vercel + Render/Railway）

このロードマップを完了すると：
- Phase 3に移行する準備が整う
- 外部公開可能な品質になる
- ポートフォリオとして使用可能

---

## 📚 関連ドキュメント

- [Project Roadmap](./roadmap.md) - プロジェクト全体のロードマップ
- [Battle Simulation Roadmap](./battle_simulation_roadmap.md) - シミュレーションエンジンの拡張計画
- [ADVANCED_BATTLE_LOGIC_REPORT](../ADVANCED_BATTLE_LOGIC_REPORT.md) - Phase 2.5 実装レポート（武器属性）
- [TERRAIN_DETECTION_IMPLEMENTATION_REPORT](../TERRAIN_DETECTION_IMPLEMENTATION_REPORT.md) - Phase 2.5 実装レポート（地形・索敵）
- [RESOURCE_MANAGEMENT_IMPLEMENTATION](../RESOURCE_MANAGEMENT_IMPLEMENTATION.md) - Phase 2.5 実装レポート（リソース管理）

---

**Last Updated**: 2026年2月9日
