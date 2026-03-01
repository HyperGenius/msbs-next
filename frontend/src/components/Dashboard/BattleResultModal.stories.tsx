import type { Meta, StoryObj } from "@storybook/react";
import BattleResultModal from "./BattleResultModal";
import { MobileSuit, BattleRewards } from "@/types/battle";

const meta: Meta<typeof BattleResultModal> = {
  title: "Dashboard/BattleResultModal",
  component: BattleResultModal,
  parameters: {
    layout: "fullscreen",
    backgrounds: { default: "dark" },
  },
  argTypes: {
    winLoss: {
      control: "select",
      options: ["WIN", "LOSE", "DRAW"],
    },
    onClose: { action: "closed" },
  },
};

export default meta;
type Story = StoryObj<typeof BattleResultModal>;

// ── サンプルデータ ──────────────────────────────────────────

const sampleMs: MobileSuit = {
  id: "ms-001",
  name: "RX-78-2 ガンダム",
  max_hp: 200,
  current_hp: 120,
  armor: 25,
  mobility: 1.8,
  position: { x: 0, y: 0, z: 0 },
  side: "PLAYER",
  tactics: { priority: "CLOSEST", range: "BALANCED" },
  weapons: [
    {
      id: "beam_rifle",
      name: "ビームライフル",
      power: 55,
      range: 600,
      accuracy: 85,
      type: "BEAM",
    },
    {
      id: "beam_saber",
      name: "ビームサーベル",
      power: 70,
      range: 50,
      accuracy: 90,
      type: "BEAM",
      is_melee: true,
    },
  ],
  hp_rank: "A",
  armor_rank: "B",
  mobility_rank: "S",
};

const sampleMsZaku: MobileSuit = {
  id: "ms-002",
  name: "MS-06 ザクII",
  max_hp: 160,
  current_hp: 0,
  armor: 18,
  mobility: 1.2,
  position: { x: 0, y: 0, z: 0 },
  side: "PLAYER",
  tactics: { priority: "CLOSEST", range: "RANGED" },
  weapons: [
    {
      id: "zaku_machine_gun",
      name: "ザク・マシンガン",
      power: 25,
      range: 400,
      accuracy: 75,
      type: "PHYSICAL",
    },
  ],
  hp_rank: "B",
  armor_rank: "C",
  mobility_rank: "C",
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

// ── ストーリー ──────────────────────────────────────────────

/** WIN: 機体・武器・報酬あり（通常勝利） */
export const Win: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsWin,
    msSnapshot: sampleMs,
    kills: 2,
    onClose: () => {},
  },
};

/** WIN: レベルアップ演出あり */
export const WinWithLevelUp: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsLevelUp,
    msSnapshot: sampleMs,
    kills: 3,
    onClose: () => {},
  },
};

/** LOSE: 敗北結果 */
export const Lose: Story = {
  args: {
    winLoss: "LOSE",
    rewards: rewardsLose,
    msSnapshot: sampleMsZaku,
    kills: 0,
    onClose: () => {},
  },
};

/** DRAW: 引き分け */
export const Draw: Story = {
  args: {
    winLoss: "DRAW",
    rewards: {
      exp_gained: 100,
      credits_gained: 500,
      level_before: 4,
      level_after: 4,
      total_exp: 1700,
      total_credits: 8000,
    },
    msSnapshot: sampleMs,
    kills: 1,
    onClose: () => {},
  },
};

/** WIN: 機体スナップショットなし（旧データの後方互換確認） */
export const WinNoSnapshot: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsWin,
    msSnapshot: null,
    kills: 2,
    onClose: () => {},
  },
};

/** WIN: 報酬なし（未認証バトル） */
export const WinNoRewards: Story = {
  args: {
    winLoss: "WIN",
    rewards: null,
    msSnapshot: sampleMs,
    kills: 1,
    onClose: () => {},
  },
};

/** WIN: 撃墜数 0 */
export const WinZeroKills: Story = {
  args: {
    winLoss: "WIN",
    rewards: rewardsWin,
    msSnapshot: sampleMs,
    kills: 0,
    onClose: () => {},
  },
};
