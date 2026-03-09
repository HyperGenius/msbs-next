---
title: '[Feature]: バトルログ改善 - パイロットの存在感強化'
labels: enhancement, ux, battle-log
---

## 概要

バトルログにパイロット名を組み込み、「誰が戦っているか」を明確にする。
未索敵の機体は `UNKNOWN` として表示し、正体不明機からの攻撃を演出する。
スキル発動時はその戦局への影響を強調する。

## 目的

- プレイヤーが手塩にかけて育てたパイロットが戦っていることを実感させる
- 「機体同士の戦闘」から「パイロットが駆る機体の戦闘」へと没入感を高める
- スキルの育成効果がログ上でも可視化され、育成への動機付けとなる

## 要件

### 1. パイロット名の組み込み

- **仕様詳細:**
  - `actor.pilot_name` が存在する場合、ログの機体名を `[パイロット名]のMS名` 形式で表示する
  - `actor.pilot_name` が存在しない場合（NPC など）は従来通り機体名のみを表示する
  - 対象ログ: 攻撃・命中・ミス・破壊・ターゲット選択・移動 など全アクションログ
- **特殊なルールや例外処理:**
  - パイロット名が空文字列の場合は機体名のみ表示（NPCとの一貫性）
  - プレイヤー機体の場合は「自機」表示も選択肢として検討（後続Issueにて判断）

**【改善イメージ】**

```
❌ 現状:
Gelgoogの攻撃！ -> 命中！ AcguyにXXダメージ！

⭕️ 改善後:
[マ・クベ]のGelgoogが攻撃！ -> 命中！ Acguyに大ダメージ！
```

### 2. 未索敵機体の `UNKNOWN` 表示

- **仕様詳細:**
  - 攻撃を受けた際に `actor` がプレイヤーチームの索敵範囲外の場合、ログ上の `actor` 表記を `UNKNOWN` に置き換える
  - 「`UNKNOWN`機が攻撃！」のような表現でサスペンス感を演出する
  - 索敵フェーズで発見された後は通常のパイロット名・機体名表示に戻る
- **特殊なルールや例外処理:**
  - `team_detected_units` の状態を参照して判定する
  - ミニョフスキー粒子濃度が高い場合は発見後も一定確率で `UNKNOWN` 維持（将来拡張）

**【改善イメージ】**

```
⭕️ 改善後:
UNKNOWN機から攻撃！ -> 命中！ [自機]のGelgoogに軽微なダメージ！
```

### 3. スキル発動ログの強化

- **仕様詳細:**
  - パイロットスキル（`accuracy_up`, `evasion_up` など）が命中率・回避率に影響した場合、ログにその旨を追記する
  - スキルが攻撃の成否を決定的に変えたと推定される場合（命中率が閾値を境にする場合）は特別な強調表示を行う
- **特殊なルールや例外処理:**
  - スキルボーナスが 0 の場合はログに追記しない
  - 強調条件: スキルボーナス適用前後で命中/回避の判定が反転する場合

**【改善イメージ】**

```
⭕️ 改善後 (通常):
[アムロ]のGundamが[ビーム・ライフル]で攻撃！ -> 命中！ Zakuに大ダメージ！

⭕️ 改善後 (スキル強調):
[アムロ]のGundamが[ビーム・ライフル]で攻撃！
  ★ [直感LV3]が発動し、絶妙なタイミングで照準！ -> 命中！ Zakuに大ダメージ！
```

## 技術的な実装方針

### Backend (`backend/`)

1. **データ定義・モデル:**
   - `BattleLog` モデルに `pilot_name: str | None` フィールドを追加（`backend/app/models/models.py`）
   - `MobileSuit` の `pilot_name` 属性が既に存在する（`actor.pilot_name`）ため参照可能

2. **ロジック・サービス (`backend/app/engine/simulation.py`):**
   - `_format_actor_name(actor: MobileSuit) -> str` ヘルパー関数を追加:
     ```python
     def _format_actor_name(self, actor: MobileSuit, viewer_team_id: str | None = None) -> str:
         # 未索敵チェック
         if viewer_team_id and actor.id not in self.team_detected_units.get(viewer_team_id, set()):
             return "UNKNOWN"
         if actor.pilot_name:
             return f"[{actor.pilot_name}]の{actor.name}"
         return actor.name
     ```
   - 全ログ生成箇所（`_log_target_selection`, `_process_attack`, `_process_hit`, `_process_miss`, `_process_destruction`, `_process_movement`）で `_format_actor_name` を使用するよう変更
   - スキルボーナス適用時に `skill_activated: bool` フラグを `BattleLog` に付加し、フロントエンドで強調表示できるようにする

3. **APIエンドポイント:**
   - 既存の `/api/battle/simulate` エンドポイントは変更不要（`BattleLog` の拡張のみ）

### Frontend (`frontend/`)

1. **型定義 (`frontend/src/types/battle.ts`):**
   - `BattleLog` 型に `pilot_name?: string` および `skill_activated?: boolean` を追加

2. **ログ整形 (`frontend/src/utils/logFormatter.ts`):**
   - `formatBattleLog` において `UNKNOWN` 表示のロジックを追加
   - `skill_activated === true` の場合に `★` プレフィックスを付与するスタイルロジックを追加

3. **表示スタイル (`frontend/src/components/history/BattleLogViewer.tsx`):**
   - スキル発動ログ（`skill_activated === true`）に対してゴールド系のハイライトを適用

## 完了条件 (Acceptance Criteria)

- [ ] パイロット名がある機体のアクションログが `[パイロット名]のMS名` 形式で表示される
- [ ] パイロット名がない機体（NPC）のアクションログは従来通りMS名のみ表示される
- [ ] 未索敵機体のログが `UNKNOWN機` として表示される
- [ ] 索敵成功後は `UNKNOWN` から実名表示に切り替わる
- [ ] スキル発動が命中判定に影響した場合、ログに `★` 付きの強調メッセージが追記される
- [ ] 既存の `logFormatter.test.ts` が全てパスし、新規ケースのテストが追加されている

## 作業のヒント・メモ

> [!TIP]
> - `backend/app/engine/simulation.py` の `_log_target_selection`, `_process_attack`, `_process_hit`, `_process_miss` など各ログ生成メソッドを参照
> - `actor.pilot_name` は `MobileSuit` モデルに定義済み（`getattr(target, 'pilot_name', 'Unknown')` での参照例が `_process_destruction` 付近に存在）
> - `team_detected_units` は `dict[str, set[uuid.UUID]]` 形式でチームIDと索敵済みユニットIDを管理
> - フロントエンドの `formatBattleLog` はバックエンドから受け取った `message` 文字列を整形するため、バックエンド側でメッセージを改善するアプローチが効果的

## 関連Issue

- Epic: バトルログUX改善（[README.md](./README.md)）
- Sub-Issue: [02_weapon_armor_display.md](./02_weapon_armor_display.md)
