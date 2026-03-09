---
title: '[Feature]: バトルログ改善 - 戦況グラデーション表現の強化'
labels: enhancement, ux, battle-log
---

## 概要

ダメージ量・HP残量・装甲との相性などの内部計算結果をログのテキストバリエーションとして表現し、
「大ダメージ」「軽微なダメージ」といった結果に対して、なぜそうなったのかを匂わせる記述を加える。
これにより、プレイヤーは次戦で「同じ武器でも状況次第で効果が変わる」ことを体感し、戦術的な試行錯誤を促す。

## 目的

- ダメージの大小に「理由のある表現」を付与し、納得感を生む
- HP残量に応じて「追い詰められている感」や「余裕がある感」をログで演出する
- クリティカルヒット・完全回避などの特殊ケースをドラマティックに表現する

## 要件

### 1. ダメージ量のグラデーション表現

- **仕様詳細:**
  - 現在の `damage >= 100 → 大ダメージ`, `>= 30 → ダメージ`, `< 30 → 軽微なダメージ` の3段階を維持しつつ、状況説明を追加する
  - `max_hp` に対するダメージ割合（`damage / target.max_hp`）でさらに細かく表現を分ける:
    - 20%以上: 致命的なダメージ
    - 10%以上: 手痛いダメージ
    - 5%以上: ダメージ
    - 5%未満: 軽微なダメージ
  - テキストバリエーションを複数用意し、ランダムまたは状況によって選択する

- **特殊なルールや例外処理:**
  - `target.max_hp` が 0 の場合は割合計算をスキップし、絶対値ベースの判定を使用
  - 既存の `abstractDamage` 関数（`logFormatter.ts`）の閾値と整合性を保つ

**【改善イメージ】**

```
❌ 現状:
Gelgoogの攻撃！ -> 命中！ Acguyに150ダメージ！

⭕️ 改善後 (HP20%以上消耗):
[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！
-> 致命的なヒット！ AcguyのHPを大きく削り取った！（大ダメージ）

⭕️ 改善後 (HP5%未満消耗):
[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！
-> 命中するも、Acguyの機体には軽微なダメージに留まった。
```

### 2. HP残量に応じた戦況表現

- **仕様詳細:**
  - ダメージを受けた後のターゲットのHP残量割合（`current_hp / max_hp`）に応じて状況コメントを追加する:
    - 20%以下: `（残りHP僅少！次の一撃が勝負）` のような緊張感の演出
    - 50%以下: `（戦闘継続能力が低下）`
    - 80%以上: `（まだ余裕がある）`（省略してもよい）
  - ターゲットが破壊寸前（HP <= 10%）の場合は特別な演出を追加
- **特殊なルールや例外処理:**
  - HP残量コメントはオプション表示（ログが長くなりすぎる場合は折りたたむ）
  - 既存の `_process_destruction` で爆散ログは生成されるため、そちらとの重複に注意

**【改善イメージ】**

```
⭕️ 改善後:
[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！
-> 命中！ Acguyに大ダメージ！ — 機体が大破寸前...！（残りHP僅少）
```

### 3. クリティカルヒット・完全回避の演出強化

- **仕様詳細:**
  - クリティカルヒット時（現状: `-> クリティカルヒット！！`）に戦況の転換を示す演出を追加
  - 完全回避時（LUK による奇跡的回避、現状: `-> 命中！ しかし{target.name}は奇跡的に回避した！`）の表現をさらに劇的に
  - スキル発動による特殊ケース（01_pilot_presence.md と連携）

- **特殊なルールや例外処理:**
  - クリティカル判定は `INT` ステータスに依存（`simulation.py` 内の `_process_hit` を参照）
  - 完全回避（LUK 判定）は `player_pilot_stats.luk` の値が影響

**【改善イメージ】**

```
❌ 現状:
Gundamの攻撃！ -> クリティカルヒット！！ ZakuにXXダメージ！

⭕️ 改善後:
[アムロ]のGundamが[ビーム・ライフル]で攻撃！
-> ★★ クリティカルヒット！！ 弱点を的確に捉え、Zakuに致命的なダメージ！
   （装甲を貫通し、HPを大幅に削り取った！）
```

```
❌ 現状:
Gundamの攻撃！ -> 命中！ しかしZakuは奇跡的に回避した！

⭕️ 改善後:
[アムロ]のGundamが[ビーム・ライフル]で攻撃！
-> 直撃コース！ しかし[シャア]のZakuは信じられない反射神経で紙一重の回避！
   ★ [LUK]の奇跡が働いた！
```

### 4. `logFormatter.ts` の `abstractDamage` 拡張

- **仕様詳細:**
  - 現状の `abstractDamage` はダメージ数値を単純な3段階ラベルに変換するだけだが、
    コンテキスト（`target.max_hp` に対する割合）を考慮した変換ができるよう拡張する
  - `BattleLog` に `target_max_hp?: number` フィールドを追加（バックエンドから送信）し、
    フロントエンドで割合計算を行う
- **特殊なルールや例外処理:**
  - `target_max_hp` が未提供の場合は既存の絶対値ベース判定にフォールバック
  - `isProduction === false`（開発モード）では変換しない（既存の挙動を維持）

## 技術的な実装方針

### Backend (`backend/`)

1. **データ定義・モデル (`backend/app/models/models.py`):**
   - `BattleLog` に `target_max_hp: int | None` フィールドを追加（フロントエンドでの割合計算に使用）

2. **ロジック・サービス (`backend/app/engine/simulation.py`):**

   **ダメージグラデーション計算の追加:**
   ```python
   def _get_damage_description(self, damage: int, target: MobileSuit) -> str:
       """HP割合ベースのダメージ表現を返す"""
       ratio = damage / max(1, target.max_hp)
       if ratio >= 0.20:
           return "致命的なヒット"
       elif ratio >= 0.10:
           return "手痛いダメージ"
       elif ratio >= 0.05:
           return "ダメージ"
       else:
           return "軽微なダメージ"
   ```

   **HP残量コメントの追加:**
   ```python
   def _get_hp_status_comment(self, target: MobileSuit) -> str:
       ratio = target.current_hp / max(1, target.max_hp)
       if ratio <= 0.10:
           return " — 大破寸前...！（残りHP僅少）"
       elif ratio <= 0.20:
           return " — 機体が限界に近い！"
       elif ratio <= 0.50:
           return " — 戦闘継続能力が低下"
       return ""
   ```

   **クリティカル・完全回避ログの改善:**
   - `_process_hit` 内のクリティカル分岐でメッセージを改善
   - `_process_hit` 内の LUK 回避分岐でメッセージを改善

### Frontend (`frontend/`)

1. **型定義 (`frontend/src/types/battle.ts`):**
   - `BattleLog` 型に `target_max_hp?: number` を追加

2. **ログ整形 (`frontend/src/utils/logFormatter.ts`):**

   **`abstractDamage` の拡張:**
   ```typescript
   function abstractDamage(
     message: string,
     damage: number | undefined,
     targetMaxHp?: number
   ): string {
     if (damage === undefined) return message;
     let damageLabel: string;
     if (targetMaxHp && targetMaxHp > 0) {
       const ratio = damage / targetMaxHp;
       if (ratio >= 0.20) damageLabel = "致命的なダメージ";
       else if (ratio >= 0.10) damageLabel = "手痛いダメージ";
       else if (ratio >= 0.05) damageLabel = "ダメージ";
       else damageLabel = "軽微なダメージ";
     } else {
       damageLabel = damage >= 100 ? "大ダメージ" : damage >= 30 ? "ダメージ" : "軽微なダメージ";
     }
     return message
       .replace(/\d+\s*ダメージ/g, damageLabel)
       .replace(/ダメージ[：:]\s*\d+/g, damageLabel);
   }
   ```

3. **テスト (`frontend/tests/unit/logFormatter.test.ts`):**
   - `target_max_hp` を使った割合ベースのダメージラベル変換テストを追加
   - クリティカルヒット・完全回避ログのスタイル判定テストを追加

## 完了条件 (Acceptance Criteria)

- [ ] ダメージログがHP割合に基づいた4段階の表現（致命的・手痛い・通常・軽微）で表示される
- [ ] `target_max_hp` が未提供の場合、既存の3段階（大ダメージ・ダメージ・軽微）にフォールバックされる
- [ ] HP残量が20%以下の場合、ダメージログに残HP状況のコメントが付く
- [ ] クリティカルヒット時に `★★` プレフィックスと強調メッセージが表示される
- [ ] LUK による完全回避時に特別な演出メッセージが表示される
- [ ] `abstractDamage` 関数が `target_max_hp` パラメータを受け取れるよう拡張されている
- [ ] 既存の `logFormatter.test.ts` が全てパスし、新規ケースのテストが追加されている

## 作業のヒント・メモ

> [!TIP]
> - `_process_hit` 内のクリティカル判定（`simulation.py` 640–660行付近）と
>   LUK 回避判定（590–600行付近）を参照
> - `abstractDamage` は `logFormatter.ts` の 52–62行に定義されており、
>   `formatBattleLog` から呼ばれる（128行付近）
> - `BattleLog` の `damage` フィールドは `int | None` であるため、
>   `target_max_hp` も同様に `None` 許容にすること
> - HP残量コメントは1ログ内の末尾に追記する形が自然（改行ではなく ` — ` 区切り）

## 関連Issue

- Epic: バトルログUX改善（[README.md](./README.md)）
- Sub-Issue: [01_pilot_presence.md](./01_pilot_presence.md)（スキル発動強調と連携）
- Sub-Issue: [02_weapon_armor_display.md](./02_weapon_armor_display.md)（装甲軽減と連携）
- Sub-Issue: [03_tactics_feedback.md](./03_tactics_feedback.md)
