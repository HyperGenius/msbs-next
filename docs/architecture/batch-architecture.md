# バッチシステムアーキテクチャ図

```
┌─────────────────────────────────────────────────────────────────────┐
│                     GitHub Actions (Scheduler)                      │
│                                                                     │
│  Trigger: Cron (JST 21:00) or Manual                              │
│  Workflow: .github/workflows/scheduled-battle.yaml                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ Execute
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Batch Script (run_batch.py)                       │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │  Phase 1: Matching                                        │    │
│  │  ┌────────────────────────────────────────────────────┐   │    │
│  │  │  MatchingService.create_rooms()                    │   │    │
│  │  │  - Find OPEN BattleRooms                          │   │    │
│  │  │  - Fill with NPCs (up to 8 units)                 │   │    │
│  │  │  - Update status to WAITING                        │   │    │
│  │  └────────────────────────────────────────────────────┘   │    │
│  └───────────────────────────────────────────────────────────┘    │
│                             │                                       │
│                             ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │  Phase 2: Simulation                                      │    │
│  │  ┌────────────────────────────────────────────────────┐   │    │
│  │  │  For each WAITING room:                           │   │    │
│  │  │  - Restore MobileSuits from snapshots             │   │    │
│  │  │  - Run BattleSimulator                            │   │    │
│  │  │  - Save BattleResults                             │   │    │
│  │  │  - Update room status to COMPLETED                │   │    │
│  │  └────────────────────────────────────────────────────┘   │    │
│  └───────────────────────────────────────────────────────────┘    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ Writes to
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Database (PostgreSQL)                        │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ BattleRooms  │  │ BattleEntry  │  │ MobileSuits  │            │
│  │              │  │              │  │              │            │
│  │ - OPEN       │  │ - user_id    │  │ - Snapshots  │            │
│  │ - WAITING    │  │ - is_npc     │  │              │            │
│  │ - COMPLETED  │  │ - snapshot   │  │              │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
│                             │                                       │
│                             ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │                   BattleResults                           │     │
│  │                                                           │     │
│  │  - user_id                                               │     │
│  │  - room_id                                               │     │
│  │  - win_loss                                              │     │
│  │  - logs (JSON)                                           │     │
│  └──────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             │ Read by
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                             │
│                                                                     │
│  Users can view:                                                   │
│  - Battle history                                                  │
│  - Results and logs                                                │
│  - Win/Loss statistics                                             │
└─────────────────────────────────────────────────────────────────────┘
```

## データフロー

### 1. エントリーフェーズ（ユーザー操作）
```
User → API → BattleEntry (status: pending)
            ↓
        BattleRoom (status: OPEN)
```

### 2. マッチングフェーズ（バッチ処理）
```
OPEN BattleRoom → MatchingService → Check player count
                                    ↓
                                Generate NPCs if needed
                                    ↓
                                Update to WAITING
```

### 3. シミュレーションフェーズ（バッチ処理）
```
WAITING BattleRoom → Load snapshots → BattleSimulator → Results
                                                         ↓
                                                    BattleResults
                                                         ↓
                                                    Status: COMPLETED
```

### 4. 閲覧フェーズ（ユーザー操作）
```
User → API → BattleResults → Display logs and outcome
```

## コンポーネント間の関係

```
┌─────────────────────┐
│  MatchingService    │
│  - NPC Generation   │
│  - Room Management  │
└──────────┬──────────┘
           │ uses
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│  BattleSimulator    │◄────│  run_batch.py       │
│  - Combat Logic     │     │  - Orchestration    │
│  - Turn Processing  │     │  - Error Handling   │
└─────────────────────┘     └─────────────────────┘
           │
           │ generates
           ▼
┌─────────────────────┐
│  BattleLog          │
│  - Action records   │
│  - Turn-by-turn     │
└─────────────────────┘
```

## エラーハンドリング

```
run_batch.py
    │
    ├── try: Room 1
    │   ├── Success → Save results
    │   └── Error → Log & Continue
    │
    ├── try: Room 2
    │   ├── Success → Save results
    │   └── Error → Log & Continue
    │
    └── try: Room N
        ├── Success → Save results
        └── Error → Log & Continue
```

## スケーリング考慮事項

### 現在の実装
- シーケンシャル処理（1ルームずつ）
- 単一プロセス

### 将来の拡張
- 並列処理（複数ルームを同時に処理）
- ワーカープール
- キューイングシステム
- 分散処理
