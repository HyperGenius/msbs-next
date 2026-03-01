# ダッシュボード仕様書

## 概要

`frontend/src/app/page.tsx` はアプリケーションのメインダッシュボードページ（エントリーポイント）です。  
バトルエントリー、未読バトル結果の確認、初回オンボーディング、開発用シミュレーションパネルを統合しています。

## 画面構成

```
┌─────────────────────────────────────────────────────────────────┐
│  [BattleResultAnnouncer] WIN / LOSE / DRAW アナウンス（任意表示）   │
├─────────────────────────────────────────────────────────────────┤
│  [RewardPanel] 獲得報酬（経験値・クレジット・レベルアップ）（任意表示） │
├─────────────────────────────────────────────────────────────────┤
│  [BattleViewer] 3D タクティカルモニター（任意表示）                  │
│  [TurnController] ターン操作スライダー / PREV-NEXT ボタン           │
├─────────────────────────────────────────────────────────────────┤
│  [CountdownTimer] 次回バトルまでのカウントダウン                     │
├─────────────────────────────────────────────────────────────────┤
│  [EntryDashboard] ENTRY / 出撃登録セクション                       │
│    - 未ログイン: ログイン案内                                       │
│    - ロード中: スピナー                                             │
│    - ログイン済: エントリー / キャンセル UI                          │
├─────────────────────────────────────────────────────────────────┤
│  [DevSimulationPanel] 即時シミュレーション（開発環境のみ）            │
└─────────────────────────────────────────────────────────────────┘

モーダル（オーバーレイ）:
  - [BattleResultModal]     バトル結果モーダル
  - [EntrySelectionModal]   機体選択モーダル（複数機体保有時）
  - [StarterSelectionModal] スターター機体選択モーダル
  - [OnboardingOverlay]     オンボーディングオーバーレイ
```

## コンポーネント構成

| コンポーネント | ファイル | 役割 |
|---|---|---|
| `BattleResultAnnouncer` | `components/Dashboard/BattleResultAnnouncer.tsx` | WIN/LOSE/DRAWを大きく表示 |
| `RewardPanel` | `components/Dashboard/RewardPanel.tsx` | 経験値・クレジット・レベルアップ表示 |
| `BattleViewer` | `components/BattleViewer/` | 3D タクティカルビューア |
| `TurnController` | `components/Dashboard/TurnController.tsx` | ターン操作スライダー/ボタン |
| `CountdownTimer` | `components/Dashboard/CountdownTimer.tsx` | 次回バトルカウントダウン |
| `EntryDashboard` | `components/Dashboard/EntryDashboard.tsx` | エントリー状況・操作 UI |
| `BattleResultModal` | `components/Dashboard/BattleResultModal.tsx` | バトル結果モーダル |
| `EntrySelectionModal` | `components/Dashboard/EntrySelectionModal.tsx` | 機体選択モーダル |
| `DevSimulationPanel` | `components/Dashboard/DevSimulationPanel.tsx` | 開発用シミュレーションパネル |

## カスタムフック構成

| フック | ファイル | 役割 |
|---|---|---|
| `useOnboarding` | `hooks/useOnboarding.ts` | オンボーディング進行管理・スターター選択・SWR キャッシュ更新 |
| `useBattleSimulation` | `hooks/useBattleSimulation.ts` | 即時バトルシミュレーション状態管理 |
| `useUnreadBattleQueue` | `hooks/useUnreadBattleQueue.ts` | 未読バトル結果キューイングとモーダル表示 |
| `useEntryAction` | `hooks/useEntryAction.ts` | バトルエントリー登録・キャンセル |

## オンボーディングフロー

```
新規ユーザー
  └─ パイロット未作成? → /onboarding へリダイレクト
  └─ 機体 1 機以下 かつ バトル履歴なし かつ localStorage 未完了?
      └─ [OnboardingOverlay] 表示 (startStep=0)
          └─ complete → onboardingState: BATTLE_STARTED
              └─ バトル実行 → バトル結果モーダル表示
                  └─ CONTINUE → onboardingState: BATTLE_FINISHED
                      └─ [OnboardingOverlay] 再表示 (startStep=4)
                          └─ complete → onboardingState: COMPLETED
                              └─ localStorage: msbs_onboarding_completed = "true"
```

## 未読バトル結果フロー

```
ログイン
  └─ unreadBattles を SWR で取得
      └─ 未読あり? → unreadQueue に積む（1 回のみ: unreadShownRef）
          └─ showResultModal=false → キューから 1 件取り出し
              └─ [BattleResultModal] 表示
                  └─ CONTINUE → markBattleAsRead() → 次の未読を処理
```

## 定数

| 定数 | ファイル | 値 |
|---|---|---|
| `ONBOARDING_COMPLETED_KEY` | `constants.ts` | `"msbs_onboarding_completed"` |

## 型定義

| 型 | ファイル | 説明 |
|---|---|---|
| `OnboardingState` | `constants.ts` | `"NOT_STARTED" \| "BATTLE_STARTED" \| "BATTLE_FINISHED" \| "COMPLETED"` |
