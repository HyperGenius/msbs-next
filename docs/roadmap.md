# Project Roadmap: MSBS-Next (仮)

ブラウザベースの定期更新型MSバトルシミュレーションゲームの開発ロードマップです。
MSBSのプレイ感を現代的なクラウドネイティブ技術で再現・進化させることを目的とします。

## 1. プロジェクト概要

* **ジャンル:** 定期更新型タクティカルバトルシミュレーション (PvPvE)
* **プラットフォーム:** Webブラウザ (PC/Mobile)
* **コア体験:** MSカスタマイズ → 戦術設定 → 自動シミュレーション → バトルログ確認

## 2. 技術スタック

| 領域 | 技術 | 状態 |
|------|------|------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS | ✅ 稼働中 |
| Backend | Python (FastAPI), Pydantic v2, SQLModel | ✅ 稼働中 |
| Simulation | NumPy (ベクトル計算), Pure Python Logic | ✅ 実装済 |
| Database | Neon (PostgreSQL), Alembic (マイグレーション) | ✅ 稼働中 |
| Auth | Clerk (JWT/JWKS) | ✅ 実装済 |
| Visuals | React Three Fiber (@react-three/fiber, drei) | ✅ 実装済 |
| Infra | Terraform (Neon), Vercel (Frontend), Render (Backend予定) | 🔧 一部構築済 |

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

### Phase 1: MVP (Minimum Viable Product) 🔧 進行中
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
* **Backend (FastAPI):**
    * [x] バトル実行APIエンドポイントの実装。
        * `POST /api/battle/simulate` - プレイヤー機体 vs 敵3機の戦闘
    * [x] 機体管理API。
        * `GET /api/mobile_suits` - 機体一覧取得
        * `PUT /api/mobile_suits/{ms_id}` - 機体更新（認証必須）
    * [ ] バトル結果のDB保存 (JSONBカラム活用)。
    * [ ] 対戦相手の選択機能 (ランダム or ID指定)。
* **Game Logic:**
    * [x] 簡易戦闘の実装 (命中率計算、ダメージ計算、HP減少)。
        * 距離による命中率ペナルティ
        * 機動性による回避ボーナス
        * クリティカルヒット判定 (5%)
        * 装甲によるダメージ軽減
    * [x] 勝敗判定。
        * プレイヤー全滅 or 敵全滅で終了
* **Infrastructure:**
    * [x] Neon DB構築 (Terraform)。
        * `infra/neon/main.tf` - プロジェクト・ロール・DB作成
    * [x] Alembicマイグレーション。
        * `mobile_suits` テーブル（`side`カラム追加済）
    * [ ] Vercel/Render デプロイ設定。

### Phase 2: α版 (Visual & Strategy Update) 🔧 一部先行実装
**ゴール:** 視覚的な面白さと戦術性の向上。

* **Visuals:**
    * [x] **3Dリプレイ (Three.js/R3F):** バトルログJSONを解析し、ブラウザ上で3D表示。
        * `frontend/src/components/BattleViewer.tsx`
        * 球体でMS表現 (HP残量で色変化: 緑→黄→赤)
        * ターンスライダーで任意時点の状態を確認可能
        * HPバー付きUIオーバーレイ
        * Stars, Grid背景
* **Logic:**
    * [ ] **AI/戦術設定:** 「HP50%以下で回避優先」「遠距離重視」などの行動パターンの実装。
    * [ ] **成長要素:** 戦闘後の経験値獲得とパイロットステータス上昇。

### Phase 3: β版 (Community & Expansion)
**ゴール:** 定期更新ゲームとしての体裁を整える。

* **System:**
    * [ ] **定期更新自動化:** 指定時間に対戦キューを一括処理するバッチ処理 (GitHub Actions / Render Cron)。
    * [ ] **ランキング:** 勝敗数や撃墜数によるランキング集計。
* **Content:**
    * [ ] 勢力 (Faction) の導入。
    * [ ] MS/武器のバリエーション追加。

### Phase 4: 正式サービス (Monetization)
**ゴール:** 収益化と運営体制の確立。

* **Economy:**
    * [ ] Stripe決済導入。
    * [ ] アバター/スキン等のコスメティックアイテム販売。
* **Ops:**
    * [ ] 運営管理画面の整備。

---

## 4. シミュレーション仕様 (実装済)

物理エンジンは使用せず、数学的な計算のみで処理する。

* **フィールド:**
    * 境界なしの3D空間 (現状)。
    * 障害物は未実装。
* **移動:**
    * 慣性は考慮せず、毎ターン `mobility × 基本速度` 分だけターゲット方向へベクトル移動。
    * 移動速度: `max(5.0, mobility * 50)`
* **判定:**
    * **ターゲット選択:** 最も近い敵対勢力ユニットを選択。
    * **攻撃:** 射程内であれば攻撃、そうでなければ移動。
    * **命中率:** `base_accuracy - (distance/100)*2 - (target.mobility * 10)`
    * **ダメージ:** `max(1, weapon.power - target.armor) * variance(0.9~1.1)`
    * **クリティカル:** 5%確率で `power * 1.2` (装甲無視)

## 5. データモデル (実装済)

### mobile_suits テーブル
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
| position | JSON | Vector3 |
| velocity | JSON | Vector3 |
| weapons | JSON | Weapon[] |
| active_weapon_index | Integer | 選択中武器 |

### 今後追加予定
* `users`: ユーザー基本情報
* `pilots`: パイロットステータス (メイン/サブ)
* `battle_logs`: 戦闘結果 (JSONB - リプレイデータ含む)
* `factions`: 勢力情報

---

## 6. テスト

* **Unit Tests:** `backend/tests/unit/test_simulation.py`
    * シミュレータ初期化テスト
    * ターン順序テスト（機動性順）
    * プレイヤー勝利シナリオテスト
    * 敵勝利シナリオテスト
    * 移動ロジックテスト
    * 攻撃命中率テスト

---

## 7. ドキュメント

* [Clerk認証セットアップガイド](./CLERK_SETUP.md)
* [Clerk実装サマリー](./CLERK_IMPLEMENTATION_SUMMARY.md)
* [Neonマイグレーションガイド](./neon_migration.md)
* [インフラ構成](./infra.md)
* [Mobile Suit API仕様](./mobile-suit-api-implementation.md)