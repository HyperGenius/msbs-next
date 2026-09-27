import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import BlueprintCollectionCard from "./BlueprintCollectionCard";
import { BlueprintCollectionItem } from "@/types/battle";

const meta: Meta<typeof BlueprintCollectionCard> = {
  title: "Collection/BlueprintCollectionCard",
  component: BlueprintCollectionCard,
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
type Story = StoryObj<typeof BlueprintCollectionCard>;

const unowned: BlueprintCollectionItem = {
  blueprint_id: "mobile_suit:gelgoog",
  target_type: "MOBILE_SUIT",
  target_id: "gelgoog",
  target_name: "ゲルググ",
  faction: "ZEON",
  is_standard_issue: false,
  is_owned: false,
  acquired_at: null,
  source: null,
  is_available_to_faction: true,
  obtainable_theaters: [{ label: "全戦域", requires_win: false }],
};

/** 所持（ドロップで入手） */
export const Owned: Story = {
  args: {
    item: {
      ...unowned,
      is_owned: true,
      acquired_at: "2026-09-26T12:00:00Z",
      source: "DROP",
      obtainable_theaters: [],
    },
  },
};

/** 所持（導入時の付与）の武器 */
export const OwnedByMigration: Story = {
  args: {
    item: {
      ...unowned,
      blueprint_id: "weapon:beam_rifle",
      target_type: "WEAPON",
      target_id: "beam_rifle",
      target_name: "ビームライフル",
      faction: "",
      is_owned: true,
      acquired_at: "2026-09-20T00:00:00Z",
      source: "MIGRATION",
      obtainable_theaters: [],
    },
  },
};

/** 未所持（入手先あり） */
export const Unowned: Story = {
  args: { item: unowned },
};

/** 未所持（勝利時のみ） */
export const UnownedWinOnly: Story = {
  args: {
    item: {
      ...unowned,
      obtainable_theaters: [{ label: "全戦域", requires_win: true }],
    },
  },
};

/** 未所持（複数の戦域。戦域ローテーション導入後の想定） */
export const UnownedMultipleTheaters: Story = {
  args: {
    item: {
      ...unowned,
      obtainable_theaters: [
        { label: "オデッサ", requires_win: false },
        { label: "ソロモン宙域", requires_win: true },
      ],
    },
  },
};

/** 未所持（入手先なし） */
export const Unavailable: Story = {
  args: {
    item: { ...unowned, obtainable_theaters: [] },
  },
};

/** 未所持（パイロットの勢力では入手できない） */
export const OtherFaction: Story = {
  args: {
    item: {
      ...unowned,
      blueprint_id: "mobile_suit:gundam",
      target_id: "gundam",
      target_name: "ガンダム",
      faction: "FEDERATION",
      is_available_to_faction: false,
      obtainable_theaters: [],
    },
  },
};

/** 標準配備 */
export const StandardIssue: Story = {
  args: {
    item: {
      ...unowned,
      blueprint_id: "mobile_suit:zaku_ii",
      target_id: "zaku_ii",
      target_name: "ザクII",
      is_standard_issue: true,
      obtainable_theaters: [],
    },
  },
};

/** 長い名前 */
export const LongName: Story = {
  args: {
    item: {
      ...unowned,
      target_name:
        "RX-78GP03 ガンダム試作3号機 デンドロビウム（オーキス装備・長距離侵攻仕様）",
      obtainable_theaters: [{ label: "全戦域", requires_win: true }],
    },
  },
};
