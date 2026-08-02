# Garage 所持武器一覧（装備先MS表示）

## 概要

Garageページに、プレイヤーが所持する全武器インスタンス（`player_weapons`）を横断的に一覧できる「所持武器一覧」タブを追加した。
機体を1体ずつ選んで装備モーダルを開かなくても、所持している武器の総数・種別・装備状況（どのMSのどのスロットに装備中か、または未装備か）を一目で把握できる。

既存のバックエンドAPI（`GET /api/player-weapons`）・データモデル（`PlayerWeapon`）を変更せずに実現しており、本Issueはフロントエンドの表示層追加が中心（Issue #403）。

---

## UI構成

Garageページ（`frontend/src/app/garage/page.tsx`）にタブ切り替えを追加:

| タブ | 内容 |
|------|------|
| 機体一覧 | 既存の `MobileSuitList`（所持MSのグリッド表示） |
| 所持武器一覧 | 新規追加。所持する全 `PlayerWeapon` インスタンスの一覧 |

### 所持武器一覧（`WeaponInventoryList.tsx`）

各行に以下を表示する:

- 武器名・属性（BEAM/PHYSICAL）・威力/射程/命中ランク（`base_snapshot` から算出）
- 装備状態: 装備中なら装備先MS名 + スロット番号、未装備なら「未装備」
  - `equipped_ms_id` が所持MS一覧に見つからない場合は「不明な機体」と表示し、エラーにしない
- 同一マスター武器を複数所持している場合も、`PlayerWeapon.id` 単位で個別の行として表示される

### フィルタ・並び替え

- 「未装備のみ表示」トグル
- 属性フィルタ（すべて / BEAM / PHYSICAL）
- 並び替え（取得日時が新しい順 / 古い順 / 装備中を上に表示）

いずれもクライアント側でのフィルタリング（`GET /api/player-weapons` の全件取得結果に対して行う）。

### 一覧からの操作

- **装備中の武器の行**: 行自体はクリック不可（将来の武器改造モーダルの導線として予約するため）。装備先MS名・スロット番号を含む一体化ボタン「→ {MS名} へ移動（スロットN）」を設置し、押すと装備先MSの `CustomizationModal` を開く（`useGarageEditor.handleNavigateToEquippedMs`）。汎用ラベル＋別ボタンの構成ではなく、遷移先そのものをボタン化することで直感的なクリック対象にしている。武器変更モーダルへは自動遷移させず、ユーザーが次のアクション（LOADOUTタブ操作など）を自分で選べるようにする
- **未装備の武器の行** → 装備先MS・スロットをインラインの `SciFiSelect` で選択し、「装備する」ボタンで直接装備できる（`useGarageEditor.handleEquipFromInventory` が `PUT /api/mobile_suits/{ms_id}/equip` を呼び出す既存の `equipWeapon` サービス関数を利用）

> [!NOTE]
> 行自体のクリックは、今後実装予定の武器改造（強化）モーダルへの導線として空けてある（関連: 武器改造機能に向けたデータモデル整理・マイグレーション Issue）。

---

## 関連ファイル

- `frontend/src/app/garage/page.tsx` — タブ切り替えUIの追加
- `frontend/src/app/garage/hooks/useGarageEditor.ts` — `activeTab` 状態、`handleNavigateToEquippedMs` / `handleEquipFromInventory` ハンドラを追加
- `frontend/src/app/garage/components/WeaponInventoryList.tsx` — 所持武器一覧コンポーネント（新規）
- `frontend/src/hooks/usePlayerWeapons.ts` — 所持武器取得フック（既存、変更なし）
- `frontend/src/app/garage/constants.ts` — `getWeaponSlots()`（既存、スロット選択に再利用）
- `backend/app/routers/player_weapons.py` / `backend/app/services/weapon_service.py` — `GET /api/player-weapons`（既存、変更なし）

---

## 今後の拡張

- 武器改造（強化）機能実装後、本一覧に強化状態（`PlayerWeapon.custom_stats` 由来の差分）を表示する拡張を予定
- 一覧から武器の売却・破棄（`DELETE /api/player-weapons/{pw_id}`）を行う導線は未実装（別Issueで検討）

---

## テスト

- `cd frontend && ./node_modules/.bin/tsc --noEmit` — 型チェック
- `cd frontend && npx vitest run tests/unit/` — 既存ユニットテスト（本機能はSWRフック・Reactコンポーネントが中心で、`frontend/CLAUDE.md` の方針によりユニットテスト対象外）
- `cd frontend && npm run build` — 本番ビルド確認
