# BattleViewer 仕様書

## 概要

`BattleViewer` はバトルヒストリー詳細モーダル内で使用される 3D リプレイビューアコンポーネントです。  
バトルログを時系列に沿って再生し、モビルスーツの動きや戦闘結果をリアルタイムで可視化します。

---

## コンポーネント構成

```
BattleDetailModal
├── BattleViewer               # 3D リプレイビューア本体
└── TurnController             # 再生コントローラー（タイムライン操作）
    └── シークバー + 再生/一時停止/停止ボタン
```

---

## TurnController

### 概要

`TurnController` は `currentTimestamp` を操作するUIコンポーネントです。  
自動再生・一時停止・停止・手動シークをサポートします。

### ファイル

`frontend/src/components/history/TurnController.tsx`

### Props

| Prop | 型 | 説明 |
|------|----|------|
| `currentTimestamp` | `number` | 現在の再生位置（秒） |
| `maxTimestamp` | `number` | 最大タイムスタンプ（秒） |
| `onTimestampChange` | `(timestamp: number) => void` | タイムスタンプ変更コールバック |

### ボタン構成

| ボタン | アイコン | 動作 |
|-------|---------|------|
| 停止 | ⏹ | 再生を停止し、`currentTimestamp` を 0 にリセット |
| 再生 / 一時停止 | ▶ / ⏸ | 自動再生の開始・一時停止をトグル |

- 再生中は ▶ を ⏸ に切り替えて表示（トグルボタン）
- 最終タイムスタンプに達したら自動停止

### 自動再生ロジック

- 実時間 **100ms ごとに `currentTimestamp` を +0.1s** 進める（1倍速）
- `useEffect` + `setInterval` で実装
- `isPlaying` ステートで再生状態を管理
- `currentTimestamp >= maxTimestamp` になったら `isPlaying = false` に自動セット

### シークバー

- 手動ドラッグによるシーク可能
- ドラッグ開始時に自動再生を一時停止

### UI レイアウト

```
[ ⏹ ] [ ▶ / ⏸ ]  [========●============]  Start  Time: 5.0s / 39.2s  End
```

- ボタンは `bg-green-900 hover:bg-green-800` スタイル
- シークバーは `accent-green-500`

---

## BattleViewer

### 概要

Three.js（`@react-three/fiber`）を使用した 3D バトルリプレイビューアです。

### ファイル

`frontend/src/components/BattleViewer/index.tsx`

### Props

| Prop | 型 | 説明 |
|------|----|------|
| `logs` | `BattleLog[]` | バトルログ配列 |
| `player` | `MobileSuit` | プレイヤー機体情報 |
| `enemies` | `MobileSuit[]` | 敵機体情報配列 |
| `obstacles` | `Obstacle[]` (optional) | フィールド障害物配列 |
| `currentTimestamp` | `number` | 現在の再生タイムスタンプ |
| `environment` | `string` | 環境（`"SPACE"` 等） |

### 内部フック

| フック | 役割 |
|--------|------|
| `useBattleSnapshot` | タイムスタンプに対応するスナップショット取得 |
| `useBattleEvents` | 攻撃・ダメージイベントの管理 |

### 索敵による表示制御（本番環境）

本番環境（`IS_PRODUCTION === true`）では、プレイヤーが索敵していない敵MSをビューアに表示しません。

#### `getDetectedUnits` ユーティリティ関数

`frontend/src/components/BattleViewer/hooks/useBattleSnapshot.ts` に定義。

```typescript
function getDetectedUnits(
    playerId: string,
    logs: BattleLog[],
    currentTimestamp: number
): Set<string>
```

- バトルログを走査し、`action_type === "DETECTION"` かつ `actor_id === playerId` のエントリから `target_id` を収集
- 索敵は永続的（一度発見した敵MSは以降のタイムスタンプでも表示し続ける）
- 戻り値: 索敵済み敵MS の ID セット（`Set<string>`）

#### フィルタ適用フロー

```
BattleViewer
  → getDetectedUnits(player.id, logs, currentTimestamp)
  → enemyStates.filter(enemy => detectedIds.has(enemy.id))  ← IS_PRODUCTION 時のみ
  → visibleEnemyStates を BattleScene / BattleOverlay に渡す
```

- 開発環境では全 MS を表示（従来動作を維持）
- 未索敵敵 MS は 3D シーン（球体オブジェクト）にもHPゲージにも表示されない

---

## 関連ファイル一覧

| ファイル | 役割 |
|---------|------|
| `frontend/src/components/history/BattleDetailModal.tsx` | モーダル全体 |
| `frontend/src/components/history/TurnController.tsx` | タイムライン操作コントローラー |
| `frontend/src/components/history/BattleLogViewer.tsx` | バトルログ表示 |
| `frontend/src/components/BattleViewer/index.tsx` | 3D リプレイビューア |
| `frontend/src/components/BattleViewer/scene/BattleScene.tsx` | Three.js シーン |
| `frontend/src/components/BattleViewer/scene/MobileSuitMesh.tsx` | MS 球体描画 |
| `frontend/src/components/BattleViewer/scene/ObstacleMesh.tsx` | 障害物円柱描画 |
| `frontend/src/components/BattleViewer/scene/BattleEventDisplay.tsx` | イベントエフェクト表示 |
| `frontend/src/components/BattleViewer/hooks/useBattleSnapshot.ts` | 状態スナップショット管理 |
| `frontend/src/components/BattleViewer/hooks/useBattleEvents.ts` | イベント管理 |

---

## 障害物（Obstacle）の3D表示

### 概要

バトルシミュレーターが生成する障害物（`Obstacle`）をフィールド上に半透明円柱として描画します。

### `ObstacleMesh` コンポーネント

`frontend/src/components/BattleViewer/scene/ObstacleMesh.tsx`

| プロパティ | 内容 |
|-----------|------|
| 形状 | `CylinderGeometry`（上下同径の円柱） |
| 色 | SPACE: `#5a4a3a` / GROUND: `#4a5a4a` |
| 透明度 | `opacity: 0.75` |
| スケール | `0.05`（既存 MS 座標スケールと統一） |
| Y オフセット | 円柱の底面をグリッド面（y=0）に合わせるため `y + h/2` |

### データフロー

```
BattleResult.obstacles_info (DB)
  → BattleDetailModal (obstacles_info を BattleViewer に渡す)
  → BattleViewer (obstacles prop)
  → BattleScene (obstacles prop)
  → ObstacleMesh (各障害物を個別描画)
```

### 注意事項

- `obstacles_info` が `null` / `undefined` の場合は何も描画しない（既存バトル履歴への後方互換性）
- バックエンドで障害物が生成されない設定（`obstacle_density: "NONE"` など）では `obstacles_info` は `null` として保存される

