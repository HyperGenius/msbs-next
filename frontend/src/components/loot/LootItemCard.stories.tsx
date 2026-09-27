import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import LootItemCard from "./LootItemCard";
import LootList from "./LootList";
import LootBadge from "./LootBadge";
import { BlueprintLootItem, TechFragmentLootItem } from "@/types/battle";

const meta: Meta<typeof LootItemCard> = {
  title: "Loot/LootItemCard",
  component: LootItemCard,
  parameters: {
    backgrounds: { default: "dark" },
  },
  decorators: [
    (Story) => (
      <div className="max-w-md p-4 bg-[#0a0a0a]">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof LootItemCard>;

const newMobileSuit: BlueprintLootItem = {
  kind: "BLUEPRINT",
  blueprint_id: "mobile_suit:gelgoog",
  target_type: "MOBILE_SUIT",
  target_id: "gelgoog",
  target_name: "ゲルググ",
  is_new: true,
  credits_awarded: 0,
};

const convertedWeapon: BlueprintLootItem = {
  kind: "BLUEPRINT",
  blueprint_id: "weapon:beam_rifle",
  target_type: "WEAPON",
  target_id: "beam_rifle",
  target_name: "ビームライフル",
  is_new: false,
  credits_awarded: 1200,
};

const techFragment: TechFragmentLootItem = {
  kind: "TECH_FRAGMENT",
  tech_id: "psycommu_tech",
  target_name: "サイコミュ技術",
  fragment_count: 5,
  level: 1,
  max_level: 3,
  is_level_up: false,
  fragments_to_next_level: 3,
  credits_awarded: 0,
};

const techLevelUp: TechFragmentLootItem = {
  ...techFragment,
  fragment_count: 8,
  level: 2,
  is_level_up: true,
  fragments_to_next_level: 7,
};

const techConverted: TechFragmentLootItem = {
  ...techFragment,
  tech_id: "beam_generator_tech",
  target_name: "ビームジェネレータ技術",
  fragment_count: 15,
  level: 3,
  fragments_to_next_level: null,
  credits_awarded: 500,
};

/** 機体設計図を新規入手 */
export const NewMobileSuit: Story = {
  args: { item: newMobileSuit },
};

/** 新規入手の演出あり */
export const NewWithAnimation: Story = {
  args: { item: newMobileSuit, animate: true },
};

/** 所持済みの武器設計図を換金 */
export const ConvertedWeapon: Story = {
  args: { item: convertedWeapon },
};

/** 技術断片を入手（Lvは上がらない） */
export const TechFragment: Story = {
  args: { item: techFragment },
};

/** 技術断片で技術Lvが上がった（入手演出あり） */
export const TechFragmentLevelUp: Story = {
  args: { item: techLevelUp, animate: true },
};

/** 技術断片で最大Lvに到達した */
export const TechFragmentReachedMax: Story = {
  args: {
    item: { ...techLevelUp, fragment_count: 15, level: 3, fragments_to_next_level: null },
  },
};

/** 最大Lv後の技術断片をクレジットに換金 */
export const TechFragmentConverted: Story = {
  args: { item: techConverted },
};

/** 対象のマスターが削除済み（名前は target_id） */
export const MissingMaster: Story = {
  args: {
    item: {
      ...newMobileSuit,
      target_id: "deleted_ms",
      target_name: "deleted_ms",
    },
  },
};

/** 長い名前 */
export const LongName: Story = {
  args: {
    item: {
      ...newMobileSuit,
      target_name:
        "RX-78GP03 ガンダム試作3号機 デンドロビウム（オーキス装備・長距離侵攻仕様）",
    },
  },
};

/** 一覧: ドロップなし・導入前のバトル・複数 */
export const ListStates: Story = {
  render: () => (
    <div className="space-y-4 font-mono text-xs text-gray-400">
      <div>
        <p className="mb-1">複数</p>
        <LootList loot={[newMobileSuit, convertedWeapon]} />
      </div>
      <div>
        <p className="mb-1">設計図と技術断片（導入前の戦利品と混在）</p>
        <LootList loot={[convertedWeapon, techFragment]} />
      </div>
      <div>
        <p className="mb-1">ドロップなし（空配列）</p>
        <LootList loot={[]} />
      </div>
      <div>
        <p className="mb-1">導入前のバトル（null）: 何も表示しない</p>
        <LootList loot={null} />
      </div>
    </div>
  ),
};

/** バトル履歴の一覧のバッジ */
export const Badges: Story = {
  render: () => (
    <div className="flex gap-2">
      <LootBadge loot={[newMobileSuit]} />
      <LootBadge loot={[convertedWeapon]} />
      <LootBadge loot={[techLevelUp]} />
      <LootBadge loot={[techConverted]} />
      <LootBadge loot={[techFragment]} />
      <LootBadge loot={[]} />
      <LootBadge loot={null} />
    </div>
  ),
};
