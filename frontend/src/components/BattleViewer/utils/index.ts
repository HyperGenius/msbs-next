/* frontend/src/components/BattleViewer/utils/index.ts */

// デフォルト値定数
export const DEFAULT_MAX_EN = 1000;
export const EN_WARNING_THRESHOLD = 0.2; // EN比率がこれ未満でENゲージを赤くする
/** en_recovery 未指定時の EN 回復量 (/s)。バックエンドの MobileSuit.en_recovery の既定値に合わせる。 */
export const DEFAULT_EN_RECOVERY = 100;
/** boost_en_cost 未指定時のブースト中 EN 消費量 (/s)。バックエンドの DEFAULT_BOOST_EN_COST に合わせる。 */
export const DEFAULT_BOOST_EN_COST = 5.0;
/** ENゲージを点滅させる details.reason_code（backend/app/engine/constants.py と同じ値） */
export const EN_SHORTAGE_REASON_CODES: ReadonlySet<string> = new Set(["EN_SHORTAGE", "EN_DEPLETED"]);
export const RESIST_PATTERN = /(\d+)%軽減/; // 軽減率パターン
/** シミュレーションのステップ幅（秒）。prevSnapshot 計算に使用する。 */
export const SIMULATION_STEP_S = 0.1;

// 色計算用のヘルパー
export function getHpColor(current: number, max: number) {
    const ratio = current / max;
    if (ratio > 0.5) return "green"; // 余裕
    if (ratio > 0.2) return "yellow"; // 注意
    return "red"; // 危険
}

// HPバーの色を計算
export function getHpBarColor(ratio: number): string {
    if (ratio > 0.5) return '#3b82f6'; // 青
    if (ratio > 0.2) return '#eab308'; // 黄
    return '#ef4444'; // 赤
}

// 敵のHPバーの色を計算
export function getEnemyHpBarColor(ratio: number): string {
    if (ratio > 0.5) return '#ef4444'; // 赤
    if (ratio > 0.2) return '#eab308'; // 黄
    return '#dc2626'; // 濃い赤
}

// 環境に応じた背景色を決定
export function getEnvironmentColor(environment: string) {
    switch (environment) {
        case "GROUND":
            return "#1a3a1a"; // 濃い緑
        case "COLONY":
            return "#2a2a3a"; // 濃い紫
        case "UNDERWATER":
            return "#0a2a3a"; // 濃い青
        case "SPACE":
        default:
            return "#000000"; // 黒
    }
}

/** ビーム武器かどうかを weapon_name の文字列で判定する（武器 ID から型を引けない場合のフォールバック）。 */
export function isBeamWeapon(weaponName?: string): boolean {
    if (!weaponName) return false;
    const lower = weaponName.toLowerCase();
    return lower.includes("beam") || weaponName.includes("ビーム") || lower.includes("mega particle");
}

/** ヒット演出の配色。モックアップ（msbs_hit_effect_final_mockup.html）に合わせる。 */
export const HIT_EFFECT_COLORS = {
    /** 自機以外が受けたダメージ（与ダメージ） */
    dealt: "#ffd84a",
    /** 自機が受けたダメージ */
    taken: "#ff5a4e",
    miss: "#9aa0a6",
    resist: "#4caf50",
    flashCore: "#ffffff",
    flashRing: "#ffd84a",
    tracerBeam: "#6fe6ff",
    tracerBullet: "#ffb36b",
} as const;
