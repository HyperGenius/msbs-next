---
title: '[Epic]: バトルログUX改善'
labels: enhancement, ux, battle-log
---

## 概要

バトルログの表示を改善し、プレイヤーが「育成・カスタマイズの成果確認」と「次戦に向けた戦術分析」を行えるようにする。
ビジュアル表示（BattleViewer）との役割を明確に分担し、テキストログはプレイヤーの育成・カスタマイズへの投資を肯定し、シミュレーションとしての納得感・ワクワク感を提供することに特化させる。

## 背景

現在のバトルログは機体名同士の抽象的な表現に留まっており、以下の問題がある。

- `Gelgoogの攻撃！ (距離不利) -> 回避された！` のように、「誰が」「何を使って」戦っているのかが不明確
- ターゲット選択ログ（`Gelgoogがターゲット選択: Acguy (戦術: CLOSEST, 距離: 中距離)`）が事務的で没入感に欠ける
- 装甲による軽減（`[対実弾装甲により12%軽減]`）が文脈から浮いており、戦術的意味が読み取りにくい

## Sub-Issue 一覧

| # | タイトル | ファイル | 優先度 |
|---|----------|----------|--------|
| 1 | パイロットの存在感強化 | [01_pilot_presence.md](./01_pilot_presence.md) | 高 |
| 2 | 武装・装甲情報の明示 | [02_weapon_armor_display.md](./02_weapon_armor_display.md) | 高 |
| 3 | 戦術フィードバックの改善 | [03_tactics_feedback.md](./03_tactics_feedback.md) | 中 |
| 4 | 戦況グラデーション表現の強化 | [04_damage_gradation.md](./04_damage_gradation.md) | 中 |

## 改善前後イメージ

### ターゲット選択

```
❌ 現状:
Gelgoogがターゲット選択: Acguy (NPC) (戦術: CLOSEST, 距離: 中距離)

⭕️ 改善後:
[マ・クベ]のGelgoogは[戦術: 近距離優先]に従い、中距離にいるAcguy (NPC)をターゲットに捕捉！
```

### 攻撃・回避

```
❌ 現状:
Gelgoogの攻撃！ (距離不利) -> 回避された！

⭕️ 改善後:
[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！ -> 距離が合わず回避された！
```

### ダメージ・装甲軽減

```
❌ 現状:
Gelgoogの攻撃！ -> 命中！ [対実弾装甲により12%軽減] AcguyにXXダメージ！

⭕️ 改善後:
[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！ -> 命中！ Acguyの対実弾装甲が衝撃を受け止め、軽微なダメージに抑えた！
```

## 関連ファイル

- バックエンド（ログ生成）: `backend/app/engine/simulation.py`
- フロントエンド（ログ整形）: `frontend/src/utils/logFormatter.ts`
- フロントエンド（ログ表示）: `frontend/src/components/history/BattleLogViewer.tsx`
- 型定義: `frontend/src/types/battle.ts`
- テスト: `frontend/tests/unit/logFormatter.test.ts`
