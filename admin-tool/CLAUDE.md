# CLAUDE.md

このファイルは、Claude Code が `admin-tool` ディレクトリで作業する際の方針を記述します。
リポジトリ全体の規約はルートの `CLAUDE.md` を参照してください。

## Admin Tool の基本方針: Garage でできることは Admin Tool でもできるようにする

プレイヤーが Garage 画面（`frontend/src/app/garage/`）で機体に対してできる操作は、
管理者が Admin Tool から NPC 機体・エース機体に対しても行えるようにする。
NPC の挙動確認・バランス調整を、プレイヤーと同じ条件で行えるようにするため。

- Garage に機能を追加・変更する場合は、Admin Tool の NPC 機体（`/npcs`）とエース機体（`/ace-pilots`）にも対応する操作があるか確認する。
- 対応がない場合は、同じ PR で追加するか、下表の「未対応」に追記したうえで Issue を起票する。
- Admin Tool ではクレジット消費や改造段階を経由しない。最終的な値を直接編集できればよい。

### Garage と Admin Tool の対応表

| Garage の操作 | Garage 側の実装 | Admin Tool（NPC 機・エース機） |
|---|---|---|
| 機体名の変更 | `MobileSuitEditor` / `PUT /api/mobile_suits/{id}` | 対応済み（機体タブ） |
| 戦術（ターゲット優先度・交戦距離） | `TacticsSelector` | 対応済み（機体タブ） |
| 戦術（武装持ち替えポリシー `weapon_switch_policy`） | `TacticsSelector` | 未対応 |
| 機体ステータス強化（HP・装甲・機動性・適性/補正） | `StatusTab` / `/api/engineering/*` | 対応済み（値を直接編集。適性/補正は NPC 機のみ） |
| 機体ステータス強化（武器威力 `weapon_power`） | `StatusTab` | 対応済み（武装タブで各武器の威力を直接編集） |
| 武装の装備変更（インベントリから武器スロットへ） | `WeaponChangeModal` / `PUT /api/mobile_suits/{id}/equip` | 一部対応（武装タブで手入力。武器マスターからの選択と、機体ごとのスロット数上限は未対応） |
| 武器改造（威力・命中ボーナス） | `WeaponUpgradeModal` / `/api/player-weapons/{id}/upgrade` | 対応済み（各武器の威力・命中率を直接編集） |
| 狙い部位配分（`aim_distribution`） | `AimDistributionEditor` | 未対応（保存時は既存値を引き継ぐ） |

## NPC 機体・エース機体のデータの持ち方

- 通常 NPC 機: `mobile_suits` テーブルの行（`user_id = 'npc-{uuid}'`、`side = 'ENEMY'`）。武装は `mobile_suits.weapons`（JSON）に機体ごとに保存する。
  プレイヤーと違い `player_weapons` の行を持たないため、`weapons` の JSON がそのままバトルで使われる。
- エース機: `ace_pilots.mobile_suit`（JSON）が雛形。マッチングのたびに `mobile_suits` へコピーされる。
  Admin Tool で編集するのは雛形の方。コピー後の `mobile_suits` の行は編集対象にしない。
- 武器スロット数（`weapon_slot_count`）は `master_mobile_suits` にだけある。プレイヤー機は機体名で機体マスターを引いて解決する。
  NPC 機は機体名が `"{機体マスター名} (NPC)"` になるため解決できない。

## フォーム実装の注意

- `react-hook-form` を使うフォームコンポーネントには `"use no memo"` を付ける。React Compiler の自動メモ化が `reset()` を阻害するため（Issue #388）。
- 機体スペック・武装の入力欄は `src/components/admin/MobileSuitSpecFields.tsx` の共通部品を使う。NPC 機とエース機で入力項目をそろえるため。
- フォームで扱わない武器項目（`weapon_type` / `cooldown_sec` / `fire_arc_deg` / `aim_distribution` 等）は、送信時に同じ武器 ID の取り込み元から引き継ぐ（`mergeWeaponSources()`）。引き継がないと既定値に戻ってしまう。
