import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import BattleResultModal from "./BattleResultModal";
import { MobileSuit, BattleRewards, LootItem } from "@/types/battle";

/** モバイル幅の確認用ビューポート（375px） */
const MOBILE_VIEWPORTS = {
  mobile375: {
    name: "Mobile 375",
    styles: { width: "375px", height: "667px" },
    type: "mobile",
  },
  desktop: {
    name: "Desktop 1280",
    styles: { width: "1280px", height: "800px" },
    type: "desktop",
  },
};

const meta: Meta<typeof BattleResultModal> = {
  title: "Dashboard/BattleResultModal",
  component: BattleResultModal,
  parameters: {
    layout: "fullscreen",
    backgrounds: { default: "dark" },
    viewport: { options: MOBILE_VIEWPORTS },
  },
  argTypes: {
    winLoss: {
      control: "select",
      options: ["WIN", "LOSE", "DRAW"],
    },
    onClose: { action: "closed" },
    onOpenReplay: { action: "replay" },
  },
  args: {
    onClose: () => {},
  },
};

export default meta;
type Story = StoryObj<typeof BattleResultModal>;

// ── サンプルデータ ──────────────────────────────────────────

// バトル結果の ms_snapshot と同じく、ランクの項目を含まない
const sampleMs: MobileSuit = {
  id: "ms-001",
  name: "RX-78-2 ガンダム",
  max_hp: 1200,
  current_hp: 720,
  armor: 70,
  mobility: 1.6,
  position: { x: 0, y: 0, z: 0 },
  side: "PLAYER",
  tactics: { priority: "CLOSEST", range: "BALANCED" },
  weapons: [
    {
      id: "beam_rifle",
      name: "ビームライフル",
      power: 150,
      range: 600,
      accuracy: 85,
      type: "BEAM",
    },
    {
      id: "beam_saber",
      name: "ビームサーベル",
      power: 220,
      range: 50,
      accuracy: 90,
      type: "BEAM",
      is_melee: true,
    },
  ],
};

const sampleMsZaku: MobileSuit = {
  id: "ms-002",
  name: "MS-06 ザクII",
  max_hp: 800,
  current_hp: 0,
  armor: 45,
  mobility: 1.1,
  position: { x: 0, y: 0, z: 0 },
  side: "PLAYER",
  tactics: { priority: "CLOSEST", range: "RANGED" },
  weapons: [
    {
      id: "zaku_machine_gun",
      name: "ザク・マシンガン",
      power: 90,
      range: 400,
      accuracy: 75,
      type: "PHYSICAL",
    },
  ],
};

const sampleMsLongName: MobileSuit = {
  ...sampleMs,
  name: "RX-78GP03 ガンダム試作3号機 デンドロビウム（オーキス装備・長距離侵攻仕様）",
  weapons: [
    {
      id: "long_weapon",
      name: "大型集束ミサイル・コンテナ（マイクロミサイル内蔵型／対艦攻撃用）",
      power: 320,
      range: 800,
      accuracy: 60,
      type: "PHYSICAL",
    },
    {
      id: "long_weapon2",
      name: "メガ・ビーム砲（Iフィールド・ジェネレーター直結式・高出力モード）",
      power: 400,
      range: 900,
      accuracy: 70,
      type: "BEAM",
    },
  ],
};

const rewardsWin: BattleRewards = {
  exp_gained: 320,
  credits_gained: 1500,
  level_before: 5,
  level_after: 5,
  total_exp: 2450,
  total_credits: 12800,
};

const rewardsLevelUp: BattleRewards = {
  exp_gained: 480,
  credits_gained: 2200,
  level_before: 7,
  level_after: 8,
  total_exp: 6000,
  total_credits: 24500,
};

const rewardsLose: BattleRewards = {
  exp_gained: 80,
  credits_gained: 300,
  level_before: 3,
  level_after: 3,
  total_exp: 940,
  total_credits: 5300,
};

const rewardsDraw: BattleRewards = {
  exp_gained: 100,
  credits_gained: 500,
  level_before: 4,
  level_after: 4,
  total_exp: 1700,
  total_credits: 8000,
};

const lootNew: LootItem = {
  kind: "BLUEPRINT",
  blueprint_id: "mobile_suit:gelgoog",
  target_type: "MOBILE_SUIT",
  target_id: "gelgoog",
  target_name: "ゲルググ",
  is_new: true,
  credits_awarded: 0,
};

const lootConverted: LootItem = {
  kind: "BLUEPRINT",
  blueprint_id: "weapon:beam_rifle",
  target_type: "WEAPON",
  target_id: "beam_rifle",
  target_name: "ビームライフル",
  is_new: false,
  credits_awarded: 300,
};

const lootLongName: LootItem = {
  ...lootNew,
  blueprint_id: "mobile_suit:long",
  target_id: "long",
  target_name:
    "RX-78GP03 ガンダム試作3号機 デンドロビウム（オーキス装備・長距離侵攻仕様）",
};

// ── 勝敗 ────────────────────────────────────────────────────

/** WIN: 通常勝利（戦利品なし） */
export const Win: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsWin,
    msSnapshot: sampleMs,
    kills: 2,
    loot: [],
  },
};

/** LOSE: 敗北 */
export const Lose: Story = {
  args: {
    winLoss: "LOSE",
    rewards: rewardsLose,
    msSnapshot: sampleMsZaku,
    kills: 0,
    loot: [],
  },
};

/** DRAW: 引き分け */
export const Draw: Story = {
  args: {
    winLoss: "DRAW",
    rewards: rewardsDraw,
    msSnapshot: sampleMs,
    kills: 1,
    loot: [],
  },
};

// ── 戦利品 ──────────────────────────────────────────────────

/** 設計図を新規入手（報酬のあとに入手演出） */
export const LootNewBlueprint: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsWin,
    msSnapshot: sampleMs,
    kills: 3,
    loot: [lootNew],
  },
};

/** 所持済みの設計図を換金（獲得報酬のクレジットとは分けて表示） */
export const LootConverted: Story = {
  args: {
    winLoss: "LOSE",
    rewards: rewardsLose,
    msSnapshot: sampleMsZaku,
    kills: 1,
    loot: [lootConverted],
  },
};

/** ドロップなし（空配列）は「戦利品なし」を控えめに表示 */
export const LootEmpty: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsWin,
    msSnapshot: sampleMs,
    kills: 2,
    loot: [],
  },
};

/** 戦利品の導入前のバトル（loot = null）は戦利品欄を出さない */
export const LootLegacyBattle: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsWin,
    msSnapshot: sampleMs,
    kills: 2,
    loot: null,
  },
};

// ── レベルアップ・撃墜数・スナップショット ────────────────────

/** レベルアップ（新規入手の演出のあとにレベルアップ演出） */
export const LevelUpWithNewLoot: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsLevelUp,
    msSnapshot: sampleMs,
    kills: 3,
    loot: [lootNew],
  },
};

/** レベルアップ（戦利品なし） */
export const LevelUp: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsLevelUp,
    msSnapshot: sampleMs,
    kills: 3,
    loot: [],
  },
};

/** 撃墜数 0 */
export const ZeroKills: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsWin,
    msSnapshot: sampleMs,
    kills: 0,
    loot: [],
  },
};

/** 機体スナップショットなし（旧データの後方互換確認） */
export const NoSnapshot: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsWin,
    msSnapshot: null,
    kills: 2,
    loot: [lootConverted],
  },
};

/** 報酬なし（未ログインのソロミッション） */
export const NoRewards: Story = {
  args: {
    winLoss: "WIN",
    rewards: null,
    msSnapshot: sampleMs,
    kills: 1,
  },
};

/** 長い機体名・武器名・戦利品名 */
export const LongNames: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsWin,
    msSnapshot: sampleMsLongName,
    kills: 12,
    loot: [lootLongName],
  },
};

// ── リプレイ導線 ────────────────────────────────────────────

/** 未読の定期バトル（リプレイを見るボタンあり） */
export const UnreadBattleWithReplay: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsWin,
    msSnapshot: sampleMs,
    kills: 2,
    loot: [lootNew],
    onOpenReplay: () => {},
  },
};

// ── 画面幅・最終状態 ────────────────────────────────────────

/** モバイル幅（375px）: 情報が最も多い状態でも CONTINUE がスクロールなしで見えること */
export const MobileFull: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsLevelUp,
    msSnapshot: sampleMsLongName,
    kills: 3,
    loot: [lootNew, lootConverted],
    onOpenReplay: () => {},
  },
  globals: { viewport: { value: "mobile375", isRotated: false } },
};

/** モバイル幅（375px）: 敗北・換金 */
export const MobileLose: Story = {
  args: {
    winLoss: "LOSE",
    rewards: rewardsLose,
    msSnapshot: sampleMsZaku,
    kills: 0,
    loot: [lootConverted],
    onOpenReplay: () => {},
  },
  globals: { viewport: { value: "mobile375", isRotated: false } },
};

/** デスクトップ幅: 演出を省いた最終状態（見た目の比較用） */
export const DesktopFinalState: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsLevelUp,
    msSnapshot: sampleMs,
    kills: 3,
    loot: [lootNew, lootConverted],
    onOpenReplay: () => {},
    animate: false,
  },
  globals: { viewport: { value: "desktop", isRotated: false } },
};
