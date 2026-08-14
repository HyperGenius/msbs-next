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

## `relationship()` 未定義によるINSERT順序の不定性（Issue #461）

上記の「新規NPC生成ループのバルク化」で、新規 `MobileSuit`/`Pilot`/`BattleEntry` を1回の
`session.flush()` にまとめた際、`BattleEntry.mobile_suit_id` が参照する `MobileSuit` より
先に `BattleEntry` がINSERTされ `battle_entries_mobile_suit_id_fkey` 違反になる不具合が
本番で発生した（room_sizeを8→50へ引き上げた直後に顕在化）。

`backend/app/models/models.py` では `MobileSuit`/`Pilot`/`BattleEntry` 間に SQLModel/SQLAlchemy の
`relationship()` を一切定義しておらず、`Field(foreign_key=...)` によるスキーマレベルのFK制約しか
持たない。**`relationship()` が無い場合、SQLAlchemyのflushは複数テーブルへのINSERT順序を
`session.add()` した順序や実際のFK依存関係に基づいては決定しない**（同一クラスのオブジェクトを
まとめてバルクINSERTする際のテーブル間の順序は事実上不定）。add()した順に親→子で並べていても
子テーブルのINSERTが先に発行されるケースを再現テスト（`sqlite3` + `PRAGMA foreign_keys=ON`）で
確認済み。本ベンチスクリプト（in-memory SQLite、既定でFK制約を有効化していない）はSQL発行回数の
計測が目的で、この順序不定性を検出できていなかった。

対策として、新規NPC生成ループを「`MobileSuit`/`Pilot` の生成・add・flush」→「その結果を使った
`BattleEntry` の生成・add」の2段階に分割し、`BattleEntry` がINSERTされる前に参照先の
`MobileSuit` が確実にDBへ反映されるようにした。ラウンドトリップは1回増える（NPC生成が発生する
ルームにつき2回のflush）が、`room_size` に比例して増えるものではないため、Issue #448 で狙った
「NPC数に依存しないラウンドトリップ数」という性質自体は維持している。

**今後 `MobileSuit`/`Pilot`/`BattleEntry` のような「新規作成した親を新規作成した子が同一flush内で
参照する」パターンを書く際は、`relationship()` を定義しない限りテーブル間のINSERT順序を
SQLAlchemyに委ねてはいけない**。親をflushしてIDをDBへ確定させてから子を作成するか、
`relationship()` を定義してORMに依存関係を教えるかのいずれかが必要。
