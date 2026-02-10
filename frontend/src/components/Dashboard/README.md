# Dashboard Components

このディレクトリには、ゲームサイクル体験を向上させるためのダッシュボードコンポーネントが含まれています。

## Components

### CountdownTimer.tsx
次回バトルまでのカウントダウンタイマーを表示するコンポーネント。

**機能:**
- JST 21:00 (UTC 12:00) までの残り時間を表示
- 1秒ごとに自動更新
- 時間到達時に「集計中...」のステータスを表示

**Props:**
- `targetTime: Date | null` - カウントダウンの目標時刻

### EntryDashboard.tsx
エントリー状況を表示し、エントリー/キャンセル操作を行うダッシュボードコンポーネント。

**機能:**
- 未エントリー時: エントリーボタンと参加者数の表示
- エントリー済み時: 確認ステータス、使用機体情報、キャンセルボタンの表示
- リアルタイムの参加者数表示（10秒ごとに自動更新）

**Props:**
- `isEntered: boolean` - エントリー済みかどうか
- `entryCount: number` - 現在の参加者数
- `mobileSuit?: MobileSuit` - エントリーに使用する機体情報
- `onEntry: () => void` - エントリーボタンクリック時のハンドラ
- `onCancel: () => void` - キャンセルボタンクリック時のハンドラ
- `isLoading: boolean` - ローディング状態
- `disabled?: boolean` - ボタンの無効化状態

### BattleResultModal.tsx
バトル結果を表示するモーダルコンポーネント。

**機能:**
- WIN/LOSE/DRAW の結果に応じた視覚的演出
- 獲得経験値とクレジットのカウントアップアニメーション
- レベルアップ時の特別表示
- フェードインアニメーション

**Props:**
- `winLoss: "WIN" | "LOSE" | "DRAW"` - バトル結果
- `rewards: BattleRewards | null` - 報酬情報
- `onClose: () => void` - モーダルを閉じる時のハンドラ

## Usage

```tsx
import CountdownTimer from "@/components/Dashboard/CountdownTimer";
import EntryDashboard from "@/components/Dashboard/EntryDashboard";
import BattleResultModal from "@/components/Dashboard/BattleResultModal";

// CountdownTimer
<CountdownTimer targetTime={new Date("2024-01-01T12:00:00Z")} />

// EntryDashboard
<EntryDashboard
  isEntered={false}
  entryCount={42}
  onEntry={() => console.log("Entry")}
  onCancel={() => console.log("Cancel")}
  isLoading={false}
/>

// BattleResultModal
<BattleResultModal
  winLoss="WIN"
  rewards={rewardsData}
  onClose={() => console.log("Close")}
/>
```

## API Integration

これらのコンポーネントは以下のAPIエンドポイントと連携します:

- `GET /api/entries/status` - エントリー状況の取得
- `GET /api/entries/count` - 参加者数の取得（10秒ごとに自動更新）
- `POST /api/entries` - エントリーの作成
- `DELETE /api/entries` - エントリーのキャンセル
