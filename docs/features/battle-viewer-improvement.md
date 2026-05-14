# バトルヒストリー詳細ページ 改善方針

## 概要

バトルヒストリー詳細モーダル（`BattleDetailModal`）のUX・リアリティ改善計画。  
現状は PREV/NEXT ボタンによる手動シーク、全ログ一括表示、全MS可視化という状態であり、  
以下の5つの観点から改善を行う。

---

## 改善項目一覧

| # | カテゴリ | タイトル | 優先度 |
|---|---------|---------|--------|
| 1 | TurnController | 再生・停止・一時停止ボタンへの置き換え | High |
| 2 | BattleLog (本番) | 自機フォーカスログ表示 | High |
| 3 | BattleLog (本番) | 近距離ログのみ表示（リアリティ向上） | Medium |
| 4 | BattleLog (本番) | 開発用ログの本番非表示 | High |
| 5 | BattleViewer (本番) | 未索敵MSの非表示 | High |
| 6 | BattleViewer | 自機向き・ターゲット方向の可視化 | Medium |
| 7 | BattleViewer | 攻撃エフェクト（武器・命中結果の表示） | Medium |
| 8 | BattleViewer | 障害物の3D表示 | High |
| 9 | BattleViewer | LOS遮断の可視化 | Medium |
| B | バグ修正 | 格闘ダメージ表示が消えない問題 | High |

---

## 詳細方針

### 1. TurnController — 再生・停止・一時停止ボタン

**現状:** `< PREV` / `NEXT >` ボタンを 0.1s ステップで手動クリックする必要がある。

**方針:**
- `useInterval` ベースの自動再生ロジックを `TurnController` に追加
- 再生中: `currentTimestamp` を一定間隔（例: 100ms ごとに 0.1s 進める）で自動更新
- ボタン構成: ▶ 再生 / ⏸ 一時停止 / ⏹ 停止（先頭へ戻す）
- シークバーは引き続き手動操作可能
- 再生速度変更ボタン（0.5x / 1x / 2x）もオプションとして追加検討

**影響ファイル:**
- `frontend/src/components/history/TurnController.tsx`

---

### 2. バトルログ本番表示 — 自機フォーカス

**現状:** `filterRelevantLogs` で一定のフィルタは存在するが、本番環境での表示粒度が粗い。

**方針:**
- 自機（`ownedMobileSuitIds`）の行動ログを最優先表示
- 敵MSのログは「自機が索敵済みの敵」かつ「自機に影響する行動」のみ表示
  - 例: 自機への攻撃、自機が観測できる爆発など
- 索敵外のMSのログは本番環境では完全に非表示

**影響ファイル:**
- `frontend/src/utils/logFormatter.ts`
- `frontend/src/hooks/useBattleLogic.ts`

---

### 3. バトルログ本番表示 — 近距離ログのみ表示

**現状:** 遠方のMSの行動もすべてログに出るため、プレイヤーが知り得ないはずの情報が表示される。

**方針:**
- 本番環境では、自機から一定距離（例: センサー範囲内）の敵の行動のみ表示
- センサー範囲外の敵の行動ログは非表示
- 索敵フェーズ実装（Phase 6-4: 確率的索敵）との連携が前提になる場合は、  
  `detected_units` の状態をログに持たせることで対応

**影響ファイル:**
- `frontend/src/hooks/useBattleLogic.ts`
- `backend/app/engine/` (将来的にログへの索敵状態付与)

---

### 4. バトルログ本番表示 — 開発用ログの非表示

**現状:** 「ファジィ推論」「優先度スコア」などのデバッグ情報が本番ログに表示されている。

**方針:**
- `formatBattleLog` 内または `filterRelevantLogs` で、本番環境時にメッセージパターンマッチで除外
- 除外対象パターン: `ファジィ推論`, `優先度スコア`, `UNKNOWN機`, `[FUZZY]` など
- すでに `IS_PRODUCTION` フラグが存在するため、これを活用して条件分岐

**影響ファイル:**
- `frontend/src/utils/logFormatter.ts`
- `frontend/src/hooks/useBattleLogic.ts`

---

### 5. BattleViewer 本番表示 — 未索敵MSの非表示

**現状:** 全敵MSが開幕から3Dビューアに表示され、HPゲージも見える。

**方針:**
- 自機の索敵状態（バトルログの `DETECT` アクション等）に基づいて、  
  各タイムスタンプ時点で自機が索敵済みの敵MSのみを `BattleScene` に渡す
- 未索敵の敵MSは球体オブジェクト・HPゲージともに非表示
- `getBattleSnapshot` の拡張として「発見済みユニットセット」を管理するロジックを追加
- 本番/開発フラグ (`IS_PRODUCTION`) で切り替え可能にする

**影響ファイル:**
- `frontend/src/components/BattleViewer/index.tsx`
- `frontend/src/components/BattleViewer/hooks/useBattleSnapshot.ts`
- `frontend/src/components/BattleViewer/scene/BattleScene.tsx`

---

### 6. BattleViewer — 自機向き・ターゲット方向の可視化

**現状:** 自機MSは球体で表示されているのみ。向きやターゲット方向は不明。

**方針:**
- 自機の向きを示す矢印（`THREE.ArrowHelper` または cone mesh）を球体に付与
- 現在のターゲット（`target_id`）に向けた細い線（`THREE.Line`）を描画
- ターゲットMSの球体をハイライト表示（発光強化・リング追加）
- 向き情報はバトルログの `heading` フィールドから取得

**影響ファイル:**
- `frontend/src/components/BattleViewer/scene/MobileSuitMesh.tsx`
- `frontend/src/components/BattleViewer/scene/BattleScene.tsx`
- `frontend/src/components/BattleViewer/hooks/useBattleSnapshot.ts`

---

### 7. BattleViewer — 攻撃エフェクト（武器・命中結果）

**現状:** 攻撃結果はダメージ数値の一時表示のみ。どの武器で攻撃したか、命中したかが不明。

**方針:**
- 自機→ターゲット間に攻撃ラインを一時表示（色: 命中=黄、ミス=グレー）
- 命中時: ターゲット位置に爆発エフェクト（`💥` + グロウエフェクト）
- ミス時: 点線 or 波線で表現
- 武器名は `BattleEventDisplay` のテキストに追加
- バトルログの `weapon_id`, `hit` フィールドを活用

**影響ファイル:**
- `frontend/src/components/BattleViewer/scene/BattleEventDisplay.tsx`
- `frontend/src/components/BattleViewer/hooks/useBattleEvents.ts`
- `frontend/src/components/BattleViewer/scene/BattleScene.tsx`

---

### 8. BattleViewer — 障害物の3D表示

**現状:** フィールド上に障害物（`Obstacle`）が存在するが、3Dビューアには一切描画されていない。  
障害物は `radius` と `height` を持つ円柱形オブジェクトとしてシミュレーション内で機能している。

**課題:**
- `BattleResult` に `obstacles_info` フィールドが存在しない（シミュレーション時のみ生成され保存されない）
- フロントエンド側に `Obstacle` 型が未定義

**方針:**
- **Backend**: `BattleResult` に `obstacles_info: list[dict] | None` JSON カラムを追加し、  
  バトル結果保存時に `simulator.obstacles` をシリアライズして格納
- **Frontend types**: `Obstacle` 型（`obstacle_id`, `position`, `radius`, `height`）を `battle.ts` に追加し、  
  `BattleResult` に `obstacles_info?: Obstacle[]` を追加
- **BattleViewer**: `obstacles` プロパティを受け取り、`BattleScene` で `THREE.CylinderGeometry` で描画
  - 見た目: 半透明グレー/茶色の円柱（ `opacity: 0.7`）
  - `scale` 係数は既存の MS 座標スケール（`0.05`）と合わせる

**影響ファイル:**
- `backend/app/models/models.py`（`BattleResult` カラム追加）
- `backend/app/services/` または `routers/`（obstacles_info 保存処理）
- `backend/alembic/versions/`（マイグレーション追加）
- `frontend/src/types/battle.ts`
- `frontend/src/components/BattleViewer/index.tsx`
- `frontend/src/components/BattleViewer/scene/BattleScene.tsx`
- `frontend/src/components/BattleViewer/scene/ObstacleMesh.tsx`（新規）
- `frontend/src/components/history/BattleDetailModal.tsx`

---

### 9. BattleViewer — LOS遮断の可視化

**現状:** 障害物による LOS（Line of Sight）カットはシミュレーション内では機能しているが、  
ビューア上でプレイヤーは「なぜ攻撃できなかったのか」を視覚的に確認できない。

**方針:**
- 各タイムスタンプで自機から各敵MSへの視線ラインを描画
  - **LOS あり（視線が通っている）**: 緑の細線（薄いグロウ付き）
  - **LOS なし（障害物で遮断）**: 赤の破線。どの障害物で遮断されているかをハイライト
- LOS 計算は `has_los` と同じ Ray-Sphere 交差判定をフロントエンドで再実装（TypeScript）
- 常時表示は視認性が悪いため、トグルボタン（「LOS表示: ON/OFF」）で切り替え可能にする
- 遮断している障害物を一時的に強調表示（赤くなる）

**LOS計算のフロントエンド実装:**
```typescript
function hasLos(
    posA: { x: number; y: number; z: number },
    posB: { x: number; y: number; z: number },
    obstacles: Obstacle[]
): boolean {
    // Ray-Sphere 交差判定（Python版 has_los と同じアルゴリズム）
    const dir = { x: posB.x - posA.x, y: posB.y - posA.y, z: posB.z - posA.z };
    const dist = Math.sqrt(dir.x**2 + dir.y**2 + dir.z**2);
    if (dist < 1e-6) return true;
    const ud = { x: dir.x/dist, y: dir.y/dist, z: dir.z/dist };
    for (const obs of obstacles) {
        const oc = { x: posA.x - obs.position.x, y: posA.y - obs.position.y, z: posA.z - obs.position.z };
        const b = 2.0 * (oc.x*ud.x + oc.y*ud.y + oc.z*ud.z);
        const c = (oc.x**2 + oc.y**2 + oc.z**2) - obs.radius**2;
        const discriminant = b**2 - 4.0 * c;
        if (discriminant < 0) continue;
        const t = (-b - Math.sqrt(discriminant)) / 2.0;
        if (t > 0.0 && t < dist) return false;
    }
    return true;
}
```

**影響ファイル:**
- `frontend/src/components/BattleViewer/scene/BattleScene.tsx`
- `frontend/src/components/BattleViewer/utils/losUtils.ts`（新規）
- `frontend/src/components/BattleViewer/index.tsx`

---

### B. バグ修正 — 格闘攻撃ダメージ表示が消えない

**現状:** 格闘攻撃（`MELEE` 系）のダメージ表示が `animate-bounce` で表示されたままになる。

**原因調査ポイント:**
- `BattleEventDisplay.tsx` の表示ロジック
- `useBattleEvents.ts` での格闘攻撃イベントのタイムアウト処理
- 格闘攻撃は `action_type` が通常攻撃と異なる可能性あり

**方針:**
- `useBattleEvents` にて格闘攻撃のイベント消去ロジックを確認・修正
- 表示時間を統一（例: 0.3s 以内に自動消去）

**影響ファイル:**
- `frontend/src/components/BattleViewer/hooks/useBattleEvents.ts`
- `frontend/src/components/BattleViewer/scene/BattleEventDisplay.tsx`

---

## 実装優先度

```
Phase 1（即効性・ユーザー体験）
  B. バグ修正: 格闘ダメージ表示が消えない
  1. TurnController: 再生ボタン実装
  4. 開発用ログの本番非表示

Phase 2（リアリティ向上）
  8. 障害物の3D表示（Backend + Frontend）
  5. 未索敵MSの非表示
  2. 自機フォーカスログ
  3. 近距離ログのみ表示

Phase 3（ビジュアル強化）
  9. LOS遮断の可視化
  6. 自機向き・ターゲット方向の可視化
  7. 攻撃エフェクト（武器・命中結果）
```

---

## 関連ファイル一覧

| ファイル | 役割 |
|---------|------|
| `frontend/src/components/history/BattleDetailModal.tsx` | モーダル全体 |
| `frontend/src/components/history/TurnController.tsx` | タイムライン操作 |
| `frontend/src/components/history/BattleLogViewer.tsx` | ログ表示 |
| `frontend/src/components/BattleViewer/index.tsx` | 3Dビューア |
| `frontend/src/components/BattleViewer/scene/BattleScene.tsx` | Three.jsシーン |
| `frontend/src/components/BattleViewer/scene/MobileSuitMesh.tsx` | MS球体描画 |
| `frontend/src/components/BattleViewer/scene/ObstacleMesh.tsx` | 障害物描画（新規） |
| `frontend/src/components/BattleViewer/scene/BattleEventDisplay.tsx` | イベントエフェクト |
| `frontend/src/components/BattleViewer/hooks/useBattleSnapshot.ts` | 状態スナップショット |
| `frontend/src/components/BattleViewer/hooks/useBattleEvents.ts` | イベント管理 |
| `frontend/src/components/BattleViewer/utils/losUtils.ts` | LOS計算ユーティリティ（新規） |
| `frontend/src/utils/logFormatter.ts` | ログ整形 |
| `frontend/src/hooks/useBattleLogic.ts` | ログフィルタロジック |
| `backend/app/models/models.py` | DBモデル（obstacles_info追加） |
| `backend/alembic/versions/` | DBマイグレーション |
