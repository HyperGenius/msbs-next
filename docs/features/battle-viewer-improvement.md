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

**現状:** フィールド上に障害物（`Obstacle`）が生成され3Dビューアに描画される。  
障害物は `radius` と `height` を持つ円柱形オブジェクトとして描画される。

**修正済みバグ:**
- `BattleSimulator` の障害物自動生成は `battlefield` 引数が明示的に渡された場合にのみ実行される設計だったが、
  `backend/main.py`（`simulate_battle`）および `backend/scripts/run_batch.py`（`_run_simulation`）で
  `battlefield` 引数が渡されていなかったため、`obstacles_info` が常に `NULL` になっていた。
- 修正: 両箇所で `battlefield=BattleField()` を明示的に渡すよう変更。

**実装済み:**
- **Backend**: `BattleResult` の `obstacles_info` JSON カラムにシリアライズして格納
- **Frontend types**: `Obstacle` 型（`obstacle_id`, `position`, `radius`, `height`）を `battle.ts` に定義済み、
  `BattleResult` に `obstacles_info?: Obstacle[]` を追加済み
- **BattleViewer**: `BattleScene` で `THREE.CylinderGeometry` で描画済み
  - 見た目: 半透明グレー/茶色の円柱（`opacity: 0.7`）
  - `scale` 係数は既存の MS 座標スケール（`0.05`）と統一

**影響ファイル（修正済み）:**
- `backend/main.py`（`battlefield=BattleField()` 追加）
- `backend/scripts/run_batch.py`（`battlefield=BattleField()` 追加）
- `backend/app/models/models.py`（`BattleResult.obstacles_info` カラム実装済み）
- `frontend/src/types/battle.ts`（実装済み）
- `frontend/src/components/BattleViewer/index.tsx`（実装済み）
- `frontend/src/components/BattleViewer/scene/BattleScene.tsx`（実装済み）
- `frontend/src/components/BattleViewer/scene/ObstacleMesh.tsx`（実装済み）
- `frontend/src/components/history/BattleDetailModal.tsx`（実装済み）

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

---

## velocity外挿のdt上限（Issue #421）

`useBattleSnapshot.ts` の `getBattleSnapshot()` は、ログ間の滑らかな移動表示のため
`pos = 直近のposition_snapshot + velocity_snapshot × dt` で位置を外挿している。

`velocity_snapshot` はほぼ毎ティックのログに付与されるが、`DESTROYED` ログ（`backend/app/engine/combat.py`
`_process_destruction`）には含まれない。そのため撃破後や長時間移動が発生しない区間では `dt` が伸び続け、
古い速度ベクトルのまま実位置から大きくズレた場所まで外挿されてしまい、照準線（`TargetLine`）や攻撃ライン
（`AttackLine`）が無関係な方向を指す不具合が発生していた。

`MAX_VELOCITY_EXTRAPOLATION_SECONDS`（1.0秒）を超える `dt` では外挿を行わず、直近の実位置（`position_snapshot`）
に留める。併せて `TargetLine` は自機（`playerState.hp > 0`）・ターゲット双方の生存を表示条件に加えている。

---

## 密集戦闘時の自機識別マーカー（Issue #426）

格闘戦（近接戦闘）で複数ユニットの球体が密集すると、自機・敵機ともに同じ `MobileSuitMesh` の球体で
描画され HP による色分けしかないため、ユーザーが自機を見失いやすい問題があった。

**調査で判明した前提:** 自機が `isTargeted`（敵のターゲットハイライトリング、赤）の対象になる経路は
コード上そもそも存在しない。`BattleScene.tsx` で自機は専用の `<MobileSuitMesh>` 呼び出しで描画され、この
呼び出しには `isTargeted` prop が渡されない。敵側の `isTargeted={enemy.id === playerState.targetId}` は
`enemyStates`（`enemies` prop 由来、自機とは別変数）に対してのみ評価される。バックエンド側も
`main.py`/`run_batch.py` の両生成箇所で `player_info`/`enemies_info` を構造的に分離しており（後者は
`enemies_info` 生成時に自ユニットIDを明示的に除外）、自機を敵側の配列に混入させる経路は無い。そのため
自機用の常時マーカーを追加しても、既存の `isTargeted` リングと表示が衝突する懸念はない。

**実装:**
- `MobileSuitMesh.tsx` に `isSelf?: boolean` prop を追加し、true の場合のみ常時表示の識別リングを描画する
  - 色は新規に導入せず、既存パレットの青系（向き矢印と同じ `#4488ff`）を使用。既存の `isTargeted` リング
    （赤、半径 1.4〜1.8・細め）・センサーリング（緑、`AnimatedSensorRing`）とは、より太い幅（半径 1.9〜2.4）
    とパルス点滅（`opacity` を sin波で周期的に変化）で区別する。ラベル文字（"YOU"等）は視認性を悪化させる
    ため採用しない
- 識別リングは射撃反動アニメーション用の `innerGroupRef` の**外側**（`hoverGroupRef` 直下）に配置し、
  反動でブレず自機の位置を安定して示せるようにしている
- `BattleScene.tsx` の自機用 `<MobileSuitMesh>` 呼び出しに `isSelf={true}` を追加

> [!IMPORTANT]
> 3Dビューアの配色パレットからの逸脱は禁止（`frontend/CLAUDE.md`「BattleViewerの配色パレット」参照）。
> 新しい視覚要素を追加する際は、既存色の太さ・点滅など表現方法の差異で区別すること。

**影響ファイル:**
- `frontend/src/components/BattleViewer/scene/MobileSuitMesh.tsx`
- `frontend/src/components/BattleViewer/scene/BattleScene.tsx`

---

## BattleViewerのカメラ初期化タイミング（Issue #425）

`BattleDetailModal` は `battle.player_info` / `enemies_info`（同期データ）のみで `hasReplayData` を判定していたため、
`useBattleLogs` によるバトルログの非同期取得（`logsLoading`）が完了する前に `BattleViewer` が先にマウントされていた。

`useBattleSnapshot.ts` の `getBattleSnapshot()` は `logs` が空の場合 `pos = initialMs.position` にフォールバックするが、
この値は実際の戦闘開始位置ではない（ガレージ格納時などの座標）。一方 `BattleScene.tsx` の `CameraInitializer` は
マウント時（`useEffect` の依存配列が空）に一度だけこのフォールバック座標を基準としてカメラ位置・`OrbitControls` の
`target` を固定する。バトルログの読み込みが完了すると自機の描画位置は実ログの `position_snapshot` に基づく本来の
位置に切り替わるが、カメラは追従しないため、自機がビューポート外に外れて見失われる不具合が発生していた。

**修正:** `BattleDetailModal.tsx` にて `logsLoading` 中は `BattleViewer` をマウントせず、同サイズのプレースホルダー
（「ビューアを準備中...」）を表示するようにした。ログ読み込み完了後に確定した実位置で `BattleViewer` が初めて
マウントされるため、`CameraInitializer` は常に正しい初期位置を基準にカメラを配置する。

**影響ファイル:**
- `frontend/src/components/history/BattleDetailModal.tsx`

---

## getBattleSnapshotの差分更新キャッシュ（Issue #465）

`getBattleSnapshot()` は再生タイムスタンプが進むたびに `logs[0]` から現在時刻まで毎回全走査してユニット状態
（位置・HP・EN・弾薬・ターゲット・クールダウン基準時刻）を再構築していた。呼び出し元（`BattleViewer/index.tsx`）
は自機×2（現在＋1ステップ前）＋敵ユニット×2×N が100msごとに呼ばれるため、1ティックあたりの計算量が
「ユニット数 × ログ長」に比例して増加し、バトル終盤・敵ユニットが多いほど再生がスローモーション化していた。
また、クールダウン判定用の直近ATTACK探索も配列末尾からの逆走査で、`currentTimestamp` より未来のログも
対象に含めてしまう不具合があった。

**修正:** `getBattleSnapshot()` に任意の `SnapshotCache`（`Map<string, SnapshotCacheEntry>`）を渡せるようにし、
「前回どこまでログを読んだか（`nextIndex`）＋その時点の状態」をキャッシュエントリとして保持する差分更新方式に
変更した。再生が進行するだけ（`currentTimestamp` が単調増加するだけ）であれば、前回のスキャン位置から続きの
ログのみを走査すればよく、O(全ログ長)だった1回あたりの計算量が「前回呼び出しからの経過分のログ数」に減る。
`currentTimestamp` が巻き戻った場合（シーク操作・巻き戻しボタン等）や `logs` 参照が変わった場合（別バトルの
表示）は自動的に先頭からの全走査にフォールバックする。クールダウン判定の直近ATTACK基準時刻もこの前方走査中に
更新するよう変更し、逆走査を廃止すると同時に未来ログを誤って参照していた不具合も解消した。

`cache` を渡さない場合は従来どおり無状態（毎回全走査）で動作するため、API 互換性は維持している。

`BattleViewer/index.tsx` では `useRef` でコンポーネントインスタンスに紐づく `SnapshotCache` を1つ保持し、
自機・各敵ユニットに渡している。「現在時刻」用と「1ステップ前（`SIMULATION_STEP_S`）」用は再生中どちらも
時間軸上を単調に前進するが同じキーで混在させると干渉するため、`` `${id}:prev` `` のように別キーを与えて
独立したキャッシュエントリとして扱っている。

呼び出し元 `BattleViewer/index.tsx` 自体（`useMemo` を使わず毎レンダーで `getBattleSnapshot` を呼んでいる点）
のメモ化は別Issueで対応予定。今回の修正は `getBattleSnapshot()` 内部のアルゴリズムのみを対象にしている。

**影響ファイル:**
- `frontend/src/components/BattleViewer/hooks/useBattleSnapshot.ts`
- `frontend/src/components/BattleViewer/index.tsx`
- `frontend/tests/unit/battleSnapshot.test.ts`
