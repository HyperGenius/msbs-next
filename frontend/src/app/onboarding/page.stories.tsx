import type { Meta, StoryObj } from "@storybook/react";
import { fn, userEvent, within, spyOn } from "storybook/test";
import OnboardingPage from "./page";

const meta: Meta<typeof OnboardingPage> = {
  title: "Onboarding/OnboardingPage",
  component: OnboardingPage,
  parameters: {
    layout: "fullscreen",
    nextjs: {
      appDirectory: true,
      navigation: {
        push: fn(),
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof OnboardingPage>;

// ── Step 1 ──────────────────────────────────────────────────────────────────

/** Step 1 — 初期表示（勢力選択 & コールサイン入力） */
export const Step1Empty: Story = {};

/** Step 1 — 入力済み（FEDERATION選択、コールサイン入力） */
export const Step1Filled: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const nameInput = canvas.getByPlaceholderText("例: Amuro Ray");
    await userEvent.type(nameInput, "Amuro Ray");
    const federationButton = canvas.getByText("地球連邦軍");
    await userEvent.click(federationButton);
  },
};

/** Step 1 — エラー表示（名前短すぎ） */
export const Step1NameError: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const nameInput = canvas.getByPlaceholderText("例: Amuro Ray");
    await userEvent.type(nameInput, "A");
    const nextButton = canvas.getByText("▶ 次へ / NEXT");
    await userEvent.click(nextButton);
  },
};

/** Step 1 — エラー表示（勢力未選択） */
export const Step1FactionError: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const nameInput = canvas.getByPlaceholderText("例: Amuro Ray");
    await userEvent.type(nameInput, "Amuro Ray");
    const nextButton = canvas.getByText("▶ 次へ / NEXT");
    await userEvent.click(nextButton);
  },
};

// ── Step 2 ──────────────────────────────────────────────────────────────────

/** Step 2 — 経歴選択（何も選択していない状態） */
export const Step2Empty: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const nameInput = canvas.getByPlaceholderText("例: Amuro Ray");
    await userEvent.type(nameInput, "Amuro Ray");
    const federationButton = canvas.getByText("地球連邦軍");
    await userEvent.click(federationButton);
    const nextButton = canvas.getByText("▶ 次へ / NEXT");
    await userEvent.click(nextButton);
  },
};

/** Step 2 — 経歴選択済み */
export const Step2BackgroundSelected: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const nameInput = canvas.getByPlaceholderText("例: Amuro Ray");
    await userEvent.type(nameInput, "Amuro Ray");
    const federationButton = canvas.getByText("地球連邦軍");
    await userEvent.click(federationButton);
    const nextButton = canvas.getByText("▶ 次へ / NEXT");
    await userEvent.click(nextButton);
    // 経歴選択
    const academyOption = canvas.getByText("士官学校卒 (Academy Elite)");
    await userEvent.click(academyOption);
  },
};

// ── Step 3 ──────────────────────────────────────────────────────────────────

/** Step 3 — ボーナスポイント割り振り（初期状態、5pt残り） */
export const Step3BonusAllocation: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const nameInput = canvas.getByPlaceholderText("例: Amuro Ray");
    await userEvent.type(nameInput, "Amuro Ray");
    const federationButton = canvas.getByText("地球連邦軍");
    await userEvent.click(federationButton);
    let nextButton = canvas.getByText("▶ 次へ / NEXT");
    await userEvent.click(nextButton);
    const academyOption = canvas.getByText("士官学校卒 (Academy Elite)");
    await userEvent.click(academyOption);
    nextButton = canvas.getByText("▶ 次へ / NEXT");
    await userEvent.click(nextButton);
  },
};

/** Step 3 — ポイント全割り振り済み（送信可能） */
export const Step3AllPointsAllocated: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Step 1
    const nameInput = canvas.getByPlaceholderText("例: Amuro Ray");
    await userEvent.type(nameInput, "Char Aznable");
    const zeonButton = canvas.getByText("ジオン公国軍");
    await userEvent.click(zeonButton);
    let nextButton = canvas.getByText("▶ 次へ / NEXT");
    await userEvent.click(nextButton);
    // Step 2
    const survivorOption = canvas.getByText("現場叩き上げ (Street Survivor)");
    await userEvent.click(survivorOption);
    nextButton = canvas.getByText("▶ 次へ / NEXT");
    await userEvent.click(nextButton);
    // Step 3: ポイント割り振り（DEXに2、INTに2、LUKに1）
    const incrementButtons = canvas.getAllByText("＋");
    // DEX +2
    await userEvent.click(incrementButtons[0]);
    await userEvent.click(incrementButtons[0]);
    // INT +2
    await userEvent.click(incrementButtons[1]);
    await userEvent.click(incrementButtons[1]);
    // LUK +1
    await userEvent.click(incrementButtons[4]);
  },
};

// ── フル送信フロー ────────────────────────────────────────────────────────────

/** 送信成功 — fetch をモックして登録成功 → router.push('/') */
export const SubmitSuccess: Story = {
  beforeEach() {
    spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        pilot: {
          id: "pilot-001",
          user_id: "user_test",
          name: "Amuro Ray",
          faction: "FEDERATION",
          background: "ACADEMY_ELITE",
          level: 1,
          exp: 0,
          credits: 1000,
          skill_points: 0,
          skills: {},
          status_points: 0,
          dex: 12,
          intel: 9,
          ref: 13,
          tou: 11,
          luk: 5,
          awq: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        mobile_suit_id: "gm-trainer-001",
        message: "パイロット登録完了。GM Trainer が支給されました。",
      }),
    } as Response);
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Step 1
    const nameInput = canvas.getByPlaceholderText("例: Amuro Ray");
    await userEvent.type(nameInput, "Amuro Ray");
    const federationButton = canvas.getByText("地球連邦軍");
    await userEvent.click(federationButton);
    let nextButton = canvas.getByText("▶ 次へ / NEXT");
    await userEvent.click(nextButton);
    // Step 2
    const academyOption = canvas.getByText("士官学校卒 (Academy Elite)");
    await userEvent.click(academyOption);
    nextButton = canvas.getByText("▶ 次へ / NEXT");
    await userEvent.click(nextButton);
    // Step 3: DEX +2, INT +2, LUK +1
    const incrementButtons = canvas.getAllByText("＋");
    await userEvent.click(incrementButtons[0]);
    await userEvent.click(incrementButtons[0]);
    await userEvent.click(incrementButtons[1]);
    await userEvent.click(incrementButtons[1]);
    await userEvent.click(incrementButtons[4]);
    // 送信
    const submitButton = canvas.getByText("▶ 出撃準備完了 / DEPLOY");
    await userEvent.click(submitButton);
  },
};

/** 送信失敗 — fetch をモックして 500 エラーを返す */
export const SubmitError: Story = {
  beforeEach() {
    spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: async () => ({
        detail: "サーバーエラーが発生しました。しばらくしてから再試行してください。",
      }),
    } as Response);
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Step 1
    const nameInput = canvas.getByPlaceholderText("例: Amuro Ray");
    await userEvent.type(nameInput, "Amuro Ray");
    const federationButton = canvas.getByText("地球連邦軍");
    await userEvent.click(federationButton);
    let nextButton = canvas.getByText("▶ 次へ / NEXT");
    await userEvent.click(nextButton);
    // Step 2
    const academyOption = canvas.getByText("士官学校卒 (Academy Elite)");
    await userEvent.click(academyOption);
    nextButton = canvas.getByText("▶ 次へ / NEXT");
    await userEvent.click(nextButton);
    // Step 3: DEX +2, INT +2, LUK +1
    const incrementButtons = canvas.getAllByText("＋");
    await userEvent.click(incrementButtons[0]);
    await userEvent.click(incrementButtons[0]);
    await userEvent.click(incrementButtons[1]);
    await userEvent.click(incrementButtons[1]);
    await userEvent.click(incrementButtons[4]);
    // 送信
    const submitButton = canvas.getByText("▶ 出撃準備完了 / DEPLOY");
    await userEvent.click(submitButton);
  },
};
