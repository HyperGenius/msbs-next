---
title: '[Feature]: バトルログ改善 - 武装・装甲情報の明示'
labels: enhancement, ux, battle-log
---

## 概要

攻撃ログに使用武器名を明示し、「何を使って攻撃しているか」をプレイヤーが把握できるようにする。
クールタイム中・EN不足時の待機理由を具体的に表現し、カスタマイズの影響を実感させる。
装甲ダメージ軽減メッセージをバトルの文脈に自然に溶け込ませる。

## 目的

- プレイヤーが選択・強化した武器が実際にどう機能しているかをログで確認できるようにする
- 武器が使えなかった理由（クールタイム・EN不足）をログで明示し、次の編成判断に役立てる
- 装甲軽減が「システム的な注釈」ではなく「戦闘描写の一部」として読めるようにする

## 要件

### 1. 攻撃ログへの武器名明示

- **仕様詳細:**
  - `_process_attack` が呼ばれる際に使用した `weapon.name` をログメッセージに組み込む
  - 形式: `[パイロット名]のMS名が[武器名]で攻撃！`
  - 武器が設定されていない場合（格闘など）は `[格闘]` と表記するか、武器名なしで自然な表現にする
- **特殊なルールや例外処理:**
  - `actor.get_active_weapon()` が `None` を返した場合は `[格闘攻撃]` と表記
  - 武器名が空文字の場合は武器種別（`weapon.weapon_type`）を使用する

**【改善イメージ】**

```
❌ 現状:
Gelgoogの攻撃！ (最適距離!) -> 命中！ AcguyにXXダメージ！

⭕️ 改善後:
[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！ -> 最適射程でクリーンヒット！ Acguyに大ダメージ！
```

### 2. 武器使用不能時の理由表現

- **仕様詳細:**
  - `_check_attack_resources` での失敗理由をログに自然な表現で組み込む
  - クールタイム中: `[武器名]はまだ冷却中（残りXターン）のため、次善策を選択`
  - EN不足: `[武器名]を使いたいがENが不足しているため、待機`
  - 弾切れ: `[武器名]の弾薬が尽きており、攻撃手段がない`
- **特殊なルールや例外処理:**
  - 現状は `"{actor.name}は{failure_reason}のため攻撃できない（待機）"` という表現を改善する
  - 待機ではなく最適でない武器で攻撃した場合もその旨を表現する

**【改善イメージ】**

```
❌ 現状:
Gelgoogはクールダウン中 (残り2ターン)のため攻撃できない（待機）

⭕️ 改善後:
[マ・クベ]のGelgoogは[ジャイアント・バズ]の冷却を待ちながら（残り2ターン）、やむなく待機
```

```
❌ 現状:
GelgoogはEN不足のため攻撃できない（待機）

⭕️ 改善後:
[マ・クベ]のGelgoogはENが枯渇し、[ビーム・サーベル]を使えず待機中
```

### 3. 装甲ダメージ軽減表現の文脈への溶け込み

- **仕様詳細:**
  - 現状の `[対実弾装甲により12%軽減]` というカッコ書きを廃止し、ダメージ描写の一部として表現する
  - 軽減率が高い場合（20%以上）: 装甲の強さを強調する表現
  - 軽減率が低い場合（10%未満）: さらっと触れる程度の表現
  - ビーム/実弾の属性を自然な言葉に置き換える（`対ビーム装甲` → `ビーム吸収コーティング` など）
- **特殊なルールや例外処理:**
  - `resistance` の数値が 0 の場合は装甲軽減の言及をしない
  - `resistance_msg` の生成箇所（`simulation.py` の `_process_hit` 内）を改修する

**【改善イメージ】**

```
❌ 現状:
Gelgoogの攻撃！ -> 命中！ [対実弾装甲により12%軽減] AcguyにXXダメージ！

⭕️ 改善後 (高軽減):
[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！
-> 命中！ しかしAcguyの強固な対実弾装甲が衝撃を受け止め、ダメージは軽微に！

⭕️ 改善後 (低軽減):
[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！
-> 命中！ Acguyの装甲をわずかに弾きながらも、大ダメージ！
```

## 技術的な実装方針

### Backend (`backend/`)

1. **ロジック・サービス (`backend/app/engine/simulation.py`):**

   **攻撃ログへの武器名追加:**
   ```python
   # _process_attack 内の log_base 生成箇所を変更
   # 変更前:
   log_base = f"{actor.name}の攻撃！{distance_msg} (命中: {int(hit_chance)}%)"
   # 変更後:
   weapon_display = f"[{weapon.name}]" if weapon and weapon.name else "[格闘]"
   log_base = f"{self._format_actor_name(actor)}が{weapon_display}で攻撃！{distance_msg}"
   ```

   **待機理由ログの改善:**
   ```python
   # _check_attack_resources の返り値（failure_reason）を拡張し、
   # 武器名を含む自然な文字列を生成する
   # 変更前の生成箇所:
   message=f"{actor.name}は{failure_reason}のため攻撃できない（待機）"
   # 変更後:
   message=f"{self._format_actor_name(actor)}は{failure_reason}、やむなく待機"
   ```

   **装甲軽減メッセージの改善:**
   ```python
   # _process_hit 内の resistance_msg 生成箇所を変更
   # resistance が 0.2 以上（高軽減）:
   #   "しかし{target.name}の強固な対{attr}装甲が衝撃を受け止め、ダメージは軽微に！"
   # resistance が 0.2 未満（低軽減）:
   #   "{target.name}の装甲をわずかに弾きながらも"
   ```

2. **データ定義・モデル:**
   - `BattleLog` モデルに `weapon_name: str | None` フィールドを追加すると、フロントエンド側での武器情報活用が容易になる（任意）

### Frontend (`frontend/`)

1. **型定義 (`frontend/src/types/battle.ts`):**
   - `BattleLog` 型に `weapon_name?: string` を追加（バックエンド対応時）

2. **ログ整形 (`frontend/src/utils/logFormatter.ts`):**
   - `getLogStyle` での武器属性判定を武器名に基づくロジックに更新（ビーム系・実弾系）
   - 装甲軽減メッセージの旧形式（`[対XXX装甲によりYY%軽減]`）に対応するスタイルを更新

3. **テスト (`frontend/tests/unit/logFormatter.test.ts`):**
   - 武器名を含む新形式のメッセージに対するスタイル判定テストを追加

## 完了条件 (Acceptance Criteria)

- [ ] 攻撃ログに使用した武器名が `[武器名]` 形式で含まれる
- [ ] 武器が存在しない場合は `[格闘]` と表示される
- [ ] クールタイム中の待機ログに武器名と残りターン数が含まれる
- [ ] EN不足の待機ログに武器名が含まれ、EN枯渇の状況が表現される
- [ ] 装甲軽減メッセージがカッコ書きではなく戦闘描写の一文として表現される
- [ ] 装甲軽減率の高低に応じてメッセージのトーンが変わる
- [ ] 既存の `logFormatter.test.ts` が全てパスし、新規ケースのテストが追加されている

## 作業のヒント・メモ

> [!TIP]
> - `_check_attack_resources` の返り値 `(success: bool, failure_reason: str)` を確認
> - `_process_hit` 内の `resistance_msg` 生成箇所（`simulation.py` 670–690行付近）を参照
> - `actor.get_active_weapon()` は `weapon: Weapon | None` を返す
> - `weapon.weapon_type` は `"BEAM"` または `"PHYSICAL"` などの文字列
> - 装甲軽減の属性: `BEAM` → `ビーム`, `PHYSICAL` → `実弾` の対応

## 関連Issue

- Epic: バトルログUX改善（[README.md](./README.md)）
- Sub-Issue: [01_pilot_presence.md](./01_pilot_presence.md)（パイロット名フォーマット関数を共有）
- Sub-Issue: [03_tactics_feedback.md](./03_tactics_feedback.md)
