# バトルエンジン変更時のCIスモークテスト

`backend/app/engine/**` を変更したPRで、mainへのマージ前に実際に `BattleSimulator` を
完走させて例外・決着不能を検出するCIステップを追加した。

## 経緯

Cloud Run Jobs のマッチングバッチ実行が実際に失敗した際（`battle_entries_mobile_suit_id_fkey`
違反、別件）の対応の中で、「エンジン変更をmainへマージする前に、実際にシミュレーションを
走らせて確認できるとよい」という提案が出た。Cloud Run上で実行するアプローチも検討したが、
以下の理由からローカル完結（DB・GCP不使用）の方針を採用した。

- `NEON_DATABASE_URL` はチーム共有の本番Neon DBを指しており（`backend/CLAUDE.md`参照）、
  PRごとのCIから共有DBに接続するのは事故リスクが大きい
- Cloud Run実行にはGCPサービスアカウント鍵をCIに持ち込む必要があり、権限管理のコストが増える
- `backend/scripts/simulation/sim_scale_bench.py`（Issue #446）のように、このエンジンは
  合成ユニットを使えばDB不要で完結するシミュレーションが既に可能

## 実装

### `backend/scripts/simulation/engine_ci_smoke.py`

`sim_scale_bench.py` の `_build_units()`（合成ユニットビルダー）を再利用し、複数サイズ
（デフォルト: 2/8/20機）× 複数ラウンド（デフォルト: 3回）で `BattleSimulator` を完走まで
実行する。DB・外部APIには一切接続しない。

失敗条件（exit code 1）:
- いずれかのラウンドで例外が発生した場合
- 全ラウンドが `--max-steps`（デフォルト2000、200秒相当）に到達し、1件も決着しなかった場合
  （エンジンが根本的に壊れているsignal。個別ラウンドの長期化・引き分けは正常な揺らぎとして許容する）

**このエンジンには現状シード固定による再現性が無い**（`app/engine/combat.py` 等の命中判定・
ターゲット選定処理が `random`/`np.random.default_rng()` を非シード化のまま使っている）。
そのため「同一シードで再現する」のではなく「同一構成をNラウンド繰り返して揺らぎを吸収する」
方式を取っている。ユニット配置のみ `_build_units()` 内部の固定シード(42)で決定的。

ローカル実行:

```bash
cd backend
python scripts/simulation/engine_ci_smoke.py
python scripts/simulation/engine_ci_smoke.py --sizes 2,8,20 --rounds 5
```

### `.github/workflows/backend-ci.yaml`

`dorny/paths-filter@v3` で `backend/app/engine/**` の変更有無を検出し、変更があった場合のみ
`engine_ci_smoke.py` を実行するステップを `test` ジョブに追加した。既存の `pytest` 実行後に
配置しており、通常のユニットテストが通った上でのエンジン完走確認という位置づけ。

## スコープ外・今後の課題

- パフォーマンス回帰の検出（`sim_scale_bench.py --sizes 8,50,100` のような処理時間比較）は
  本CIには含めていない。CI環境のマシン性能はローカル/本番と異なりばらつくため、固定閾値での
  判定は誤検知が多くなると判断した。パフォーマンス検証は各Issue対応時に手動で
  `sim_scale_bench.py`/`spawn_scale_bench.py` を実行する既存の運用を継続する。
- 勝率・撃破数の偏りなどバランス面の警告（`BALANCE_WARN_*`）もCIの合否には含めていない。
  バランス変化はエンジン変更の意図した結果であることが多く、機械的にブロックすべきではないため。
