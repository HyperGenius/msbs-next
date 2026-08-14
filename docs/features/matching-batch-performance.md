# マッチングバッチのNPC補充パフォーマンス最適化 (Issue #448)

`MatchingService.create_rooms()`（`backend/app/services/matching_service.py`）の
NPC補充処理は、`room_size` を増やすとNeon（チーム共有のリモートDB）へのDBラウンドトリップ数が
線形に増加する実装になっていた。`room_size=50〜100` への引き上げを見据え、ラウンドトリップ回数を
ルーム内のNPC数に依存しない形へ最適化した。

## 変更点

### 1. 永続化NPC取得のN+1解消（`select_npcs_for_room()`）

選択したNPCパイロットごとに `MobileSuit` を個別クエリで取得していた箇所を、
`MobileSuit.user_id.in_(user_ids)` による一括クエリに変更した。
「ランダムにNPCパイロットをサンプリングしてから対応機体を取得する」という選定順序・確率分布は変更していない
（`user_id` ごとに最初の1体を対応付ける点も従来の `.first()` と同じ選定結果になる）。

### 2. 新規NPC生成ループのバルク化（`create_rooms()`）

- `MobileSuit.id` / `Pilot.id` はどちらも `default_factory=uuid.uuid4` でPython側のオブジェクト構築時に
  即時採番される（DBのAUTO INCREMENTに依存しない）ため、IDを得るための `session.flush()` はそもそも不要だった。
- `PilotService.create_npc_pilot()` はNPCパイロット1体ごとに `session.commit()` していたため、
  新規NPC生成数だけコミットが発生していた。DBへの追加なしにPilotレコードを構築するだけの
  `PilotService.build_npc_pilot()` を新設し、`create_rooms()` 側は `session.add()` を積み上げるだけにして、
  ループ終了後に1回の `session.flush()` にまとめた（`create_npc_pilot()` 自体は既存の呼び出し元
  （管理画面・テスト等、即時のDB確定を期待する箇所）向けにそのまま残してある）。
- 既存の永続化NPC再利用ループも同様に、1体ごとの `session.flush()` を廃止した。

## 計測用ベンチマーク（`backend/scripts/matching_scale_bench.py`）

DBを使わないシミュレーションベンチ（`backend/scripts/simulation/sim_scale_bench.py`、Issue #446）とは別に、
in-memory SQLiteでマッチングフェーズのSQL発行回数・処理時間を計測するスクリプトを用意した。
Neonへの実レイテンシは再現できないが、「ルームサイズに対してクエリ発行回数が線形に増えていないか」は確認できる。

```bash
cd backend
source .venv/bin/activate
python scripts/matching_scale_bench.py
# python scripts/matching_scale_bench.py --sizes 8,50,100 --player-count 1
```

### 最適化後の計測結果例（in-memory SQLite）

| room_size | SQL発行回数 | 処理時間(sec) |
|---|---|---|
| 8 | 10 | 0.0075 |
| 50 | 10 | 0.0175 |
| 100 | 10 | 0.0302 |

`room_size` を8→100に引き上げてもSQL発行回数は一定（10クエリ）のまま。最適化前の実装では
NPC1体ごとに「一括取得できない個別クエリ」「機体flush」「NPCパイロットの個別commit」が発生していたため、
NPC数に比例してクエリ数が増加していた。

## デフォルト定員の引き上げ

上記の検証結果を踏まえ、`MatchingService.room_size` のデフォルト値を8機から50機へ引き上げた。
`backend/scripts/run_batch.py` の `_save_battle_results`（デイリーバトルロイヤル用バッチ、
`.github/workflows/scheduled-battle.yaml` から定期実行）は `MatchingService(session)` とデフォルト引数で
呼んでいるため、本番の定員はこの変更により実際に50機へ引き上がる。
