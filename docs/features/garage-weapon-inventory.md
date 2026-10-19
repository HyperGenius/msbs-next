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

各行（カード）は「名前 / バッジ / 装備状態」の3行で構成する（Issue #665）:

- 1行目: 武器名・改造済みマーク・属性（BEAM/PHYSICAL）
  - 改造済みマーク「改+N」: 威力・命中率の改造段階数の合計（`countUpgradeSteps`、`app/garage/weaponUpgrade.ts`）。同じ武器を複数持っているときに、どれを改造したかを一覧で見分けるため。最後の1段は上限で切り詰められて増分に満たないことがあるので、切り上げで数える
- 2行目: 威力/射程/命中ランク（`base_snapshot` から算出）と、弾数・EN消費（`WeaponResourceBadges.tsx`）
  - ランクはS〜Eごとに背景色付きバッジで色分け表示する（`RANK_BADGE_CLASSES`。S=緑, A=青, B=黄, C=橙, D=赤, E=暗赤）
  - 弾数は `max_ammo` を表示する。`null`・`0` は「∞」にする（エンジンは両方を無制限として扱う）
  - EN消費は `en_cost > 0` の武器にだけ「EN20」のように表示する。ビーム兵器は弾数が「∞」でも EN を消費するため
  - 弾数・EN消費はランクではなく実数なので、ランク色を使わない中立のバッジにしている。バッジが1行に収まらないときは折り返す
- 3行目: 装備状態。装備中なら「→ {MS名}へ移動（スロット）」ボタン、未装備なら「未装備」と「装備する」ボタン
  - `equipped_ms_id` が所持MS一覧に見つからない場合は「不明な機体」と表示し、エラーにしない
- カードの右端に「›」を置き、カードを押すと改造モーダルが開くことを示す
- 同一マスター武器を複数所持している場合も、`PlayerWeapon.id` 単位で個別の行として表示される

`base_snapshot` は武器マスターの `model_dump()` なので、`max_ammo`・`en_cost` はバックエンドを変えずに取れる。

### フィルタ・並び替え

使用頻度で優先度をつけ、1行に複数のUIパターンを混在させないよう配置している:

- 常時表示（高頻度）: 「未装備のみ表示」トグル（漏斗アイコン）、属性フィルタ（すべて / BEAM / PHYSICAL、着弾点アイコン + `SciFiSelect`）
- アイコン + ポップアップメニュー（低頻度）: 並び替え（新しい順 / 古い順 / 装備中が上）は上下矢印アイコンのみのボタンにまとめ、タップ時にメニューを開く方式にして常時表示領域を圧迫しないようにした
- 見出し横に `件数 / 全件数` を表示し、フィルタ適用中であることが分かるようにしている。フィルタで0件になった場合は「フィルタをリセット」ボタンを表示する

属性フィルタ・並び替えはクライアント側でのフィルタリング/ソートだが、「未装備のみ表示」だけは `WeaponInventoryList` 内で `usePlayerWeapons(true)` を呼び直し、`GET /api/player-weapons?unequipped=true` のサーバー側フィルタを使う（`usePlayerWeapons(false)` と同一URLはSWRのグローバルキャッシュで重複排除されるため、OFF時は他画面の全件フェッチと共有される）。所持数が多いユーザーで、装備済み分を毎回無駄に取得しないための対応。
アイコン（`FilterIcon` / `TypeIcon` / `SortIcon` / `EmptyBoxIcon`、`WeaponInventoryList.tsx` 内にインラインSVGで定義）でラベルを短縮している。プロジェクトにアイコンライブラリの導入がないため、依存追加を避けて `currentColor` ベースの最小限のSVGを直接実装した。

### 一覧からの操作

- **カード本体のクリック（すべての行が対象）**: 武器改造モーダル（`WeaponUpgradeModal`）を「改造」タブで開く（Issue #413）。装備中・未装備どちらの武器も改造可能
- **装備中の武器の行**: 装備先MS名・スロット番号を含む一体化ボタン「→ {MS名}へ移動（スロットN）」を、カード幅いっぱいの独自ボタン（`SciFiButton` は使わず素の `<button>`）として設置し、押すと装備先MSの `CustomizationModal` を開く（`useGarageEditor.handleNavigateToEquippedMs`）。カードの主目的アクションであるため、下線リンクではなくボタンとして視覚的な重みを持たせている。配色は新色を追加せず既存パレットの範囲内（`#00ff41`）に収め、通常時は1pxボーダー+透明背景、hover/active時のみ緑背景+黒文字に反転する構成にして、常時は主張しすぎない見た目にしている。武器変更モーダルへは自動遷移させず、ユーザーが次のアクション（LOADOUTタブ操作など）を自分で選べるようにする
- **未装備の武器の行**: 「装備する」ボタンを押すと、改造モーダルを「装備」タブで開く。装備先の機体とスロットはモーダル内で選ぶ（Issue #665）
  - 以前はカード内に機体・スロットの2つのセレクトと装備ボタンを並べていたが、スマホでは2〜3行に折り返し、未装備の武器が多いと1画面に入るカードが少なかった。また、セレクトの近くの余白を押すと改造モーダルが誤って開いた。カード内の操作をボタン1つにして、両方を解消した
- カード内のボタンはカード本体のクリックとは別の操作なので、各ボタンの `onClick` で `e.stopPropagation()` を呼び、改造モーダルが誤って開かないようにしている

### スマホでのスクロール構成（Issue #665）

モバイル幅（`md` 未満）では、GARAGE見出し・タブ・一覧の見出しと件数・フィルタ行を画面上部に固定し、カードのリストだけをスクロールさせる。機体一覧タブ（`MobileSuitList.tsx`）も同じ構成にして、タブを切り替えても見出しの位置が変わらないようにしている。

- ルートレイアウトはモバイル幅で `main` を高さ固定のスクロール領域にしている（`frontend/CLAUDE.md`「ルートレイアウトとページルート要素の規約」）。Garageページのルート要素を `h-full overflow-hidden flex flex-col` にして `main` の高さに合わせ、パネルを `flex-1 min-h-0`、`<ul>` を `flex-1 min-h-0 overflow-y-auto` にしている（`/history` の Records カードと同じパターン）
- `md` 以上は `md:h-auto md:overflow-visible` で高さ固定を外し、従来どおりページ全体をスクロールさせる。スクロール領域はどちらの幅でも1箇所になる
- `<ul>` の `px-1 py-1`（と打ち消しの `-mx-1`）は、`SciFiCard` の hover 時の `scale-[1.02]` でカードの縁がスクロール領域に切られないための余白。`overflow-x-hidden` で横スクロールも出さない
- 固定部分が高いとリストに使える高さが残らないため、スマホ幅ではGARAGE見出しとタブを1行に並べ、ページ・パネルの余白とパネル見出しの文字を小さくしている（`sm` 以上は従来のレイアウト）。375×667 の画面では、未ログイン時の大きいヘッダーを含めても、リスト領域に約220px（カード約1.6枚分）が残る
- カードの余白は `!p-3`。`SciFiCard` の既定の `p-6` が `p-3` より優先されるため、important 修飾子で上書きしている
- 並び替えポップアップはスクロール領域の外（フィルタ行）にあるので、リストのスクロールで切れない

### 武器改造モーダル（`WeaponUpgradeModal.tsx`、Issue #413 / #665）

ヘッダー（武器名・属性・弾数・EN消費・閉じるボタン）の下に「改造」「狙う部位配分」「装備」の3タブを置く（Issue #665）。以前は「武器改造」と「狙う部位配分」を1画面に縦に並べていて、スマホではスクロールしないと操作できなかった。

- モーダルは `SciFiModal` に `fixedHeightClass="h-[min(85dvh,40rem)]"` を渡して高さを固定する。タブごとに中身の量が違っても、ヘッダーとタブの位置が変わらない（タブ付きモーダルの規約。下記 `CustomizationModal` の項を参照）。`40rem` の上限は、デスクトップで中身の少ないタブが間延びしないため
- 各タブは「`flex-1 min-h-0 overflow-y-auto` の中身 + `shrink-0` のフッター」で組み、確定ボタン（改造の `HoldSciFiButton`、部位配分の「配分を適用」、装備の「装備する」）をフッターに固定する。中身をスクロールしなくても押せる
- 非表示のタブはアンマウントせず `hidden` クラスで隠す（`panelClass`）。確定前の改造ステップや部位配分の入力が、タブを切り替えても消えないようにするため
- 375×667 の画面で、3タブとも中身をスクロールせずに収まる（武器名はスマホで `text-base` にして1行に収める）。320×568 のようなさらに小さい画面では中身がスクロールするが、確定ボタンはフッターに残る
- 開くタブはカードのどこを押したかで決まる（カード本体 → 改造、「装備する」 → 装備）。`WeaponInventoryList` は `{ playerWeapon, initialTab }` を state に持つ

#### 「改造」タブ（`WeaponUpgradePanel.tsx`）

MS強化タブ（`CustomizationModal` の `StatusTab.tsx`）とレイアウト・操作感を統一するため、`StatusTab.tsx` と同じ構成要素を配置している: 所持金（現在 ➔ 変更後）表示、ステータスごとの行（ランクバッジ + `SciFiBlockIndicator` + `[-]`/`[+]` ステッパー + 1ステップ分のコスト）、末尾の `HoldSciFiButton` 一括確定ボタン。

- `power_bonus`（威力） / `accuracy_bonus`（命中率）の2ステータスを、`StatusTab.tsx` の `STAT_TYPES` と同型の `WeaponStatInfo` 配列（`WEAPON_UPGRADE_STATS`、`app/garage/weaponUpgrade.ts`）で定義する。コスト計算式（`baseCost * (1 + bonus / costDivisor)`）・上限（実効値が `base × capMultiplier` に達するまで）は `WeaponEngineeringService`（バックエンド）の定数値をクライアント側にも複製している（`StatusTab.tsx` が `EngineeringService` の式を複製しているのと同じパターン）。一覧の「改+N」も同じ定義の増分を使うため、モジュールに切り出している
- `[-]`/`[+]` ボタンで各ステータスのペンディングステップ数を増減し、`SciFiBlockIndicator` に現在値（緑）・今回追加予定（黄）・残り（黒）を表示する。ステップ数はクライアント側で `simulateSteps` によりコスト・改造後の実効値をシミュレーションし、リアルタイムにプレビューする
- `[-]`/`[+]` ボタンは指で押しやすいよう 44px（`w-11 h-11`）にしている（Issue #665）。スマホ幅ではインジケーターと同じ行に収まらないため、ステッパーは次の行の右端に折り返す。そのぶん「✨RANK UP!」はランクバッジの横ではなくラベル行に置いている
- 威力・命中率とも「200」「85.0%」のような生の数値は表示せず、ランクバッジとブロックインジケーターのみで現在値・改造後の変化を表現する（`StatusTab.tsx` も同様に生値ではなくランク・インジケーター中心の表示にしている）
- フッターの `HoldSciFiButton`（長押し確定、誤タップ防止）を押すと、ペンディングステップが入っているステータスごとに `POST /api/player-weapons/{pw_id}/upgrade` を順次呼び出す（武器改造には bulk エンドポイントが無いため、同一 `player_weapon_id` への逐次呼び出しで対応。後続の呼び出しは先の更新を含んだ `PlayerWeapon` を返すため、最後のレスポンスが最終状態になる）
- 改造後の実効値からランク（`getWeaponRank("weapon_power" | "weapon_accuracy", value)`）を計算し、ランクアップする場合は現在ランクの代わりに改造後ランクを表示して「✨RANK UP!」を添える
- 改造成功時は最後のレスポンスの `player_weapon` を `onUpgraded` で呼び出し元（`WeaponInventoryList`）に渡し、一覧側の `resolveWeaponSpec`（`base_snapshot + custom_stats` をマージして実効スペックを計算）がランクバッジに即座に反映する。同時に `usePlayerWeapons` のSWRキャッシュとパイロットのクレジット残高（`usePilot`）も再検証する（`useGarageEditor.handleWeaponUpgraded`）
- `GET /api/player-weapons/{pw_id}/upgrade-preview/{stat_type}`（バックエンド実装済み）はこのUIからは呼び出していない。`StatusTab.tsx` が機体強化側の `GET /api/engineering/preview/...` を使わずクライアント計算のみで完結させているのと同じ判断で、コスト計算をクライアント側で完結させてAPI往復を減らしている

#### 「狙う部位配分」タブ（`AimDistributionEditor.tsx`、Issue #505）

- 部位ごとのスライダー（5%刻み）で配分を決める。行の高さは 40px にして、指で操作しやすくしている
- 合計がちょうど100%でないと適用できないため、フッターに「合計」と「残り N%」「N% 超過」「OK」を表示する（Issue #665）。以前は合計値しか出ておらず、あといくつ動かせばよいかが分からなかった
- フッターの「配分を適用」で `PUT` する。クレジットは消費しない

#### 「装備」タブ（`WeaponEquipPanel.tsx`、Issue #665）

- 未装備の武器: 装備先の機体とスロットを `SciFiSelect` で選び、フッターの「装備する」で装備する（`useGarageEditor.handleEquipFromInventory`）。成功したらモーダルを閉じる。装備後はカードの「→ {MS名}へ移動」ボタンが結果を示す
  - `handleEquipFromInventory` は成否を `boolean` で返す。失敗時の通知（`alert`）はフック側で済ませているので、呼び出し元は成功時にモーダルを閉じるだけでよい
  - バックエンドの装備制約を事前に UI に出し、押してからエラーになる操作を減らしている:
    - 手前のスロットを飛ばした装備は拒否されるので、スロットの選択肢は `index <= MobileSuit.weapons.length` のものに絞る（バックエンドの検証と同じ基準）
    - BEAM武器で `required_beam_generator_lv` が機体の `beam_generator_lv` を超える場合は、理由を表示して「装備する」を無効にする
    - スロットに武器が入っている場合は選択肢に「右腕（Beam Rifle）」のように表示し、装備すると外れることを注記する。空きスロットがあれば、それを初期選択にする
  - スロットに入っている武器名は `PlayerWeapon`（装備状態の正）から引く。ただし機体の初期装備は `PlayerWeapon` を持たないため、`PlayerWeapon` が無いスロットだけ `MobileSuit.weapons` の名前で補う。全件の `usePlayerWeapons()` は Garage と同じ SWR キーなので、追加のリクエストは発生しない
- 装備中の武器: 装備先とスロットを表示し、フッターに「→ {MS名}へ移動」を置く。押すとこのモーダルを閉じてから装備先の `CustomizationModal` を開く（両モーダルは同じ `z-[60]` なので、重ねずに切り替える）

### MS改造モーダル（`CustomizationModal.tsx`）の `z-index` 不具合修正（Issue #413）

本Issueの作業中に、MS改造モーダル（`CustomizationModal.tsx`）と、その上に開く武器変更モーダル（`WeaponChangeModal.tsx`）がモバイルで `BottomNav`（`z-50 fixed bottom-0 h-16 md:hidden`）の裏に回り込み、下端が隠れる不具合を確認した。両モーダルは `SciFiModal` 導入以前からの実装で `z-40` / `z-50` のままになっており、`frontend/CLAUDE.md`「よくあるハマりポイント」に明記されている「モーダルは `z-[60]` 以上にすること」のルールを満たしていなかった。

- `CustomizationModal.tsx`: `z-40` → `z-[60]`
- `WeaponChangeModal.tsx`（`CustomizationModal` の上に重ねて開く）: `z-50` → `z-[70]`（`CustomizationModal` よりさらに前面に出す必要があるため）
- 合わせて `vh` 指定を `dvh`（モバイルブラウザのアドレスバー等による表示領域変動に追従）に更新し、外側コンテナに `p-4` を付けて上下左右の余白を均等に確保した（`CustomizationModal.tsx` 側の重複していた `mx-4` は削除）
  - `WeaponChangeModal.tsx`（タブ無し・単一ビュー）は `max-h-[85dvh]` + 内部 `overflow-y-auto`（他のモーダルと同じくコンテンツ量に応じて高さが変わる）
  - `CustomizationModal.tsx`（STATUS/TERRAIN/LOADOUT/TACTICS のタブ切り替えあり）は `h-[85dvh]` **固定**にしている。`max-h` にしてしまうとタブごとのコンテンツ量の違いでモーダル自体の高さが伸縮し、タブ切り替えのたびにヘッダー・タブバーの表示位置がずれてユーザーが混乱する不具合になったため（Issue #413で `max-h-[85dvh]` → `h-[85dvh]` に修正）。タブ切り替えUIを持つモーダルを新規に作る場合は、このモーダルに限らず固定高さ + 内部 `overflow-y-auto` を使うこと

### 空状態・少数件時のレイアウト

- 0件（未所持、またはフィルタで該当なし）の場合は、アイコン付きの空状態メッセージ（所持数ゼロなら購入導線への案内文、フィルタ起因ならリセットボタン）を表示し、単なる空白に見えないようにしている
- モバイル幅ではパネルが `main` の残りの高さいっぱいに広がる（リストだけをスクロールさせる構成のため）。件数が少なくてもパネルの枠は画面下端まで伸びる
- `md` 以上ではパネルに最小高さを設けていないため、1件のみの場合でもカード分の高さしか占有しない

---

## 関連ファイル

- `frontend/src/app/garage/page.tsx` — タブ切り替えUIの追加。`pilot` / `handleWeaponUpgraded` を `WeaponInventoryList` に渡す。モバイル幅で `main` の高さに合わせ、リストだけをスクロールさせる（Issue #665）
- `frontend/src/app/garage/hooks/useGarageEditor.ts` — `activeTab` 状態、`handleNavigateToEquippedMs` / `handleEquipFromInventory` / `handleWeaponUpgraded`（Issue #413）ハンドラを追加。`handleEquipFromInventory` は成否を `boolean` で返す（Issue #665）
- `frontend/src/app/garage/components/WeaponInventoryList.tsx` — 所持武器一覧コンポーネント。自身で `usePlayerWeapons()` を呼び出し、装備先MSの参照は `mobileSuits` から作った `Map<id, MobileSuit>`（`msById`）でO(1)解決する。カードクリック・「装備する」で `WeaponUpgradeModal` を開く
- `frontend/src/app/garage/components/MobileSuitList.tsx` — 機体一覧。所持武器一覧と同じく、モバイル幅でリストだけをスクロールさせる（Issue #665）
- `frontend/src/app/garage/weaponUpgrade.ts` — 武器改造の定数・コスト計算（`WEAPON_UPGRADE_STATS` ほか）、改造段階数（`countUpgradeSteps`）、実効スペック（`resolveWeaponSpec`）（Issue #665 で切り出し）
- `frontend/src/app/garage/components/WeaponUpgradeModal.tsx` — 武器改造モーダル。ヘッダーと3タブの切り替え（Issue #413 / #665）
- `frontend/src/app/garage/components/WeaponUpgradePanel.tsx` — 「改造」タブ（Issue #665 で `WeaponUpgradeModal.tsx` から切り出し）
- `frontend/src/app/garage/components/AimDistributionEditor.tsx` — 「狙う部位配分」タブ（Issue #505 / #665）
- `frontend/src/app/garage/components/WeaponEquipPanel.tsx` — 「装備」タブ（Issue #665）
- `frontend/src/app/garage/components/WeaponResourceBadges.tsx` — 弾数・EN消費のバッジ。一覧とモーダルのヘッダーで共有する（Issue #665）
- `frontend/src/components/ui/SciFiModal.tsx` — `fixedHeightClass` を追加。指定時は高さ固定の flex 列になり、スクロールは中身が持つ（Issue #665）
- `frontend/src/hooks/usePlayerWeapons.ts` — 所持武器取得フック（既存、変更なし。`unequippedOnly` 引数で `?unequipped=true` を切り替え可能）
- `frontend/src/app/garage/constants.ts` — `getWeaponSlots()` / `getWeaponSlotLabel()`（既存、スロット選択・表示に再利用）
- `frontend/src/services/weaponEngineering.ts` / `frontend/src/types/shop.ts` — 武器改造APIクライアント・型（Issue #411 で実装済み、本Issueで初めて画面から利用）
- `backend/app/routers/player_weapons.py` / `backend/app/services/weapon_service.py` / `backend/app/services/weapon_engineering_service.py` — 武器改造API・ロジック（既存、変更なし）

---

## 今後の拡張

- 一覧から武器の売却・破棄（`DELETE /api/player-weapons/{pw_id}`）を行う導線は未実装（別Issueで検討）

---

## テスト

- `cd frontend && ./node_modules/.bin/tsc --noEmit` — 型チェック
- `cd frontend && npx vitest run tests/unit/` — ユニットテスト。純粋関数の `countUpgradeSteps` / `resolveWeaponSpec` は `tests/unit/weaponUpgrade.test.ts` で検証する（上限で切り詰められた最後の段階、浮動小数の誤差を含む）。SWRフック・Reactコンポーネントは `frontend/CLAUDE.md` の方針によりユニットテスト対象外
- 画面の確認（Issue #665）: `/dev` 配下にモックデータを渡す一時ページを置き、Playwright で 375×667・320×568・1280×800 のスクリーンショットを撮った。ページ（`main`）がスクロールしないこと、タブを切り替えてもタブバーの位置が変わらないこと、確定前の改造ステップが残ることも計測で確認した。一時ページは確認後に削除した
- `cd frontend && npm run build` — 本番ビルド確認
