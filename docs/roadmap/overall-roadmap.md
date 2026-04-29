# Project Roadmap: MSBS-Next (仮)

ブラウザベースの定期更新型MSバトルシミュレーションゲームの開発ロードマップです。
MSBSのプレイ感を現代的なクラウドネイティブ技術で再現・進化させることを目的とします。

## 📊 現在の開発状況 (2026年2月14日時点)

**✅ Phase 0 (Simulation Engine Core)** - 完了  
**✅ Phase 1 (MVP)** - 完了  
**✅ Phase 2 (α版 - 定期更新型 PvPvE)** - 完了  
**✅ Phase 2.5 (シミュレーションエンジンの高度化)** - 完了  
**✅ Phase 2.6 (UI/UX強化)** - 完了  
**🚀 Phase 3 (β版 - Community & Content)** - 進行中  
**⏳ Phase 4 (正式サービス)** - 未着手

### 実装済み主要機能

#### 基本システム
- ✅ 3D空間でのリアルタイムバトルシミュレーション
- ✅ ユーザー認証 (Clerk)
- ✅ PostgreSQL (Neon) によるデータ永続化
- ✅ React Three Fiber による3Dビジュアライゼーション
- ✅ SciFiデザインシステム (カスタムUIコンポーネント)

#### ゲームプレイ
- ✅ 機体カスタマイズ (ガレージシステム)
- ✅ 戦術設定 (Tactics System)
- ✅ ミッション選択 (難易度別、環境タイプ)
- ✅ バトル実行とログ閲覧
- ✅ 3Dリプレイビューア (環境別演出、索敵範囲可視化、リソース表示、ダメージフラッシュ)
- ✅ 高度な戦闘システム (武器属性、地形適正、索敵、リソース管理)
- ✅ ダッシュボード (エントリー状況、カウントダウンタイマー、バトル結果モーダル)

#### 成長システム
- ✅ パイロットレベル & 経験値
- ✅ 戦闘報酬 (クレジット)
- ✅ スキルシステム (4種類のパッシブスキル)
- ✅ 機体強化 (Engineering)
- ✅ 機体購入 (Shop)

#### マルチプレイヤー対応
- ✅ バトルエントリーシステム
- ✅ マッチング & ルーム管理
- ✅ NPC自動生成
- ✅ バッチ処理システム (定期更新対応)

#### コミュニティ機能
- ✅ ランキングシステム (シーズン制、Top 100表示)
- ✅ プレイヤー視察機能 (装備・戦術確認)
- ✅ エースパイロット（ネームドNPC 5体）
- ✅ NPC性格システム (AGGRESSIVE/CAUTIOUS/SNIPER)
- ✅ 戦闘中のセリフ表示 (Battle Chatter)

---

## 1. プロジェクト概要

* **ジャンル:** 定期更新型タクティカルバトルシミュレーション (PvPvE)
* **プラットフォーム:** Webブラウザ (PC/Mobile)
* **コア体験:** MSカスタマイズ → 戦術設定 → 自動シミュレーション → バトルログ確認
* **開発状況:** Phase 2.6 (UI/UX強化) 完了、Phase 3 (β版) 準備中

## 2. 技術スタック

| 領域 | 技術 | 状態 |
|------|------|------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, React Three Fiber | ✅ 稼働中 |
| Backend | Python (FastAPI), Pydantic v2, SQLModel | ✅ 稼働中 |
| Simulation | NumPy (ベクトル計算), Pure Python Logic | ✅ 実装済 |
| Database | Neon (PostgreSQL), Alembic (マイグレーション) | ✅ 稼働中 |
| Auth | Clerk (JWT/JWKS) | ✅ 実装済 |
| Visuals | React Three Fiber (@react-three/fiber, @react-three/drei) | ✅ 実装済 |
| UI Components | カスタムSciFiデザインシステム | ✅ 実装済 |
| Infra | Terraform (Neon), Vercel (Frontend予定), Render (Backend予定) | 🔧 一部構築済 |

## 3. 開発フェーズ

### Phase 0: プロトタイプ (Simulation Engine Core) ✅ 完了
**ゴール:** CLI上で2機のMSが3D空間を移動し、射程に入ったらログを出す。

* **実装機能:**
    * [x] **データ構造定義 (Pydantic/SQLModel):** MS、座標(Vector3)、武器、BattleLogの型定義。
        * `backend/app/models/models.py` - MobileSuit, Weapon, Vector3, BattleLog
    * [x] **3D空間ロジック (NumPy):**
        * X-Y-Z座標系の定義。
        * 移動ベクトルの計算 (現在地からターゲットへの接近)。
        * 距離計測と索敵判定。
    * [x] **ターン処理:** 1ターンごとの状態更新ループの実装。
        * `backend/app/engine/simulation.py` - BattleSimulator クラス
    * [x] **テキストログ出力:** BattleLog形式でJSONレスポンスとして出力。

### Phase 1: MVP (Minimum Viable Product) ✅ 完了
**ゴール:** Webブラウザ上で「機体設定→戦闘開始→結果ログ閲覧」のコアサイクルが回る。

* **Frontend (Next.js):**
    * [x] ユーザー登録・ログイン (Clerk)。
        * `frontend/src/middleware.ts` - 保護ルート設定
        * `frontend/src/components/Header.tsx` - SignIn/UserButton
    * [x] ガレージ画面 (ステータス確認、簡易装備変更)。
        * `frontend/src/app/garage/page.tsx` - 機体一覧・編集フォーム
    * [x] バトルエントリー画面 (対戦開始ボタン)。
        * `frontend/src/app/page.tsx` - シミュレーション実行
    * [x] 結果表示画面 (テキスト形式のバトルログ表示)。
        * ログビューアー + ターンスライダー
    * [x] バトル履歴画面 (`/history`) - 過去のバトル記録閲覧
    * [x] パイロット画面 (`/pilot`) - ステータス、スキル管理
    * [x] ショップ画面 (`/shop`) - 機体購入
* **Backend (FastAPI):**
    * [x] バトル実行APIエンドポイントの実装。
        * `POST /api/battle/simulate` - プレイヤー機体 vs 敵の戦闘
    * [x] 機体管理API。
        * `GET /api/mobile_suits` - 機体一覧取得
        * `PUT /api/mobile_suits/{ms_id}` - 機体更新（認証必須）
    * [x] バトル結果のDB保存 (JSONBカラム活用)。
        * `BattleResult` テーブル - 勝敗、ログ、日時を記録
    * [x] ミッション選択機能 (難易度別の敵構成)。
        * `Mission` テーブル - 3つの標準ミッション
    * [x] パイロットAPI。
        * `GET /api/pilots/me` - パイロット情報取得
        * `POST /api/pilots/skills/unlock` - スキル習得
    * [x] ショップAPI。
        * `GET /api/shop/listings` - 商品一覧取得
        * `POST /api/shop/purchase/{item_id}` - 機体購入
    * [x] 整備(Engineering)API。
        * `POST /api/engineering/upgrade` - 機体ステータス強化
        * `GET /api/engineering/preview` - 強化コストプレビュー
* **Game Logic:**
    * [x] 高度な戦闘システムの実装。
        * 武器属性 (BEAM/PHYSICAL) と耐性
        * 距離適正による命中率変動 (最適射程、減衰係数)
        * 地形適正による移動速度補正 (S/A/B/C/D)
        * 索敵システム (Fog of War)
        * リソース管理 (弾薬、EN、クールダウン)
        * 機動性による回避ボーナス
        * クリティカルヒット判定 (5%)
        * 装甲と耐性によるダメージ軽減
    * [x] 戦略AI。
        * 戦略価値と脅威度の計算
        * 戦術に基づくターゲット選択
    * [x] 勝敗判定。
        * プレイヤー全滅 or 敵全滅で終了
    * [x] パイロット成長システム。
        * レベル、経験値、クレジット管理
        * 戦闘報酬（勝利/敗北、撃墜ボーナス）
    * [x] パイロットスキルシステム。
        * 4種類のパッシブスキル（命中率、回避率、攻撃力、クリティカル率）
        * スキルポイント (SP) による習得・強化
* **Infrastructure:**
    * [x] Neon DB構築 (Terraform)。
        * `infra/neon/main.tf` - プロジェクト・ロール・DB作成
    * [x] Alembicマイグレーション。
        * `mobile_suits`, `missions`, `battle_results`, `pilots` テーブル
    * [ ] Vercel/Render デプロイ設定。

### Phase 2: α版 (定期更新型 PvPvE) ✅ 完了
**ゴール:** 「エントリー → バッチ処理 → 結果確認」の非同期ゲームサイクルを実現し、複数プレイヤー + NPCが入り乱れるバトルロイヤル形式を完成させる。

#### ゲームサイクル (The Loop)

定期更新型ゲームの基本サイクルは以下の3フェーズで構成されます：

```
┌─────────────────────────────────────────────────────────────────┐
│  Preparation (準備期間)                                          │
│  ├─ 機体カスタマイズ (ガレージ)                                    │
│  ├─ 行動ロジック（Tactics）設定                                   │
│  └─ 次回バトルへのエントリー（参加登録）                             │
├─────────────────────────────────────────────────────────────────┤
│  Execution (更新処理) ※システム側で自動実行                        │
│  ├─ 締切時刻にエントリー締め切り（例: 毎日21:00）                    │
│  ├─ マッチング（Room分け: プレイヤー + NPC）                        │
│  └─ シミュレーション一括実行 → 結果をDBに保存                       │
├─────────────────────────────────────────────────────────────────┤
│  Result (結果閲覧)                                               │
│  ├─ バトルログ（リプレイ）の確認                                    │
│  └─ 経験値・報酬の獲得                                            │
└─────────────────────────────────────────────────────────────────┘
```

#### 実装済み機能

---

#### Step 1: 行動ロジック（Tactics）の実装 ✅ 完了

プレイヤーが戦闘中に介入できないため、AIの行動を事前に設定できる機能。

* **Frontend:**
    * [x] **Tactics設定UI:** プリセット選択
        * `frontend/src/app/garage/page.tsx` - 戦術設定フォーム
    * [x] **プレビュー機能:** 設定内容の確認

* **Backend:**
    * [x] **tactics カラム追加:** `MobileSuit` モデルに戦術設定を追加
        * `backend/app/models/models.py`
    * [x] **BattleSimulator 改修:** tactics を読み取って行動決定
        * `backend/app/engine/simulation.py`
    * [x] **API:** `PUT /api/mobile_suits/{ms_id}` - 戦術設定含む機体更新

* **Logic:**
    * [x] **ターゲット優先度:** `CLOSEST` (最寄り) / `WEAKEST` (瀕死優先) / `RANDOM` (ランダム)
    * [x] **交戦距離設定:** `MELEE` (接近) / `RANGED` (引き撃ち) / `BALANCED` (バランス) / `FLEE` (回避)
    * [x] **NPCバリエーション:** ランダムな戦術パターン

---

#### Step 2: エントリー機能とマッチングテーブルの実装 ✅ 完了

「即時実行ボタン」に加えて「次回更新にエントリー」機能を追加。

* **Database:**
    * [x] **BattleEntry テーブル作成:** ユーザーID, MSスナップショット, ステータス
        * `backend/app/models/models.py`
        * `is_npc` フィールド: NPCかどうかの判定
    * [x] **BattleRoom テーブル作成:** 参加者のグループ化用
        * ステータス: `OPEN` / `WAITING` / `COMPLETED`

* **Backend:**
    * [x] **API:** `POST /api/entries` - 次回バトルへのエントリー
    * [x] **API:** `GET /api/entries/my-entry` - エントリー状態確認
    * [x] **API:** `DELETE /api/entries/{entry_id}` - エントリーキャンセル

* **Frontend:**
    * [x] **エントリーUI実装:** 現在は即時実行のみ (エントリー機能は将来実装予定)

---

#### Step 3: バッチ処理とPvPvEロジックの結合 ✅ 完了

本番の定期更新処理を実装。

* **Batch Script:**
    * [x] **マッチング処理:** `MatchingService` - エントリー済みユーザーをグループ化
        * `backend/app/services/matching_service.py`
    * [x] **NPC自動生成:** 難易度に応じたNPCをRoomに追加
        * ランダムな機体名、ステータス、武器、戦術
    * [x] **バッチ実行スクリプト:** `backend/scripts/run_batch.py`
        * マッチング → シミュレーション → 結果保存の一括処理

* **Simulation拡張:**
    * [x] **N体シミュレーション:** 任意のユニット数（8〜16機）を処理可能に
    * [x] **陣営ロジック拡張:**
        * PLAYER (各ユーザー) - 自分以外すべて敵
        * NPC - 全プレイヤーを敵として行動
    * [x] **撃墜数記録:** バトルログに撃墜情報を記録

* **Infrastructure:**
    * [x] **GitHub Actions ワークフロー:** `.github/workflows/scheduled-battle.yaml`
        * 手動トリガー対応
        * スケジュール実行対応 (コメントアウト状態)

---

#### Step 4: 結果通知とリプレイ ✅ 完了

バッチ処理で生成されたログを閲覧・再生できる機能。

* **Frontend:**
    * [x] **バトル履歴画面:** `frontend/src/app/history/page.tsx`
        * 過去のバトル一覧
        * 結果サマリー表示 (勝敗、日時)
    * [x] **リプレイ再生:** BattleLogを3Dビューアで再生
        * `frontend/src/components/BattleViewer.tsx`

* **Backend:**
    * [x] **API:** `GET /api/battles` - 参加したバトル一覧
    * [x] **API:** `GET /api/battles/{battle_id}` - バトルログ取得
    * [ ] **結果通知（オプション）:** Webhook or メール通知 (将来実装予定)

---

#### 3Dビジュアル基盤 ✅ 完了

* **Visuals:**
    * [x] **3Dリプレイ (Three.js/R3F):** バトルログJSONを解析し、ブラウザ上で3D表示。
        * `frontend/src/components/BattleViewer.tsx`
        * 球体でMS表現 (HP残量で色変化: 緑→黄→赤)
        * ターンスライダーで任意時点の状態を確認可能
        * HPバー付きUIオーバーレイ
        * Stars, Grid背景
    * [x] **多人数対応ビューア:** 10機以上の同時表示、プレイヤー/NPC色分け対応

---

#### 成長・報酬システム ✅ 完了

* **Progression:**
    * [x] **戦闘後経験値:** 勝敗・撃墜数に応じてEXP付与
        * 勝利: +100 EXP、敗北: +20 EXP
        * 撃墜ボーナス: +10 EXP/機
    * [x] **パイロットステータス:** レベルアップシステム
        * レベル、経験値、クレジット管理
        * `backend/app/services/pilot_service.py`
    * [x] **パイロットスキル:** スキルポイント (SP) による能力強化
        * 命中率向上、回避率向上、攻撃力向上、クリティカル率向上
        * `backend/app/core/skills.py`
    * [x] **報酬:** 勝敗に応じた資金獲得
        * 勝利: +500 CR、敗北: +100 CR
        * 撃墜ボーナス: +50 CR/機

---

#### 経済システム ✅ 完了

* **Engineering (整備):**
    * [x] **機体強化システム:** クレジットを消費してステータス強化
        * HP、装甲、機動性、武器威力の強化
        * `backend/app/services/engineering_service.py`
    * [x] **API:** `POST /api/engineering/upgrade` - 強化実行
    * [x] **API:** `GET /api/engineering/preview` - コストプレビュー

* **Shop (ショップ):**
    * [x] **機体購入システム:** クレジットで新しい機体を購入
        * 複数の機体タイプをラインナップ
        * `backend/app/routers/shop.py`
    * [x] **API:** `GET /api/shop/listings` - 商品一覧
    * [x] **API:** `POST /api/shop/purchase/{item_id}` - 購入実行

### Phase 2.5: シミュレーションエンジンの高度化 ✅ 完了
**ゴール:** 戦闘の戦略性と深みを向上させる。  
**完了日:** 2026年2月8日

* **武器属性と相性システム (Attributes & Compatibility):** ✅
    * [x] ビーム/実弾の武器タイプとそれに対応する耐性。
    * [x] 武器ごとの最適射程と距離減衰。
* **バトルフィールドと索敵 (Field & Detection):** ✅
    * [x] 地形タイプ（宇宙/地上/コロニー/水中）と地形適正。
    * [x] Fog of War（索敵範囲内の敵のみターゲット可能）。
* **戦略AI (Rule-based AI):** ✅
    * [x] 戦略価値と脅威度の計算。
    * [x] 戦術設定に基づいた賢いターゲット選択。
* **リソース管理 (Resource Management):** ✅
    * [x] 弾薬制限、ENゲージ、武器クールダウン。
    * [x] リフレッシュフェーズ（ターン開始時の回復処理）。

詳細: [battle_simulation_roadmap.md](./battle_simulation_roadmap.md)  
実装レポート:
- [ADVANCED_BATTLE_LOGIC_REPORT.md](../ADVANCED_BATTLE_LOGIC_REPORT.md)
- [TERRAIN_DETECTION_IMPLEMENTATION_REPORT.md](../TERRAIN_DETECTION_IMPLEMENTATION_REPORT.md)
- [RESOURCE_MANAGEMENT_IMPLEMENTATION.md](../RESOURCE_MANAGEMENT_IMPLEMENTATION.md)

---

### Phase 2.6: UI/UX強化 ✅ 完了
**ゴール:** プレイヤー体験の向上、バトルビューアの視覚表現強化、ダッシュボードの改善。  
**完了日:** 2026年2月11日

* **3Dバトルビューアの大幅強化:** ✅
    * [x] 環境別の演出強化 (SPACE/GROUND/COLONY/UNDERWATER)
        * 地面メッシュ、水面エフェクト、メタリック床
        * 環境に応じたフォグと照明
    * [x] 索敵範囲の可視化 (Fog of War)
        * アニメーションする緑色のリング表示
        * sensor_range パラメータに基づく動的サイズ
    * [x] リアルタイムリソース表示
        * ENゲージ（シアン色）
        * 弾薬残量（オレンジ色）
        * ゲージバーとアイコン表示
    * [x] ダメージフラッシュエフェクト
        * 被ダメージ時の赤色フラッシュ
        * HPバーの視覚的フィードバック
    * [x] バトルイベント演出
        * 攻撃・被弾・撃墜のアニメーション表示
    * [x] コンポーネント分離とパフォーマンス最適化
        * `BattleScene` / `BattleOverlay` / `UnitMesh` の分離
        * `useMemo` によるレンダリング最適化

* **ダッシュボードUI刷新:** ✅
    * [x] **カウントダウンタイマー:** 次回バトルまでの残り時間を大きく表示
        * 1秒ごとのリアルタイム更新
        * グラデーションデザイン
    * [x] **エントリーダッシュボード:** エントリー状況を直感的に表示
        * 大きなENTRYボタン
        * 参加者数プログレスバー
        * エントリー済み機体のサムネイル・スペック表示
    * [x] **バトル結果モーダル:** 勝敗に応じた演出
        * WIN時: 緑/青グラデーション、星エフェクト
        * LOSE時: 赤グラデーション、警告アイコン
        * 経験値・報酬の視覚的表示

* **ガレージUIの機能拡張:** ✅
    * [x] 地形適正表示セクション
        * 4つの環境（SPACE/GROUND/COLONY/UNDERWATER）
        * ランク表示（S/A/B/C/D）と色分け
        * 補正値表示（+20% ~ -60%）
        * アイコン表示（🌌/🏔️/🏢/🌊）

* **ログ表示の改善:** ✅
    * [x] メッセージの色分け強調表示
        * リソース制限: オレンジ色（弾切れ、EN不足、クールダウン）
        * 地形・索敵: シアン色
        * 属性相性: 紫色（BEAM、PHYSICAL）

実装レポート:
- [PHASE_2_5_COMPLETION_REPORT.md](../PHASE_2_5_COMPLETION_REPORT.md) - Phase 2.5 UI実装完了報告
- [IMPLEMENTATION_SUMMARY_BATTLE_VIEWER.md](../IMPLEMENTATION_SUMMARY_BATTLE_VIEWER.md) - バトルビューア視覚表現強化
- [DASHBOARD_IMPLEMENTATION_REPORT.md](../DASHBOARD_IMPLEMENTATION_REPORT.md) - ダッシュボード改善
- [BATTLE_VIEWER_ENHANCEMENTS.md](../BATTLE_VIEWER_ENHANCEMENTS.md) - バトルビューアー強化詳細
- [SF_DESIGN_IMPLEMENTATION_SUMMARY.md](../SF_DESIGN_IMPLEMENTATION_SUMMARY.md) - SciFiデザインシステム

---

### Phase 3: β版 (Community & Content) 🚀 進行中
**ゴール:** コンテンツ拡充とコミュニティ機能の整備。

* **Advanced NPC System (NPCの高度化):**
    * [x] **エースパイロット (Ace Pilots):** ✅ 実装完了 (2026-02-14)
        * 5体のネームドNPC（赤い彗星、青き巨星、紫豚、白い悪魔、ハマーンの影）
        * レア出現システム (5%確率)
        * 特別報酬 (ボーナス経験値・クレジット)
        * 実装レポート: [ACE_PILOT_IMPLEMENTATION_SUMMARY.md](../reports/ACE_PILOT_IMPLEMENTATION_SUMMARY.md)
    * [x] **NPC性格システム (Personality):** ✅ 実装完了 (2026-02-14)
        * 3種類の性格 (AGGRESSIVE/CAUTIOUS/SNIPER)
        * 性格に応じた戦術と行動パターン
        * 戦闘中のセリフ表示 (Battle Chatter)
    * [ ] **NPC永続化 (Persistence):**
        * NPCを `Mission` 設定値から、`Pilots`/`MobileSuits` テーブルのレコードとして独立させる。
        * 個体識別（“あの時のザク”）を可能にする。
        * NPC用のプロフィールと戦績管理。
    * [ ] **自律成長 (Autonomous Growth):**
        * バトル結果に基づいてNPCも経験値を獲得しレベルアップする。
        * 獲得した報酬で機体を強化・換装するAIロジックの実装。
        * NPCの戦術をより多様化。

* **ランキング & 統計:**
    * [x] **シーズンランキング:** ✅ 実装完了 (2026-02-14)
        * シーズン管理 (Season テーブル)
        * 累計勝利数・撃墜数・獲得クレジット集計
        * バッチ処理で自動更新
    * [x] **リーダーボード:** ✅ 実装完了
        * Top 100表示
        * 自分の順位ハイライト
        * トップ3バッジ表示（金・銀・銅）
    * [x] **プレイヤー視察機能:** ✅ 実装完了
        * 他プレイヤーのプロフィール閲覧
        * 機体スペック、装備構成、戦術設定の確認
        * セキュリティ考慮（非公開情報の除外）
        * 実装レポート: [RANKING_IMPLEMENTATION_SUMMARY.md](../reports/RANKING_IMPLEMENTATION_SUMMARY.md)
    * [ ] **個人戦績:** 参加履歴、平均順位、K/D比、勝率
    * [ ] **バトル統計:** 武器使用率、地形別勝率、戦術効果分析

* **Content:**
    * [ ] **勢力 (Faction):** 所属勢力ごとのボーナス・専用機体
        * 地球連邦 / ジオン / その他勢力
        * 勢力ミッション、勢力ランキング
    * [ ] **MS/武器バリエーション:** 
        * 機体・武器のアンロック/購入システム拡充
        * レア度システム (Common/Rare/Epic/Legendary)
        * 機体ツリー（開発系統）
    * [ ] **マップバリエーション:** 
        * 宇宙/地上/コロニー内/水中など環境の追加
        * 障害物システム（岩、建物、デブリ）
        * 特殊地形効果（重力井戸、ミノフスキー粒子）
    * [ ] **ミッション拡充:** 
        * より多様な敵編成とシナリオ
        * ストーリーミッション
        * イベントミッション

* **Social:**
    * [ ] **フレンド機能:** フォロー、対戦履歴閲覧、プライベートマッチ
    * [ ] **チーム戦:** 2〜3人チームでのバトルロイヤル
    * [ ] **ギルド/クラン:** 組織対抗戦、ギルド専用報酬
    * [ ] **チャット機能:** ロビーチャット、バトル後チャット

* **UI/UX 更なる改善:**
    * [ ] **よりリッチな3Dモデル:** 機体ごとの専用3Dモデル（現在は球体）
    * [ ] **カメラコントロール:** 自由視点、追尾カメラ、リプレイのカメラワーク改善
    * [ ] **エフェクト強化:** ビーム、爆発、被弾エフェクトのグラフィック向上
    * [ ] **サウンド:** BGM、SE、ボイス
    * [ ] **モバイル対応:** タッチUI、レスポンシブ最適化

### Phase 4: 正式サービス (Monetization & Ops) ⏳ 未着手
**ゴール:** 収益化と安定運営体制の確立。

* **Deployment:**
    * [ ] **Vercel デプロイ:** Frontend の本番環境構築
    * [ ] **Render/AWS デプロイ:** Backend の本番環境構築
    * [ ] **CI/CD パイプライン:** 自動テスト & デプロイ
    * [ ] **監視・ログ:** Sentry, Datadog等の導入
    * [ ] **CDN設定:** 静的アセットの配信最適化

* **Performance:**
    * [ ] **キャッシング戦略（Redis）:** セッション管理、リーダーボードキャッシュ
    * [ ] **クエリ最適化:** インデックス設計、N+1問題の解消
    * [ ] **CDN活用:** 画像・3Dアセットの配信
    * [ ] **負荷テスト & チューニング:** 大規模ユーザー対応

* **Monetization:**
    * [ ] **課金システム:** プレミアム機能、アイテム課金
    * [ ] **サブスクリプション:** 月額会員制度
    * [ ] **広告統合:** 無料ユーザー向け広告表示

* **Operations:**
    * [ ] **カスタマーサポート:** 問い合わせフォーム、FAQ
    * [ ] **利用規約・プライバシーポリシー:** 法的文書の整備
    * [ ] **不正行為対策:** チート検出、BANシステム
    * [ ] **データバックアップ戦略:** 定期バックアップ、災害復旧計画

---

## 4. シミュレーション仕様 (実装済)

物理エンジンは使用せず、数学的な計算のみで処理する。
* **フィールド:**
    * 境界なしの3D空間。
    * 環境タイプ: `SPACE` (宇宙), `GROUND` (地上), `COLONY` (コロニー内), `UNDERWATER` (水中)
    * 障害物は未実装（将来実装予定）。
* **移動:**
    * 慣性は考慮せず、毎ターン `mobility × 基本速度 × 地形補正` 分だけ戦術に応じた方向へベクトル移動。
    * 地形補正: 地形適正 (S/A/B/C/D) に応じて 1.2 / 1.0 / 0.8 / 0.6 / 0.4 倍
    * 基本移動速度: `max(5.0, mobility * 50)`

### 戦闘システム
* **索敵:**
    * `sensor_range` 内の敵のみをターゲット候補とする (Fog of War)。
    * 索敵状態はチーム単位で共有される。
* **ターゲット選択:**
    * 戦術設定 (tactics) に基づいて選択:
        * `CLOSEST` - 最も近い敵
        * `WEAKEST` - 最もHPが低い敵
        * `HIGHEST_THREAT` - 脅威度が最も高い敵
        * `HIGHEST_VALUE` - 戦略価値が最も高い敵
        * `RANDOM` - ランダム
* **攻撃判定:**
    * 射程内かつリソース（弾数・EN・クールダウン）が足りていれば攻撃、そうでなければ移動。
* **命中率:**
    * 基本式: `base_accuracy - (distance_penalty) - (target.mobility * 10) + skill_bonus`
    * 距離ペナルティ: 武器の `optimal_range` からの偏差に応じた正規分布曲線
    * 最適射程で命中率が最も高く、離れるほど低下する。
* **ダメージ:**
    * 基本式: `max(1, weapon.power - target.armor) * variance(0.9~1.1)`
    * 武器属性と耐性による軽減:
        * ビーム兵器: `beam_resistance` により最大100%軽減
        * 実弾兵器: `physical_resistance` により最大100%軽減
    * **クリティカル:** 5%確率で `power * 1.2` (装甲無視)

### リソース管理
* **弾薬 (Ammo):**
    * 武器ごとに `max_ammo` が設定され、0になると使用不可。
    * `max_ammo = None` の場合は無限（EN兵器）。
* **エネルギー (EN):**
    * 機体ごとに `max_en` と `en_recovery` が設定。
    * ビーム兵器は `en_cost` を消費し、ENが足りないと発射不可。
    * 毎ターン開始時に `en_recovery` 分回復。
* **クールダウン:**
    * 武器ごとに `cool_down_turn` が設定され、発射後は指定ターン数待機が必要。
    * 毎ターン開始時に残りクールダウンが1減少。

---

## 5. データモデル (実装済)

### mobile_suits テーブル ✅
| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | Primary Key |
| user_id | String | Clerk User ID (nullable) |
| name | String | 機体名 |
| max_hp | Integer | 最大HP |
| current_hp | Integer | 現在HP |
| armor | Integer | 装甲値 |
| mobility | Float | 機動性 |
| sensor_range | Float | 索敵範囲 |
| side | String | 陣営 (PLAYER/ENEMY) |
| tactics | JSON | 戦術設定 (priority, range) |
| position | JSON | Vector3 |
| velocity | JSON | Vector3 |
| weapons | JSON | Weapon[] |
| active_weapon_index | Integer | 選択中武器 |

### missions テーブル ✅
| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | Primary Key |
| name | String | ミッション名 |
| description | String | 説明 |
| difficulty | String | 難易度 (EASY/NORMAL/HARD) |
| enemy_config | JSON | 敵機構成 |
| created_at | Timestamp | 作成日時 |

### battle_results テーブル ✅
| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | Primary Key |
| user_id | String | Clerk User ID |
| mission_id | UUID | FK → missions |
| room_id | UUID | FK → battle_rooms (nullable) |
| victory | Boolean | 勝敗 |
| logs | JSONB | BattleLog[] |
| created_at | Timestamp | バトル実行日時 |

### pilots テーブル ✅
| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | Primary Key |
| user_id | String | Clerk User ID (一意) |
| name | String | パイロット名 |
| level | Integer | レベル |
| exp | Integer | 経験値 |
| credits | Integer | クレジット |
| skill_points | Integer | 未使用のスキルポイント |
| skills | JSON | 習得済みスキル (skill_id: level) |
| created_at | Timestamp | 作成日時 |
| updated_at | Timestamp | 更新日時 |

### battle_rooms テーブル ✅
| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | Primary Key |
| status | String | OPEN / WAITING / COMPLETED |
| max_participants | Integer | 最大参加者数 |
| created_at | Timestamp | 作成日時 |
| updated_at | Timestamp | 更新日時 |

### battle_entries テーブル ✅
| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | Primary Key |
| room_id | UUID | FK → battle_rooms |
| user_id | String | Clerk User ID (NPC時はnull) |
| is_npc | Boolean | NPCフラグ |
| mobile_suit_snapshot | JSON | 機体データのスナップショット |
| created_at | Timestamp | エントリー日時 |

---

### 実装済み (Phase 3)

#### seasons テーブル ✅
| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | Primary Key |
| name | String | シーズン名 |
| start_date | Date | 開始日 |
| end_date | Date | 終了日 |
| is_active | Boolean | アクティブフラグ |

#### leaderboards テーブル ✅
| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | Primary Key |
| season_id | UUID | FK → seasons |
| user_id | String | Clerk User ID |
| total_points | Integer | 累計ポイント |
| total_battles | Integer | 総戦闘数 |
| total_wins | Integer | 勝利数 |
| total_kills | Integer | 総撃墜数 |

### 今後追加予定 (Phase 3以降)

#### factions テーブル
| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | Primary Key |
| name | String | 勢力名 |
| bonus_type | String | ボーナス種別 |
| bonus_value | Float | ボーナス値 |

---

## 6. テスト

### Unit Tests ✅
* **Simulation Tests:** `backend/tests/unit/test_simulation.py`
    * シミュレータ初期化テスト
    * ターン順序テスト（機動性順）
    * プレイヤー勝利シナリオテスト
    * 敵勝利シナリオテスト
    * 移動ロジックテスト
    * 攻撃命中率テスト
    * Tactics動作テスト (4件)

* **Terrain & Detection Tests:** `backend/tests/unit/test_terrain_and_detection.py`
    * 地形適正システムテスト
    * 地形補正による移動速度変化テスト
    * 索敵システムテスト (Fog of War)
    * 環境効果テスト

* **Tactics Integration Tests:** `backend/tests/unit/test_tactics_integration.py`
    * 戦術統合テスト

* **Matching Service Tests:** `backend/tests/unit/test_matching_service.py`
    * マッチングサービステスト (7件)

### Integration Tests ✅
* **Batch Processing Tests:** `backend/tests/integration/test_batch_processing.py`
    * エンドツーエンドのバッチ処理テスト

### API Tests ✅
* **Structure Tests:** `backend/tests/test_api_structure.py`
    * API構造テスト

* **Feature Tests:**
    * `backend/tests/test_engineering.py` - 整備システムテスト
    * `backend/tests/test_entry_feature.py` - エントリー機能テスト
    * `backend/tests/test_entry_snapshot.py` - エントリースナップショットテスト
    * `backend/tests/test_shop.py` - ショップテスト
    * `backend/tests/test_ranking_system.py` - ランキングシステムテスト

* **NPC Tests:**
    * `backend/tests/unit/test_npc_personality_and_ace.py` - NPC性格 & エースパイロットテスト
    * `backend/tests/unit/test_battle_chatter.py` - 戦闘セリフテスト

---

## 7. ドキュメント

### セットアップ & インフラ
* [Clerk認証セットアップガイド](./CLERK_SETUP.md)
* [Clerk実装サマリー](./CLERK_IMPLEMENTATION_SUMMARY.md)
* [Neonマイグレーションガイド](./neon_migration.md)
* [インフラ構成](./infra.md)

### 機能実装ガイド
* [Mobile Suit API仕様](./mobile-suit-api-implementation.md)
* [バトル履歴とミッション選択機能](./battle-history-implementation.md)
* [戦術システム実装](./TACTICS_IMPLEMENTATION.md)
* [パイロットシステム](./PILOT_SYSTEM.md)
* [バッチシステムとマッチング](./BATCH_SYSTEM.md)
* [バッチアーキテクチャ](./BATCH_ARCHITECTURE.md)

### 実装完了レポート
* [バトル履歴実装サマリー](../IMPLEMENTATION_SUMMARY.md)
* [戦術システム実装レポート](../IMPLEMENTATION_REPORT.md)
* [パイロットスキル実装レポート](../SKILL_IMPLEMENTATION_REPORT.md)
* [バッチ処理実装レポート](./IMPLEMENTATION_REPORT_BATCH.md)
* [武器属性と距離適正実装レポート](../ADVANCED_BATTLE_LOGIC_REPORT.md)
* [地形適正と索敵システム実装レポート](../TERRAIN_DETECTION_IMPLEMENTATION_REPORT.md)
* [リソース管理システム実装レポート](../RESOURCE_MANAGEMENT_IMPLEMENTATION.md)
* [Phase 2.5 UI実装完了報告](../PHASE_2_5_COMPLETION_REPORT.md)
* [バトルビューア視覚表現強化](../IMPLEMENTATION_SUMMARY_BATTLE_VIEWER.md)
* [ダッシュボード改善レポート](../DASHBOARD_IMPLEMENTATION_REPORT.md)
* [バトルビューアー強化詳細](../BATTLE_VIEWER_ENHANCEMENTS.md)
* [ランキング・視察機能](./reports/RANKING_IMPLEMENTATION_SUMMARY.md)
* [エースパイロット・NPC性格](./reports/ACE_PILOT_IMPLEMENTATION_SUMMARY.md)

### UI/UX ガイド
* [UI Mockups](../UI_MOCKUPS.md)
* [UI実装サマリー](../UI_IMPLEMENTATION_SUMMARY.md)
* [UI Visual Mockup](../UI_VISUAL_MOCKUP.md)
* [SciFiデザインシステム](../SF_DESIGN_IMPLEMENTATION_SUMMARY.md)
* [SciFi UIコンポーネントガイド](../SF_UI_COMPONENTS_GUIDE.md)
* [Phase 2.5 UI比較](../PHASE_2_5_UI_COMPARISON.md)
* [Phase 2.5 UI実装ガイド](../PHASE_2_5_UI_IMPLEMENTATION.md)
* [バトルビューア視覚ガイド](../VISUAL_GUIDE_BATTLE_VIEWER.md)
* [Tactics UI Mockup](./tactics-ui-mockup.html)