/* frontend/src/components/BattleViewer/utils/index.ts */

// デフォルト値定数
export const DEFAULT_MAX_EN = 1000;
export const EN_WARNING_THRESHOLD = 0.2; // 20%以下でEN不足警告
export const RESIST_PATTERN = /(\d+)%軽減/; // 軽減率パターン

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
