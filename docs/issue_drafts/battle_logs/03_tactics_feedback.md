---
title: '[Feature]: バトルログ改善 - 戦術フィードバックの改善'
labels: enhancement, ux, battle-log
---

## 概要

ターゲット選択ログや距離情報を、事務的なカッコ書きから戦闘の文脈として自然に溶け込む表現へと改善する。
「なぜその相手を狙ったのか」「なぜ命中しなかったのか（距離・地形など）」をログから論理的に読み取れるようにし、プレイヤーの次戦における戦術改善を促す。

## 目的

- 「事務的な戦術ログ」から「行動理由が伝わるナラティブログ」への転換
- プレイヤーが戦術（`CLOSEST`, `WEAKEST` など）の効果を体感し、次の編成・戦術変更の動機付けとなる
- 距離や地形の不利が「システムメッセージ」ではなく戦闘描写として伝わる

## 要件

### 1. ターゲット選択ログの自然な表現

- **仕様詳細:**
  - `_log_target_selection` の出力形式を改善する
  - 戦術ラベルを日本語の自然な表現にマッピングする:
    - `CLOSEST` → `近距離優先`
    - `WEAKEST` → `弱体ターゲット優先`
    - `STRONGEST` → `高脅威ターゲット優先`
    - `THREAT` → `最大脅威優先`
    - `RANDOM` → `ランダム選択`
  - 距離・HP などの付加情報を括弧書きではなく文章に組み込む
- **特殊なルールや例外処理:**
  - 戦術名が不明な場合は従来形式にフォールバックする
  - `details` パラメータの形式（`HP: XX`, `距離: XXXm` など）に応じて文章テンプレートを選択する

**【改善イメージ】**

```
❌ 現状:
Gelgoogがターゲット選択: Acguy (NPC) (戦術: CLOSEST, 距離: 中距離)

⭕️ 改善後:
[マ・クベ]のGelgoogは[戦術: 近距離優先]に従い、中距離にいるAcguy (NPC)をターゲットに捕捉！
```

```
❌ 現状:
Gundamがターゲット選択: Zaku (NPC) (戦術: WEAKEST, HP: 45)

⭕️ 改善後:
[アムロ]のGundamは[戦術: 弱体ターゲット優先]でスキャン。HP残量わずかなZaku (NPC)を狙い撃ちにする！
```

### 2. 距離・命中修正の自然な組み込み

- **仕様詳細:**
  - 現状の `(最適距離!)`, `(距離不利)` などの括弧表現を廃止し、攻撃結果の文脈に組み込む
  - 命中した場合: 距離が最適であればその旨を称える表現に
  - 回避された場合: 距離の不一致を回避理由として自然に表現する
  - `distance_msg` の生成方法（`simulation.py` 内）を見直す
- **特殊なルールや例外処理:**
  - `distance_from_optimal` の値に応じてメッセージトーンを変える（0 → 絶好の距離、高い → 射程外）
  - 命中率の数値はプロダクション表示では非表示（既存の `removeHitRate` で対応済み）

**【改善イメージ】**

```
❌ 現状:
Gelgoogの攻撃！ (最適距離!) -> 命中！ AcguyにXXダメージ！

⭕️ 改善後:
[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！ -> 最適射程でクリーンヒット！ Acguyに大ダメージ！
```

```
❌ 現状:
Gelgoogの攻撃！ (距離不利) -> 回避された！

⭕️ 改善後:
[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！ -> 距離が合わず、Acguyに回避された！
```

### 3. 索敵・発見ログの演出強化

- **仕様詳細:**
  - `{unit.name}が{target.name}を発見！ (距離: {int(distance)}m)` を演出重視の表現に変更
  - ミニョフスキー粒子の影響がある場合は特別な表現を追加
  - 索敵失敗（範囲外）の場合も「見えない敵の気配」を示すログを追加（任意）
- **特殊なルールや例外処理:**
  - `minovsky_msg` が空の場合はシンプルな発見表現
  - `minovsky_msg` がある場合はその内容を自然な文に組み込む

**【改善イメージ】**

```
❌ 現状:
Gelgoogがリック・ドムを発見！ (距離: 320m) [ミノフスキー粒子濃度高]

⭕️ 改善後:
[マ・クベ]のGelgoogが濃密なミノフスキー粒子の中、中距離にリック・ドムの反応を捉えた！
```

## 技術的な実装方針

### Backend (`backend/`)

1. **ロジック・サービス (`backend/app/engine/simulation.py`):**

   **ターゲット選択ログの改善:**
   ```python
   TACTICS_LABEL = {
       "CLOSEST": "近距離優先",
       "WEAKEST": "弱体ターゲット優先",
       "STRONGEST": "高脅威ターゲット優先",
       "THREAT": "最大脅威優先",
       "RANDOM": "ランダム選択",
   }

   def _log_target_selection(self, actor, target, reason, details):
       label = TACTICS_LABEL.get(reason, reason)
       actor_name = self._format_actor_name(actor)
       # details の形式に応じてテンプレートを選択
       if reason == "CLOSEST":
           message = f"{actor_name}は[戦術: {label}]に従い、{details}にいる{target.name}をターゲットに捕捉！"
       elif reason == "WEAKEST":
           message = f"{actor_name}は[戦術: {label}]でスキャン。{details}の{target.name}を狙い撃ちにする！"
       # ... 各戦術に応じたテンプレート
   ```

   **距離修正メッセージの改善:**
   ```python
   # _process_attack 内の distance_msg 生成を改善
   # 変更前:
   #   distance_msg = " (最適距離!)" or " (距離不利)"
   # 変更後:
   #   is_optimal_distance: bool フラグとして保持し、命中/ミス判定後に
   #   メッセージに織り込む
   ```

   **索敵ログの改善:**
   ```python
   # _detection_phase 内の発見ログを改善
   # 変更前:
   f"{unit.name}が{target.name}を発見！ (距離: {int(distance)}m){minovsky_msg}"
   # 変更後: 距離を抽象化し、ミニョフスキー粒子の状況を文中に溶け込ませる
   ```

### Frontend (`frontend/`)

1. **ログ整形 (`frontend/src/utils/logFormatter.ts`):**
   - `abstractDistance` 関数は引き続き有効（数値距離のフォールバック用）
   - ターゲット選択ログ（`action_type === "TARGET_SELECTION"`）に対するスタイルを追加
   - 索敵ログ（`action_type === "DETECTION"`）の新形式に合わせてスタイル判定を更新

## 完了条件 (Acceptance Criteria)

- [ ] ターゲット選択ログが自然な日本語の文章として表示される
- [ ] 戦術ラベルが `CLOSEST` → `近距離優先` などの日本語に対応している
- [ ] 命中時・ミス時のログに距離状況が自然に組み込まれている
- [ ] 索敵成功ログが演出的な表現に改善されている
- [ ] ミニョフスキー粒子の影響がある場合、その情報が文中に組み込まれている
- [ ] 既存の `logFormatter.test.ts` が全てパスし、新規ケースのテストが追加されている

## 作業のヒント・メモ

> [!TIP]
> - `_log_target_selection` メソッド（`simulation.py` 190行付近）を参照
> - `_detection_phase` メソッド内の発見ログ生成（`simulation.py` 250–265行付近）を参照
> - `distance_msg` は `_process_attack` 内で生成される（`simulation.py` 530–545行付近）
> - `_select_target` で各戦術の `details` パラメータとして渡される値の形式を確認
>   - `CLOSEST`: `f"距離: {int(distance)}m"`
>   - `WEAKEST`: `f"HP: {target.current_hp}"`
>   - `STRONGEST`: `f"戦略価値: {strategic_value:.1f}"`
>   - `THREAT`: `f"脅威度: {threat_level:.2f}"`

## 関連Issue

- Epic: バトルログUX改善（[README.md](./README.md)）
- Sub-Issue: [01_pilot_presence.md](./01_pilot_presence.md)（`_format_actor_name` 関数を共有）
- Sub-Issue: [02_weapon_armor_display.md](./02_weapon_armor_display.md)
- Sub-Issue: [04_damage_gradation.md](./04_damage_gradation.md)
