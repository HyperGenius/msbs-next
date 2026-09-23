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

### 索敵による表示制御

プレイヤーが索敵していない敵MSをビューアに表示しません。環境フラグによる切り替えは行わず、常にフィルタを適用します。

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
  → enemyStates.filter(enemy => detectedIds.has(enemy.id))
  → visibleEnemyStates を BattleScene / BattleOverlay に渡す
```

- 未索敵敵 MS は 3D シーン（球体オブジェクト）にも HP ゲージにも表示されない

---

---

## BattleScene カメラ初期化

### 概要

モーダルオープン時（`BattleScene` マウント時）に、自機MSの初期位置を中心にカメラを自動配置する。

### 仕様

- `CameraInitializer` コンポーネント（`Canvas` の子）が `useEffect` でマウント時に1回だけ実行
- カメラ位置: `[px + 50, py + 50, pz + 50]`（自機初期 Three.js 座標からの固定オフセット）
- `OrbitControls` の target（注視点）: `[px, py, pz]`（自機初期 Three.js 座標）
- 座標変換: `scale = 0.05`、`game.x/y/z → three.x/y/z` の直接対応（`MobileSuitMesh` 等 BattleViewer 全体と統一。ゲームエンジン側は `x`/`z` が地面平面、`y` が高度（通常0）。以前は `game.z → three.y` / `game.y → three.z` と軸が入れ替わっており、障害物・機体とも本来の配置が「高さ」方向に潰れて平面的に見える不具合があった（Issue #433 で修正）

### 実装詳細

```typescript
// BattleScene.tsx 内部
const POSITION_SCALE = 0.05;

function CameraInitializer({ px, py, pz, controlsRef }) {
    const { camera } = useThree();
    useEffect(() => {
        camera.position.set(px + 50, py + 50, pz + 50);
        if (controlsRef.current) {
            controlsRef.current.target.set(px, py, pz);
            controlsRef.current.update();
        }
    }, []); // マウント時のみ実行（ユーザー操作後のカメラ位置には干渉しない）
    return null;
}
```

- `useRef` で自機MS初期位置をキャプチャするため、タイムスタンプ更新時に再計算されない
- ユーザーがカメラを操作した後はカメラ位置・target を変更しない

---

## 自機向き・ターゲット方向の可視化

### 概要

自機MSの向き矢印、ターゲット照準線、ターゲットMSのハイライトを3Dシーンに表示する。

### 1. 自機向き矢印（Heading Arrow）

自機球体から現在の胴体向きに青い矢印を表示する。

| 項目 | 内容 |
|------|------|
| データソース | `BattleLog.heading`（度数法、XZ平面）|
| 実装 | `THREE.ArrowHelper`（`<primitive>`経由） |
| 色 | `0x4488ff`（青系） |
| 対象 | 自機のみ（敵MSには表示しない） |

```typescript
// MobileSuitMesh.tsx 内部
const headingRad = (heading * Math.PI) / 180;
const dir = new THREE.Vector3(
    Math.sin(headingRad), 0, Math.cos(headingRad)
).normalize();
const arrow = new THREE.ArrowHelper(dir, origin, 4, 0x4488ff, 1.5, 1.0);
```

### 2. ターゲット照準線

自機からターゲット敵MSに向けた破線を描画する。

| 項目 | 内容 |
|------|------|
| データソース | `UnitSnapshot.targetId`（TARGET_SELECTION ログから追跡） |
| 実装 | `THREE.LineDashedMaterial` + `THREE.Line`（`<primitive>`経由） |
| 色 | `0xff4444`（赤系） |
| 表示条件 | ターゲットが存在し、かつターゲットMSが生存している場合のみ |

### 3. ターゲットMSハイライト

現在ターゲットされている敵MSをハイライト表示する。

| 項目 | 内容 |
|------|------|
| 実装 | `emissiveIntensity` 増加（0.3 → 1.2）+ 赤いリング（`THREE.RingGeometry`） |
| リング色 | `0xff4444`（赤系） |
| 表示条件 | `isTargeted === true`（`enemy.id === playerState.targetId`） |

### データフロー

```
BattleLog (heading, target_id in TARGET_SELECTION)
  → getBattleSnapshot → UnitSnapshot.heading / UnitSnapshot.targetId
  → BattleViewer.playerState (heading, targetId を自動引き継ぎ)
  → BattleScene
      ├── MobileSuitMesh (player) : heading prop → 向き矢印
      ├── MobileSuitMesh (enemy)  : isTargeted prop → ハイライトリング
      └── TargetLine              : playerPos + targetPos → 照準線
```

### UnitSnapshot 拡張

```typescript
interface UnitSnapshot {
    pos: { x: number; y: number; z: number };
    hp: number;
    en: number;
    ammo: Record<string, number>;
    warnings: WarningType[];
    heading?: number;    // 現在の胴体向き（度数法）
    targetId?: string;   // 現在のターゲットMS ID
}
```

### 実際に使用した武器の特定（EN/弾薬消費計算）

`getBattleSnapshot`（`useBattleSnapshot.ts`）は ATTACK ログの EN/弾薬消費を計算する際、
`BattleLog.weapon_id` から `initialMs.weapons` 内の該当武器を検索して使用する。

- `log.weapon_id` が存在する場合: 一致する武器を `initialMs.weapons` から検索
- `log.weapon_id` が存在しない場合（旧バトルログとの後方互換）、または一致する武器が見つからない場合: 先頭武器（`initialMs.weapons[0]`）にフォールバック

`BattleLog` には `is_crit`（クリティカルヒット判定）も含まれる（バックエンドの `combat.py` で判定済みのbool値をそのまま保持）。

---

## 関連ファイル一覧

| ファイル | 役割 |
|---------|------|
| `frontend/src/components/history/BattleDetailModal.tsx` | モーダル全体 |
| `frontend/src/components/history/TurnController.tsx` | タイムライン操作コントローラー |
| `frontend/src/components/history/BattleSummaryPanel.tsx` | 戦果サマリー（Issue #521） |
| `frontend/src/components/BattleViewer/ui/ChapterTrack.tsx` | チャプタートラック（Issue #521） |
| `frontend/src/components/BattleViewer/index.tsx` | 3D リプレイビューア |
| `frontend/src/components/BattleViewer/scene/BattleScene.tsx` | Three.js シーン |
| `frontend/src/components/BattleViewer/scene/MobileSuitMesh.tsx` | MS 球体描画 |
| `frontend/src/components/BattleViewer/scene/ObstacleMesh.tsx` | 障害物円柱描画 |
| `frontend/src/components/BattleViewer/scene/TracerMesh.tsx` | 射線（ビーム／実弾）描画（Issue #531） |
| `frontend/src/components/BattleViewer/scene/WeaponLabel.tsx` | 発射側の武器名ラベル（Issue #531） |
| `frontend/src/components/BattleViewer/scene/ImpactMarker.tsx` | 着弾フラッシュとダメージ数字（Issue #531） |
| `frontend/src/components/BattleViewer/hooks/useBattleSnapshot.ts` | 状態スナップショット管理 |
| `frontend/src/components/BattleViewer/hooks/useBattleEvents.ts` | 現在タイムスタンプの攻撃演出データ生成 |
| `frontend/src/components/BattleViewer/hooks/useAttackEffectQueue.ts` | 攻撃演出のスポーン・タイミング・段積み（Issue #531） |
| `frontend/src/components/BattleViewer/hooks/useHudAttackLog.ts` | HUD の攻撃ログ行（Issue #531） |

---

## 障害物（Obstacle）の3D表示

### 概要

バトルシミュレーターが生成する障害物（`Obstacle`）をフィールド上に半透明円柱として描画します。

### `ObstacleMesh` コンポーネント

`frontend/src/components/BattleViewer/scene/ObstacleMesh.tsx`

| プロパティ | 内容 |
|-----------|------|
| 形状 | `CylinderGeometry`（上下同径の円柱） |
| 色（通常） | SPACE: `#5a4a3a` / GROUND: `#4a5a4a` |
| 色（LOS 遮断時） | `#8a3a3a`（赤みがかった色）、`opacity: 0.9` |
| 透明度（通常） | `opacity: 0.75` |
| 輪郭線（`Edges`, drei） | SPACE: `#b89b78` / GROUND: `#8fb88f`（塗りと同色相の明るいトーン）、LOS遮断時は既存パレットの `#ff4444` を流用。暗い背景色（SPACE: `#000000` 等）とのコントラストが低く視認しづらい問題への対応（Issue #431） |
| 接地影 | 障害物ベース位置に半透明円（`opacity: 0.35`）を敷いて奥行きの手がかりにする |
| スケール | `0.05`（既存 MS 座標スケールと統一） |
| Y オフセット | 円柱の底面をグリッド面（y=0）に合わせるため `y + h/2` |
| `isBlocking` prop | `true` のとき LOS 遮断障害物として強調表示 |

`BattleScene.tsx` 側では環境背景色（`getEnvironmentColor`）に合わせた `<fog>`（`near=90, far=220`）を設定し、遠景が背景色に自然に馴染むことで奥行き感を補強している。

### データフロー

バトル履歴のリプレイ（`BattleDetailModal`）:
```
BattleResult.obstacles_info (DB)
  → BattleDetailModal (obstacles_info を BattleViewer に渡す)
  → BattleViewer (obstacles prop)
  → BattleScene (obstacles prop + blockingObstacleIds)
  → ObstacleMesh (各障害物を個別描画、isBlocking で色変化)
```

ダッシュボードのライブ観戦（`page.tsx` / Tactical Monitor）:
```
POST /api/battle/simulate レスポンスの obstacles_info
  → useBattleSimulation フック（obstaclesData state）
  → page.tsx (obstaclesData を BattleViewer に渡す)
  → BattleViewer (obstacles prop)
  → BattleScene (obstacles prop + blockingObstacleIds)
  → ObstacleMesh (各障害物を個別描画、isBlocking で色変化)
```

### 注意事項

- `obstacles_info` が `null` / `undefined` の場合は何も描画しない（既存バトル履歴への後方互換性）
- バックエンドで障害物が生成されない設定（`obstacle_density: "NONE"` など）では `obstacles_info` は `null` として保存される
- `/api/battle/simulate` の `BattleResponse` にも `obstacles_info` フィールドが含まれる（バトル実行直後のライブ観戦画面で障害物を描画するために必要）
- `BattleResult` の生成箇所は `backend/main.py`（即時実行）と `backend/scripts/run_batch.py`（デイリーバトルロイヤル等のバッチ実行）の2箇所あり、`obstacles_info` の設定も両方で必要（片方だけだと `NULL` のままになる）。障害物のシリアライズ処理は `backend/app/engine/battle_utils.py` の `serialize_obstacles()` に共通化されているため、両呼び出し元はこれを呼ぶだけでよい

---

## 背景グリッドとバトルフィールドの整列（`map_bounds`）（Issue #436）

### 背景

バトルフィールドは `backend/app/engine/simulation.py` の `BattleSimulator.map_bounds`（`(0.0, side_len)`、`side_len` はユニット数に応じて `MIN_FIELD_SIZE`〜`MAX_FIELD_SIZE`（2000〜8000）で動的算出）で表される、正の象限のみに存在する正方形。一方 `BattleScene.tsx` の `<Grid infiniteGrid>` は `position` 未指定だとThree.jsワールド原点 `(0,0,0)` を基準に描画されるうえ、`fadeDistance`（カメラからの距離でフェードする範囲）が固定値 `100` だったため、フィールドが大きい/カメラから離れているバトルではグリッドが早々にフェードアウトし、フィールドの一部にしかグリッドが重ならない見た目になっていた。

### 対応内容

1. **バックエンド**: `BattleSimulator.map_bounds`（`tuple[float, float]`、`(0.0, side_len)`）を `BattleResult.map_bounds`（`list[float] | None`、DB, `battle_results.map_bounds` カラム）と `/api/battle/simulate` の `BattleResponse.map_bounds`（`tuple[float, float] | None`）の両方に含める。`BattleResult` の生成箇所は2箇所ある（`backend/main.py` / `backend/scripts/run_batch.py`）ため、障害物情報と同様に両方に設定が必要。マイグレーション前の既存レコードは `null`（バックフィルなし、既存カラムと同じ方針）
2. **フロントエンド**: `BattleScene.tsx` が `mapBounds` prop（`[number, number] | null | undefined`）を受け取り、フィールド中心 `(min+max)/2 * POSITION_SCALE` を `<Grid position>` に設定。`fadeDistance` もフィールドの一辺長（`(max-min) * POSITION_SCALE`）に応じて動的に拡大する（最低値100は維持）。`mapBounds` が未取得（`null`/`undefined`、マイグレーション前の履歴データ等）の場合は `DEFAULT_MAP_BOUNDS = [0, 5000]`（`backend/app/engine/constants.py` の `MAP_BOUNDS` デフォルトと同値）にフォールバックする

### データフロー

```
BattleSimulator.map_bounds (backend/app/engine/simulation.py)
  → BattleResult.map_bounds (DB) / BattleResponse.map_bounds (即時実行レスポンス)
  → useBattleSimulation フック（mapBounds state）/ BattleResult 型（履歴データ）
  → page.tsx / BattleDetailModal.tsx (mapBounds を BattleViewer に渡す)
  → BattleViewer (mapBounds prop)
  → BattleScene (Grid の position・fadeDistance を算出)
```

---

## 攻撃エフェクト（ヒット演出）（Issue #531）

### 概要

「誰 → 誰」は射線と発射側の武器名で、「何が起きたか」は着弾地点のフラッシュと数字で伝える。
情報を発生地点ごとに分け、次の順に再生する（見た目・タイミングの基準はモックアップ `msbs_hit_effect_final_mockup.html`）。

```
射線（発射側 → 被弾側） → 発射側の武器名 → 着弾フラッシュ → 上昇する数字 → HP バーのチップ → HUD ログ
```

以前の `AttackLine`（止まって表示される線）・`ProjectileMesh`（800ms で飛ぶ弾）・`HitEffectMesh`（パーティクル）・
`BattleEventDisplay`（ユニット上方に武器名とテキストをまとめて表示）は、この方式に置き換えて削除した。

---

### 1. データフロー

```
timestampLogs（現在タイムスタンプのログ）
  └─ useBattleEvents → computeAttackEvents()
       ATTACK / MISS / MELEE_COMBO 1 件 → AttackEvent 1 件
       （発射側 ID・被弾側 ID・武器名・射線種別・結果・ダメージ）
BattleScene
  └─ useAttackEffectQueue（currentTimestamp が変わった時だけスポーン）
       spawnAttackEffects() → tracers / labels / impacts
       ├─ TracerMesh    … 射線
       ├─ WeaponLabel   … 発射側の武器名
       └─ ImpactMarker  … 着弾フラッシュ + ダメージ数字
BattleOverlay
  ├─ HpBar           … チップ表現
  └─ useHudAttackLog … 左下の HUD ログ行
```

- `AttackEvent.impact` は `hit` / `critical` / `combo` / `miss` の 4 種。
  Critical は `is_crit` または message の「クリティカルヒット」で判定する。
- 射線種別（`BEAM` / `BULLET`）は、武器 ID から引いた `Weapon.type === "BEAM"` を優先し、
  引けない場合は武器名（「ビーム」「beam」「mega particle」）で判定する。
- 射線・演出の位置は `getBattleSnapshot()` の現在位置（`playerState.pos` / 各敵の `state.pos`）を使う。
  未索敵の敵が発射側の場合は射線と武器名を出さず、被弾側の着弾演出だけを出す。
- 演出はタイムスタンプをまたいで保持するキュー（`useAttackEffectQueue`）で管理する。
  表示期間を過ぎた演出は、タイムスタンプが変わるたびに（攻撃が無い時刻でも）取り除く（上限: 射線 20 / 武器名 8 / 着弾 15）。

---

### 2. 射線（`TracerMesh`）

| 種別 | 描き方 | 時間 | 着弾演出の開始 |
|---|---|---|---|
| ビーム | 発射側から直線が伸び（約 60ms）、フェードで消える | 220ms | 150ms 後 |
| 実弾 | 長さ 2（Three.js 座標）の弾体が飛ぶ | 距離 ÷ 1.6m/ms（120〜350ms） | 弾体の到着時 |
| MISS | 目標の横上方（横 30m・上 20m）へ外し、1.2 倍先まで伸ばす | 同上 | 同上（数字のみ） |

- 線は drei の `Line`（Line2）で描く。線幅はピクセル単位。
- 緑のグリッドに埋もれないよう、線を重ねて描く。下から暗い縁取り（黒・不透明度 0.75）、射線の色の本体の順。
  ビームは最上段に白い芯を足す（ビーム 8px / 3.5px / 1.2px、実弾 7px / 3px）。
- `depthTest={false}` と `renderOrder` で、グリッドや障害物より手前に描く。
- 格闘コンボ（`MELEE_COMBO`）は直前の格闘 `ATTACK` と同じ射線上で起きるため、射線と武器名を重ねて出さない。
  数字は同じ組の `ATTACK` の着弾から 200ms 遅らせて出す。
- 時間の定数は `useAttackEffectQueue.ts` の `EFFECT_TIMING` にまとめている。

### 3. 武器名（`WeaponLabel`）

- 発射側の上に `▶ ビームライフル` を発射の瞬間から 900ms 表示し、フェードで消す（左端の帯は射線の色）。
- 被弾側には武器名を出さない。
- 同じ発射側・同じ武器の連射はラベルを積まずに出し直す。別の武器が同時に出る場合は 24px ずつ上に積む。

### 4. 着弾フラッシュとダメージ数字（`ImpactMarker`）

- **フラッシュ:** 被弾側の位置に白い芯と黄色のリングを出す（通常 160ms / Critical 240ms でリングが大きい）。MISS はフラッシュ無し。
- **数字:** 被弾側の中心から右上（右 22px・上 18px）にスポーンし、850ms かけて 20px 上昇しながらフェードする（ease-out）。
  バウンス・スケールのポップ・`💥` 絵文字は使わない。黒の 1px 縁取り（`text-shadow`）で緑のグリッドに埋もれないようにする。
- **タイミング:** フラッシュと数字は射線が届いた時刻に始まる（CSS の `animation-delay`）。
- **連続ヒット:** 表示期間が重なる同じ被弾側の数字は、空いている一番下の段（24px 刻み）に積む（押し上げ方式。合算はしない）。
- **表記:**

| 結果 | 数字 | 補足ラベル | サイズ |
|---|---|---|---|
| 通常命中 | `-150` | なし | 16px |
| Critical | `-350` | `CRITICAL` | 22px |
| 格闘コンボ | `-750` | `NHIT COMBO` | 22px |
| RESIST | `-120` | `RESIST 30%`（緑） | 16px |
| MISS | `MISS` | なし | 16px |

- Critical は攻撃側に `CRITICAL HIT!!` を出さず、被弾側の数字（サイズ・補足ラベル）と大きいフラッシュで表現する。
  被弾した機体メッシュのフラッシュ（`MobileSuitMesh` の `isFlashing`）は従来どおり。
- RESIST の判定文字列（「対ビーム装甲により」「対実弾装甲により」）は現行バックエンドの文言と一致しないため、
  本番ではまだ発火しない（Issue #529 で対応予定）。
- CSS のキーフレーム（`bv-weapon-label` / `bv-number-rise` / `bv-number-fade` / `bv-flash-ring` / `bv-flash-core`）は
  `frontend/src/app/globals.css` に定義している。フラッシュのキーフレームは 0% を透明にしており、
  `animation-delay` 中（着弾前）に `fill-mode: both` で見えてしまうのを防いでいる。

### 5. 配色

| 用途 | 色 |
|---|---|
| 与ダメージ（自機以外が被弾） | `#ffd84a` |
| 被ダメージ（自機が被弾） | `#ff5a4e` |
| MISS | `#9aa0a6` |
| 射線・武器名の帯（ビーム） | `#6fe6ff` |
| 射線・武器名の帯（実弾） | `#ffb36b` |
| フラッシュ（芯 / リング） | `#ffffff` / `#ffd84a` |
| RESIST の補足ラベル | `#4caf50`（既存） |

定数は `BattleViewer/utils/index.ts` の `HIT_EFFECT_COLORS`。`frontend/CLAUDE.md` の配色パレットにも追記している。

### 6. HP バーのチップ表現（`HpBar`）

- 本体の帯は 150ms で新しい幅に縮む。その下の白い帯（チップ）は 400ms 待ってから 500ms かけて縮むため、
  減った量が一瞬白く残る。
- 連続ヒット中は幅が変わるたびに待ち時間がやり直されるため、合計の減少量が残ってから縮む。
- シークで時刻を戻して HP が増えた場合は、本体・チップともにトランジション無しで幅を合わせる。
  前回の HP は `useRef` で持ち、`useLayoutEffect` で描画前に `style.transition` を書き換える
  （ブラウザは変更後の `transition` で幅のトランジションを判定するため）。
- 以前の `animate-pulse` による点滅は削除した（`HpBar` は `timestampLogs` 等を受け取らなくなった）。

### 7. HUD ログ行（`BattleOverlay` / `useHudAttackLog`）

- 左下に直近 3 行を `ガンダム ▶ ザクII (NPC)  ビームライフル  -150` の形式で出す。
  結果は `-150` / `-350 CRITICAL` / `-750 (2HIT COMBO)` / `MISS`。
- 色は被ダメージ `#ff5a4e`、MISS `#9aa0a6`、それ以外は HUD 本文と同じグレー。最新行以外は半透明にする。
- 自機と索敵済みの敵が絡むログだけを出す（未索敵の敵の名前を出さない）。
- 全ログから攻撃ログ（`ATTACK` / `MELEE_COMBO` でダメージ > 0、または `MISS`）を 1 回だけ抜き出し、
  再生中は二分探索で現在時刻以前の末尾を探す。
- `formatBattleLog()`（`utils/logFormatter.ts`）との共通化は見送った。`formatBattleLog()` は backend の
  message 文字列を加工する関数で、HUD ログは `actor_id` / `target_id` / `weapon_name` / `damage` から組み立てるため。

---

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

### 索敵による表示制御

プレイヤーが索敵していない敵MSをビューアに表示しません。環境フラグによる切り替えは行わず、常にフィルタを適用します。

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
  → enemyStates.filter(enemy => detectedIds.has(enemy.id))
  → visibleEnemyStates を BattleScene / BattleOverlay に渡す
```

- 未索敵敵 MS は 3D シーン（球体オブジェクト）にも HP ゲージにも表示されない

---

---

## BattleScene カメラ初期化

### 概要

モーダルオープン時（`BattleScene` マウント時）に、自機MSの初期位置を中心にカメラを自動配置する。

### 仕様

- `CameraInitializer` コンポーネント（`Canvas` の子）が `useEffect` でマウント時に1回だけ実行
- カメラ位置: `[px + 50, py + 50, pz + 50]`（自機初期 Three.js 座標からの固定オフセット）
- `OrbitControls` の target（注視点）: `[px, py, pz]`（自機初期 Three.js 座標）
- 座標変換: `scale = 0.05`、`game.x/y/z → three.x/y/z` の直接対応（`MobileSuitMesh` 等 BattleViewer 全体と統一。ゲームエンジン側は `x`/`z` が地面平面、`y` が高度（通常0）。以前は `game.z → three.y` / `game.y → three.z` と軸が入れ替わっており、障害物・機体とも本来の配置が「高さ」方向に潰れて平面的に見える不具合があった（Issue #433 で修正）

### 実装詳細

```typescript
// BattleScene.tsx 内部
const POSITION_SCALE = 0.05;

function CameraInitializer({ px, py, pz, controlsRef }) {
    const { camera } = useThree();
    useEffect(() => {
        camera.position.set(px + 50, py + 50, pz + 50);
        if (controlsRef.current) {
            controlsRef.current.target.set(px, py, pz);
            controlsRef.current.update();
        }
    }, []); // マウント時のみ実行（ユーザー操作後のカメラ位置には干渉しない）
    return null;
}
```

- `useRef` で自機MS初期位置をキャプチャするため、タイムスタンプ更新時に再計算されない
- ユーザーがカメラを操作した後はカメラ位置・target を変更しない

---

## 関連ファイル一覧

| ファイル | 役割 |
|---------|------|
| `frontend/src/components/history/BattleDetailModal.tsx` | モーダル全体 |
| `frontend/src/components/history/TurnController.tsx` | タイムライン操作コントローラー |
| `frontend/src/components/history/BattleSummaryPanel.tsx` | 戦果サマリー（Issue #521） |
| `frontend/src/components/BattleViewer/ui/ChapterTrack.tsx` | チャプタートラック（Issue #521） |
| `frontend/src/components/BattleViewer/index.tsx` | 3D リプレイビューア |
| `frontend/src/components/BattleViewer/scene/BattleScene.tsx` | Three.js シーン |
| `frontend/src/components/BattleViewer/scene/MobileSuitMesh.tsx` | MS 球体描画 |
| `frontend/src/components/BattleViewer/scene/ObstacleMesh.tsx` | 障害物円柱描画 |
| `frontend/src/components/BattleViewer/scene/TracerMesh.tsx` | 射線（ビーム／実弾）描画（Issue #531） |
| `frontend/src/components/BattleViewer/scene/WeaponLabel.tsx` | 発射側の武器名ラベル（Issue #531） |
| `frontend/src/components/BattleViewer/scene/ImpactMarker.tsx` | 着弾フラッシュとダメージ数字（Issue #531） |
| `frontend/src/components/BattleViewer/hooks/useBattleSnapshot.ts` | 状態スナップショット管理 |
| `frontend/src/components/BattleViewer/hooks/useBattleEvents.ts` | 現在タイムスタンプの攻撃演出データ生成 |
| `frontend/src/components/BattleViewer/hooks/useAttackEffectQueue.ts` | 攻撃演出のスポーン・タイミング・段積み（Issue #531） |
| `frontend/src/components/BattleViewer/hooks/useHudAttackLog.ts` | HUD の攻撃ログ行（Issue #531） |

---

## 障害物（Obstacle）の3D表示

### 概要

バトルシミュレーターが生成する障害物（`Obstacle`）をフィールド上に半透明円柱として描画します。

### `ObstacleMesh` コンポーネント

`frontend/src/components/BattleViewer/scene/ObstacleMesh.tsx`

| プロパティ | 内容 |
|-----------|------|
| 形状 | `CylinderGeometry`（上下同径の円柱） |
| 色（通常） | SPACE: `#5a4a3a` / GROUND: `#4a5a4a` |
| 色（LOS 遮断時） | `#8a3a3a`（赤みがかった色）、`opacity: 0.9` |
| 透明度（通常） | `opacity: 0.75` |
| 輪郭線（`Edges`, drei） | SPACE: `#b89b78` / GROUND: `#8fb88f`（塗りと同色相の明るいトーン）、LOS遮断時は既存パレットの `#ff4444` を流用。暗い背景色（SPACE: `#000000` 等）とのコントラストが低く視認しづらい問題への対応（Issue #431） |
| 接地影 | 障害物ベース位置に半透明円（`opacity: 0.35`）を敷いて奥行きの手がかりにする |
| スケール | `0.05`（既存 MS 座標スケールと統一） |
| Y オフセット | 円柱の底面をグリッド面（y=0）に合わせるため `y + h/2` |
| `isBlocking` prop | `true` のとき LOS 遮断障害物として強調表示 |

`BattleScene.tsx` 側では環境背景色（`getEnvironmentColor`）に合わせた `<fog>`（`near=90, far=220`）を設定し、遠景が背景色に自然に馴染むことで奥行き感を補強している。

### データフロー

バトル履歴のリプレイ（`BattleDetailModal`）:
```
BattleResult.obstacles_info (DB)
  → BattleDetailModal (obstacles_info を BattleViewer に渡す)
  → BattleViewer (obstacles prop)
  → BattleScene (obstacles prop + blockingObstacleIds)
  → ObstacleMesh (各障害物を個別描画、isBlocking で色変化)
```

ダッシュボードのライブ観戦（`page.tsx` / Tactical Monitor）:
```
POST /api/battle/simulate レスポンスの obstacles_info
  → useBattleSimulation フック（obstaclesData state）
  → page.tsx (obstaclesData を BattleViewer に渡す)
  → BattleViewer (obstacles prop)
  → BattleScene (obstacles prop + blockingObstacleIds)
  → ObstacleMesh (各障害物を個別描画、isBlocking で色変化)
```

### 注意事項

- `obstacles_info` が `null` / `undefined` の場合は何も描画しない（既存バトル履歴への後方互換性）
- バックエンドで障害物が生成されない設定（`obstacle_density: "NONE"` など）では `obstacles_info` は `null` として保存される
- `/api/battle/simulate` の `BattleResponse` にも `obstacles_info` フィールドが含まれる（バトル実行直後のライブ観戦画面で障害物を描画するために必要）
- `BattleResult` の生成箇所は `backend/main.py`（即時実行）と `backend/scripts/run_batch.py`（デイリーバトルロイヤル等のバッチ実行）の2箇所あり、`obstacles_info` の設定も両方で必要（片方だけだと `NULL` のままになる）。障害物のシリアライズ処理は `backend/app/engine/battle_utils.py` の `serialize_obstacles()` に共通化されているため、両呼び出し元はこれを呼ぶだけでよい

---

## LOS（Line of Sight）可視化

### 概要

自機から各索敵済み敵MSへの視線が障害物で遮断されているかを視覚的に表示します。  
デフォルト OFF で、トグルボタン（右下）で ON/OFF を切り替えられます。

### アルゴリズム

バックエンド `combat.py` の `has_los` と同じ **Ray-Sphere 交差判定** を TypeScript で再実装。

実装ファイル: `frontend/src/components/BattleViewer/utils/losUtils.ts`

LOS 計算はシミュレーション実座標（スケール前）で行う。  
BattleViewer 内の 3D 表示は `scale=0.05` で縮小されているが、  
LOS 判定には `getBattleSnapshot` から取得した実座標をそのまま使用する。

### 視線ライン表示仕様

| 状態 | 線スタイル | 色 | 透明度 |
|------|-----------|-----|--------|
| LOS あり（視線が通っている） | `LineDashedMaterial`（長い破線: dashSize=3） | 緑 `#00ff88` | 0.5 |
| LOS なし（障害物で遮断） | `LineDashedMaterial`（短い破線: dashSize=0.8） | 赤 `#ff4444` | 0.85 |

### コンポーネント構成

| ファイル | 役割 |
|---------|------|
| `utils/losUtils.ts` | `hasLos` 関数（Ray-Sphere 交差判定） |
| `index.tsx` | `showLos` ステート・`losResults` の `useMemo` 計算 |
| `scene/BattleScene.tsx` | `LosLine` コンポーネントで視線ライン描画・`blockingObstacleIds` で障害物ハイライト制御 |
| `scene/ObstacleMesh.tsx` | `isBlocking` prop で色変化 |
| `ui/BattleOverlay.tsx` | LOS トグルボタン（右下） |

### データフロー

```
BattleViewer (showLos state)
  → useMemo: hasLos() × 索敵済み敵MS数 で losResults を計算
  → BattleScene (losResults prop)
    → LosLine (各敵MSへの視線ライン描画)
    → blockingObstacleIds → ObstacleMesh (isBlocking ハイライト)
BattleOverlay
  → LOS トグルボタン (onToggleLos コールバック)
```

### パフォーマンス

- LOS 計算は `currentTimestamp` 変更時のみ再計算（`useMemo` で制御）
- `showLos` が OFF の場合は計算をスキップ（`undefined` を返す）
- 敵MS数 × 障害物数 = 最大 5 × 50 = 250 回の交差判定（1フレームで軽量）

---

## 部位別命中サマリー（Issue #504）

### 概要

Issue #501（部位別フィードバック導入）Phase 3。Phase 1（#502, 武器スロットの部位ロール化）と
Phase 2（#503, 命中後の部位判定）の結果を紐付け、バトルログへ出力・集計し、
自機視点の「どの部位に被弾したか」「どの武器スロットが命中させたか」を
バトル結果画面に表示する。改造判断（装甲を強化すべき部位、主力武器スロットの把握）に
使えるデータを提供する目的。

### バックエンド

- `BattleLog`（`backend/app/models/models.py`）に `weapon_slot_role`
  （`RIGHT_ARM`/`LEFT_ARM`/`RACK`）を追加。`hit_part` は Phase 2 で追加済み。
  いずれも Optional で、既存ログ（未設定）との後方互換性を保つ
- `combat.py` の `_process_hit`（ATTACK ログ）・`_process_melee_combo`
  （MELEE_COMBO ログ）で `weapon_slot_role` を設定する。武器選択は
  `Weapon` オブジェクトのみでスロットindexを持たないため、
  `app.engine.constants.get_weapon_slot_role_for_weapon()` で
  `actor.weapons` 内をIDから逆引きしてから `get_weapon_slot_role()` に渡す。
  格闘コンボの追撃は部位を再判定せず、起点となった `_process_hit` の
  `hit_part`/`weapon_slot_role` をそのまま引き継ぐ
- 部位別集計は `app/engine/part_hit_summary.py` の
  `compute_part_hit_summary(player, logs)` が担い、
  `{"taken": {部位名: {"hits", "damage"}}, "dealt": {武器スロットロール: {"hits", "damage"}}}`
  を返す。`app/services/battle_digest_service.py` の
  `compute_battle_digest_fields()`（`battle_digest.py` と同じ「書き込み時に
  1回だけ計算する」パターン）経由で呼ばれるため、`BattleResult` の
  生成箇所2箇所（`backend/main.py` / `backend/scripts/run_batch.py`）に
  個別実装を追加する必要はない
- `BattleResult`/`BattleResultSummary` に `part_hit_summary: dict | None`
  （JSON列）を追加。`GET /api/battles/{battle_id}` のレスポンスに含まれる
- バトルログのGCSオフロード（`battle_log_storage_service.py`）は
  `list[dict]` を素通しするだけのスキーマ非依存実装のため、
  新フィールド追加による変更は不要

### フロントエンド

- `BattleLog`（`frontend/src/types/battleCore.ts`）に `attack_sector`
  ・`hit_part`・`weapon_slot_role` を追加（`attack_sector`/`hit_part` は
  バックエンドには既存だったがフロントエンド型に未反映だったため本Issueで追加）
- `BattleResult` に `part_hit_summary?: PartHitSummary | null` を追加
- `frontend/src/hooks/usePartHitSummary.ts`: `battle.part_hit_summary`
  （バックエンド計算済み）を優先し、`null`（マイグレーション前の既存レコード）の
  場合はロード済みの `logs` からクライアント側で同じロジックを計算して
  フォールバック表示する
- `frontend/src/components/history/PartHitSummaryTable.tsx`:
  被弾部位別・命中武装別の集計テーブルを表示する。`BattleDetailModal.tsx`
  の `TurnController` 直下（3D リプレイビューア・再生コントローラーと同じ
  上部固定エリア）に統合されている

---

## バトルビューアへのフィードバック統一（Issue #521）

### 概要

従来フロントエンドに存在した「バトルログ」（`BattleLogViewer.tsx`、テキストの時系列ログ一覧）を廃止し、
ユーザー向けフィードバックをバトルビューア側の2要素に統一した。モックアップ:
https://claude.ai/artifact/RNmQeBem8BFxyuYDXhontS

```
BattleDetailModal
├── BattleViewer                       # 3D リプレイビューア（HPパネル拡張、後述）
├── ChapterTrack                       # チャプタートラック（3Dビューア直下に常駐）
├── TurnController                     # タイムライン操作
└── BattleSummaryPanel                 # 戦果サマリー（タブなし・常時表示）
    ├── 撃墜数 / 被攻撃回数 / 索敵成功（stat card）
    ├── 命中率（useWeaponAccuracySummary）
    └── PartHitSummaryTable（既存、Issue #504）
```

### チャプタートラック（`ChapterTrack.tsx` / `useBattleChapters.ts`）

「読むログ」ではなく「ジャンプ先」として位置づけたコンポーネント。自機関連ログのうち、以下の**有意なイベントのみ**
を抽出する（通常の `ATTACK`/`MISS` は対象外とし、3Dシーン側の攻撃演出（射線・武器名・着弾数字）と HUD ログ行で表現する。Issue #531）。

| 種別 | 抽出条件 |
|---|---|
| `COMBO` | `action_type === "MELEE_COMBO"` かつ自機が `actor_id` |
| `CRITICAL` | `action_type === "ATTACK"` かつ `is_crit === true`、自機が `actor_id`/`target_id` のいずれか |
| `DESTROYED_ENEMY` / `DESTROYED_SELF` | `action_type === "DESTROYED"`、`actor_id` が敵機体/自機 |
| `DETECTION` | `action_type === "DETECTION"` かつ自機が `actor_id` |

表示文言は `message` の自由文ではなく、`weapon_name`/`damage`/`combo_count`/`action_type` 等の構造化フィールドから
組み立てる（`computeBattleChapters()`、`frontend/src/components/BattleViewer/hooks/useBattleChapters.ts`）。

`currentTimestamp` に同期して該当チャプターをハイライトし自動スクロールで追従、クリックで `onSeek` を呼び出して
その時刻へシークする（字幕トラック的な挙動）。

### 敵機HPパネルの複数機対応（`BattleOverlay.tsx`）

テキストログ廃止に伴い3Dビューアが唯一の状況把握手段になったため、敵HPパネルを拡張した:

- 自機が現在攻撃対象にしている敵機（`currentTargetId`）を常に最上段に固定し `TGT` バッジを表示する
- 表示件数を `MAX_VISIBLE_ENEMIES`（2機）に制限し、超過分は「…他N機」で省略する

`currentTargetId` は自機の `ATTACK`/`MELEE_COMBO`/`MISS` ログ（`target_id` 付き）のみを `logs` から事前に
絞り込んだ `selfTargetLogs` を `currentTimestamp` 以下の範囲で逆順探索して求める。`currentTimestamp` は再生中
100msごとに変わるため、絞り込み前の全ログ（大規模バトルで十万件規模、`docs/features/battle-log-feature.md`
参照）を毎tick逆順走査すると重くなる。`selfTargetLogs` 自体は `logs` の参照が変わらない限り再計算されないため、
毎tickの逆順探索は自機の攻撃ログ数（全体よりはるかに少ない）に対してのみ行われる。

### 戦果サマリー（`BattleSummaryPanel.tsx`）

タブ切り替えは行わず常時表示する。チャプタートラック/3D演出とは異なり、ここは「自身のカスタマイズの妥当性を
判断する」ための事後分析用途のため、ダメージ等の実数値をそのまま表示する方針とした（issue #521 コメント参照）。

- `usePartHitSummary`（既存、Issue #504）: 部位別の被弾/命中集計
- `useWeaponAccuracySummary`（新規）: 自機の武装ごとの命中率。`ATTACK`/`MELEE_COMBO`/`MISS` の件数から算出し、
  一度も使用しなかった装備武器（`battle.player_info.weapons`）も 0/0・`--%` 表示で一覧に含める。
  `log.weapon_name ?? "格闘"` というフォールバックがあるため、`MISS` ログに `weapon_name`/`weapon_id` が
  正しく記録されていることが前提になる（Issue #523: `combat.py` の `_process_miss()` が長らく
  `BattleLog` 生成時に `weapon_name`/`weapon_id` を渡しておらず、遠隔武器のMISSも全て「格闘」に
  誤集計されるバグがあった。`_process_hit()` 内の完全回避（LUK）分岐で発生する `action_type="MISS"`
  ログも同様に欠落していたため合わせて修正済み）
- `useDetectionSummary`（新規）: 自機が索敵に成功した敵機数（`DETECTION` ログの `target_id` をユニーク集計）/ 総敵機数
- 撃墜数・被攻撃回数は `BattleResult.kills`/`attacks_received_count`（Issue #415 の戦闘ダイジェスト、書き込み時に
  1回だけ計算済みの非正規化カラム）をそのまま表示し、ログからの再計算はしない

### 削除・整理したもの

- `frontend/src/components/history/BattleLogViewer.tsx`
- `frontend/src/hooks/useBattleLogic.ts`（自機フォーカスフィルタ。用途が `BattleLogViewer` のみだったため）
- `frontend/src/utils/logFormatter.ts` の `isProductionDebugLog()`/`formatBattleLogs()`（同上、未使用化のため削除）
- `BattleDetailModal` の `mobileSuits` prop・`useMobileSuits()` 呼び出し（`ownedMobileSuitIds` が
  `BattleLogViewer` 専用だったため、フェッチごと不要になった）

`frontend/src/utils/logFormatter.ts` の `formatBattleLog()` 本体（距離/命中率/ダメージの抽象化・スタイル判定）は
`frontend/src/components/Dashboard/DevSimulationPanel.tsx`（開発環境専用の即時シミュレーションパネル）が
引き続き利用しているため削除していない。

---

## Storybook による演出確認（Issue #528）

### 概要

BattleViewer の 3D 演出（Hit / Critical / Miss / 格闘コンボ / 弾種別の飛翔体 / 環境）を、実際にバトルを
実行せずに Storybook 上で再現・反復確認できる。`BattleViewer` 本体には手を加えず、最小限の `BattleLog` を
props で渡すだけなので、本番と同じ描画パス（`useBattleEvents` → `BattleScene`）を通る。

```bash
cd frontend
npm run storybook   # http://localhost:6006 → BattleViewer/Effects, BattleViewer/Scenario
```

### ストーリー構成

| ストーリー | 内容 |
|---|---|
| `BattleViewer/Effects/*` | 自機 1 機・敵 1 機で演出を 1 件だけ発生させ、繰り返し再生する。Controls で演出種別・攻撃側・武器・距離・ダメージ・コンボ数・環境・自動リプレイ間隔を変更できる。`RapidFire` は同時刻に 3 発命中させ、数字の段積みを確認する（Issue #531） |
| `BattleViewer/Scenario/Skirmish` | 自機 1 機・敵 2 機の約 8 秒のバトル。`BattleDetailModal` と同じく `ChapterTrack` / `TurnController` 付きで通し再生・チャプタージャンプできる |

### ファイル

| ファイル | 役割 |
|---|---|
| `frontend/src/components/BattleViewer/BattleViewerEffects.stories.tsx` | 演出別ストーリー |
| `frontend/src/components/BattleViewer/BattleViewerScenario.stories.tsx` | シナリオ通し再生ストーリー |
| `frontend/src/components/BattleViewer/__stories__/battleLogFixtures.ts` | ログ生成ヘルパー（`attackHitLog` / `missLog` / `meleeComboLog` 等）と演出 1 件分のシナリオ生成 |
| `frontend/src/components/BattleViewer/__stories__/battleScenarioFixtures.ts` | キーフレーム補間で MOVE ログを生成し、複数演出を時系列に並べたシナリオを作る |
| `frontend/src/components/BattleViewer/__stories__/EffectReplayStage.tsx` | 演出を繰り返し発火させる再生ラッパー |

### 設計上の注意

- **ログの `message` はバックエンドの実際の文言に合わせる。** `useBattleEvents` は Critical を
  `message` 内の「クリティカルヒット」で判定するなど文字列に依存しているため、バックエンド
  （`backend/app/engine/combat.py`）と異なる文言でログを作ると、本番では出ない演出を再現してしまう。
  格闘コンボも本番同様「格闘命中の `ATTACK` → 直後に `MELEE_COMBO`」の順で生成している。
  バックエンドの文言や `COMBO_DAMAGE_MULTIPLIER` を変更した場合は `battleLogFixtures.ts` も合わせて更新する。
- **演出は `currentTimestamp` の変化で発火する。** 射線・武器名・着弾演出は `useAttackEffectQueue` の
  `useEffect([currentTimestamp])` でスポーンされるため、時刻を固定したままでは 1 回しか再生されない。
  `EffectReplayStage` は「0 秒（演出なし）→ 150ms 後に演出時刻」と往復させることで再発火させている
  （同一レンダー内で往復すると effect が発火しない）。
- **敵機は自機の `DETECTION` ログが無いと描画されない。** 射線・演出の位置は各ユニットのスナップショット位置を使うため、
  未索敵の敵が発射側だと射線と武器名が出ない。
- **Docs ページは無効化している（`tags: ["!autodocs"]`）。** Canvas を 1 ページに並べると
  ブラウザの WebGL コンテキスト数上限を超えるため。
- アニメーションが `Date.now()` / `useFrame` に依存するため、Chromatic 等のビジュアルリグレッションには使っていない。
  `npx vitest run --project storybook` による描画スモークテストの対象にはなる。

### ストーリー整備時に判明した既知の挙動

- RESIST 演出（`RESIST xx%`）は、フロントの判定文字列（「対ビーム装甲により」「対実弾装甲により」）が
  現行バックエンドのメッセージと一致しないため本番で発火しない。Issue #529 で対応予定のため、
  Effects ストーリーには RESIST を含めていない。
- 格闘コンボは、以前は同時刻の `ATTACK` ログが先にアクター側の演出枠を使うため 3D 上の「N HIT COMBO!!」が
  表示されていなかった。Issue #531 で演出枠の仕組みを廃止し、被弾側の `NHIT COMBO` 付きの数字として表示するようにした
  画面中央に「×N / NCombo XXXダメージ!!」を出していた `ComboEffect` オーバーレイは、
  被弾側の数字と情報が重複し、`animate-bounce` で跳ねるため削除した。
