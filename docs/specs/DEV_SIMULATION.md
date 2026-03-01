# 開発用シミュレーションパネル仕様書

## 概要

`DevSimulationPanel` は **開発環境 (`NODE_ENV === "development"`) でのみ表示される** 即時バトルシミュレーション機能です。  
本番環境では完全に非表示となり、エンドユーザーには影響を与えません。

## ファイル

- コンポーネント: `frontend/src/components/Dashboard/DevSimulationPanel.tsx`
- ロジック: `frontend/src/hooks/useBattleSimulation.ts`

## 機能

### ミッション選択

- バックエンドの `/api/missions` から取得したミッション一覧を表示
- ミッションカードをクリックで選択（ハイライト表示）
- 各カードに表示する情報:
  - ミッション名
  - 難易度（数値）
  - 説明文
  - 敵機数
  - 環境（SPACE / 地上など）

### シミュレーション実行

- 「即時シミュレーション実行」ボタンをクリックでシミュレーション開始
- 実行中は `CALCULATING...` と表示されボタン無効化
- バックエンド API: `POST /api/battle/simulate?mission_id={id}`

### 実行結果表示

バトル完了後、以下の情報が更新される:

| 要素 | 表示場所 |
|---|---|
| PLAYER / ENEMIES 情報 | パネル内コントロールエリア |
| WIN / LOSE / DRAW | `BattleResultAnnouncer` コンポーネント |
| 経験値・クレジット報酬 | `RewardPanel` コンポーネント |
| バトル結果モーダル | `BattleResultModal` |
| 3D タクティカルビュー | `BattleViewer` コンポーネント |

### テキストログ

- ターン別のバトルログをリスト表示
- 現在選択中のターンはハイライト表示
- ログのスタイルはアクションタイプに応じて色分け:

| 種別 | 色 |
|---|---|
| 現在ターン | 緑（白文字） |
| リソース関連（弾切れ・EN 不足など） | オレンジ |
| 地形・索敵関連 | シアン |
| 属性関連（BEAM / PHYSICAL） | パープル |
| 通常 | 暗い緑 |

- バトル終了時には `WINNER` アナウンスをリスト末尾に表示

## `useBattleSimulation` フックの API

```ts
const {
  logs,            // BattleLog[] - テキストログ
  isLoading,       // boolean - ローディング状態
  winner,          // string | null - 勝者 ID
  winLoss,         // "WIN" | "LOSE" | "DRAW" | null - 勝敗
  currentTurn,     // number - 現在のターン
  setCurrentTurn,  // (turn: number) => void - ターン変更
  maxTurn,         // number - 最大ターン
  selectedMissionId,    // number - 選択中ミッション ID
  setSelectedMissionId, // (id: number) => void
  playerData,      // MobileSuit | null - プレイヤー機体情報
  enemiesData,     // MobileSuit[] - 敵機体情報
  rewards,         // BattleRewards | null - 報酬情報
  currentEnvironment,  // string - 戦場環境
  startBattle,     // (missionId: number) => Promise<void>
} = useBattleSimulation({ getToken, missions, mutatePilot, setModalResult, setShowResultModal });
```

## バックエンド API

### `POST /api/battle/simulate?mission_id={id}`

**リクエストヘッダー:**

```
Authorization: Bearer <token>  (ログイン済みの場合)
Content-Type: application/json
```

**レスポンス例:**

```json
{
  "winner_id": "player-uuid-or-ENEMY",
  "logs": [
    {
      "turn": 1,
      "actor_id": "uuid",
      "action_type": "ATTACK",
      "target_id": "uuid",
      "damage": 150,
      "message": "ザクII がビームライフルで攻撃した",
      "position_snapshot": { "x": 0, "y": 0, "z": 0 }
    }
  ],
  "player_info": { /* MobileSuit */ },
  "enemies_info": [ /* MobileSuit[] */ ],
  "rewards": {
    "exp_gained": 100,
    "credits_gained": 500,
    "level_before": 3,
    "level_after": 4,
    "total_exp": 1200,
    "total_credits": 3000
  }
}
```

## 注意事項

- 本機能は開発・デバッグ目的のみで提供されています
- 実際のゲームバトル（定期バッチ実行）とは独立した機能です
- シミュレーション結果はパイロットの経験値・クレジットに反映されます（`mutatePilot()` 呼び出し）
