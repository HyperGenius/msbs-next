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

### Phase 2: α版 (PvPvE Battle Royale) 🔧 一部先行実装
**ゴール:** 複数プレイヤー + NPCが入り乱れるバトルロイヤル形式の実現。

#### 2-1. 3Dビジュアル基盤 ✅ 先行実装済
* **Visuals:**
    * [x] **3Dリプレイ (Three.js/R3F):** バトルログJSONを解析し、ブラウザ上で3D表示。
        * `frontend/src/components/BattleViewer.tsx`
        * 球体でMS表現 (HP残量で色変化: 緑→黄→赤)
        * ターンスライダーで任意時点の状態を確認可能
        * HPバー付きUIオーバーレイ
        * Stars, Grid背景
    * [ ] **多人数対応ビューア:** 10機以上の同時表示、プレイヤー/NPC色分け

#### 2-2. バトルロイヤル・コアシステム
* **マッチング:**
    * [ ] **バトルエントリー:** プレイヤーが「次回更新」に参加登録するAPI
    * [ ] **バトルルーム:** 参加者をグループ化（例: 8プレイヤー + 4〜8 NPC）
    * [ ] **スポーン配置:** フィールド外周にランダム or 均等配置

* **Simulation拡張:**
    * [ ] **N体シミュレーション:** 任意のユニット数（12〜16機）を処理可能に
    * [ ] **陣営ロジック拡張:** 
        * PLAYER (各ユーザー) - 自分以外すべて敵
        * NPC - 全プレイヤーを敵として行動
    * [ ] **ターゲット選択AI:** 最寄りの敵 / HP最低の敵 / 脅威度順 など選択可能
    * [ ] **撃墜順位記録:** 脱落順で順位を確定（1位 = 最後の生存者）

* **フィールド:**
    * [ ] **円形/球形フィールド:** 境界ありの戦闘空間（例: 半径2000m）
    * [ ] **収縮システム（オプション）:** ターン経過でフィールド縮小、範囲外ダメージ

#### 2-3. 定期更新システム
* **バッチ処理:**
    * [ ] **更新スケジュール:** 1日1〜2回の定期更新（例: 12:00, 21:00）
    * [ ] **バトル一括実行:** エントリー済みルームを順次シミュレート
    * [ ] **結果通知:** バトル完了後、参加者に結果を通知（メール or Webhook）

* **Infrastructure:**
    * [ ] GitHub Actions / Render Cron によるスケジュール実行
    * [ ] バトルキュー管理（Redis or DB）

#### 2-4. AI/戦術設定
* **Logic:**
    * [ ] **行動パターン:** 「HP50%以下で回避優先」「遠距離維持」「積極攻撃」
    * [ ] **ターゲット優先度:** 「最寄り」「瀕死優先」「脅威度順」
    * [ ] **NPCバリエーション:** 雑魚/エース/ボス級など難易度差

#### 2-5. 成長・報酬システム
* **Progression:**
    * [ ] **戦闘後経験値:** 順位・撃墜数に応じてEXP付与
    * [ ] **パイロットステータス:** レベルアップで能力値上昇
    * [ ] **報酬:** 順位に応じた資金・アイテム獲得

### Phase 3: β版 (Community & Content)
**ゴール:** コンテンツ拡充とコミュニティ機能の整備。

* **ランキング & 統計:**
    * [ ] **シーズンランキング:** 累計ポイント・勝利数・撃墜数
    * [ ] **個人戦績:** 参加履歴、平均順位、K/D比
    * [ ] **リーダーボード:** Top100表示

* **Content:**
    * [ ] **勢力 (Faction):** 所属勢力ごとのボーナス・専用機体
    * [ ] **MS/武器バリエーション:** 機体・武器のアンロック/購入システム
    * [ ] **マップバリエーション:** 宇宙/地上/コロニー内など

* **Social:**
    * [ ] **フレンド機能:** フォロー、対戦履歴閲覧
    * [ ] **チーム戦（オプション）:** 2〜3人チームでのバトルロイヤル

### Phase 4: 正式サービス (Monetization & Ops)
**ゴール:** 収益化と安定運営体制の確立。

* **Economy:**
    * [ ] Stripe決済導入
    * [ ] プレミアムパス（シーズンパス）
    * [ ] コスメティックアイテム（スキン、エンブレム、称号）

* **Ops:**
    * [ ] 運営管理画面（ユーザー管理、バン、イベント設定）
    * [ ] 監視・アラート（エラー率、バトル処理時間）
    * [ ] CSツール（問い合わせ対応）

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

### 今後追加予定 (Phase 2: バトルロイヤル対応)

#### battle_rooms テーブル
| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | Primary Key |
| scheduled_at | Timestamp | 実行予定時刻 |
| status | String | WAITING / RUNNING / COMPLETED |
| max_players | Integer | 最大プレイヤー数 |
| npc_count | Integer | NPC数 |
| field_radius | Float | フィールド半径 |
| created_at | Timestamp | 作成日時 |

#### battle_entries テーブル
| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | Primary Key |
| room_id | UUID | FK → battle_rooms |
| user_id | String | Clerk User ID (NPC時はnull) |
| mobile_suit_id | UUID | FK → mobile_suits |
| is_npc | Boolean | NPCフラグ |
| spawn_position | JSON | 初期配置 Vector3 |
| final_rank | Integer | 最終順位 (nullable) |
| kills | Integer | 撃墜数 |
| damage_dealt | Integer | 総与ダメージ |

#### battle_results テーブル
| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | Primary Key |
| room_id | UUID | FK → battle_rooms |
| logs | JSONB | BattleLog[] |
| winner_entry_id | UUID | FK → battle_entries |
| total_turns | Integer | 総ターン数 |
| executed_at | Timestamp | 実行完了日時 |

#### pilots テーブル
| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | Primary Key |
| user_id | String | Clerk User ID |
| name | String | パイロット名 |
| level | Integer | レベル |
| exp | Integer | 経験値 |
| total_battles | Integer | 累計参加数 |
| total_wins | Integer | 累計1位回数 |
| total_kills | Integer | 累計撃墜数 |

#### factions テーブル (Phase 3)
| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | Primary Key |
| name | String | 勢力名 |
| bonus_type | String | ボーナス種別 |
| bonus_value | Float | ボーナス値 |

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