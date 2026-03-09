/* frontend/src/constants.ts */

/**
 * 本番環境フラグ。
 * process.env.NODE_ENV が "production" のときに true になります。
 */
export const IS_PRODUCTION = process.env.NODE_ENV === "production";

/**
 * オンボーディング完了フラグの localStorage キー。
 * ブラウザ（デバイス）単位で保存されるグローバルなフラグです。
 * 値は "true" 文字列で保存されます。
 * 複数ユーザーが同一ブラウザを使用する場合は注意が必要です。
 */
export const ONBOARDING_COMPLETED_KEY = "msbs_onboarding_completed";

/** オンボーディングの進行状態 */
export type OnboardingState =
  | "NOT_STARTED"
  | "BATTLE_STARTED"
  | "BATTLE_FINISHED"
  | "COMPLETED";
