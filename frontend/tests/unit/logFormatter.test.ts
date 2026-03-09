/* frontend/tests/unit/logFormatter.test.ts */

import { describe, it, expect } from "vitest";
import { getLogStyle } from "../../src/utils/logFormatter";
import { BattleLog } from "../../src/types/battle";

/** BattleLog のモックを生成するヘルパー */
function makeLog(overrides: Partial<BattleLog> = {}): BattleLog {
    return {
        turn: 1,
        actor_id: "actor-1",
        action_type: "ATTACK",
        message: "",
        position_snapshot: { x: 0, y: 0, z: 0 },
        ...overrides,
    };
}

describe("getLogStyle", () => {
    // ──────────────────────────────────────────────
    // 現在ターンのハイライト
    // ──────────────────────────────────────────────
    it("現在のターンのログは緑系のハイライトスタイルを返す", () => {
        const log = makeLog({ message: "Gundamが[ビーム・ライフル]で攻撃！" });
        const style = getLogStyle(log, true);
        expect(style.borderStyle).toBe("border-green-400");
        expect(style.bgStyle).toBe("bg-green-900/30");
        expect(style.textStyle).toBe("text-white");
    });

    // ──────────────────────────────────────────────
    // リソース関連（待機・EN不足・クールダウン）
    // ──────────────────────────────────────────────
    it("新形式: クールダウン待機メッセージはオレンジ系スタイルを返す", () => {
        const log = makeLog({
            action_type: "WAIT",
            message: "[マ・クベ]のGelgoogは[ジャイアント・バズ]の冷却を待ちながら（残り2ターン）、やむなく待機",
        });
        const style = getLogStyle(log, false);
        expect(style.borderStyle).toBe("border-orange-500");
        expect(style.textStyle).toContain("text-orange-400");
    });

    it("新形式: EN枯渇待機メッセージはオレンジ系スタイルを返す", () => {
        const log = makeLog({
            action_type: "WAIT",
            message: "[マ・クベ]のGelgoogはENが枯渇し、[ビーム・サーベル]を使えず待機中",
        });
        const style = getLogStyle(log, false);
        expect(style.borderStyle).toBe("border-orange-500");
        expect(style.textStyle).toContain("text-orange-400");
    });

    it("新形式: 弾薬切れメッセージはオレンジ系スタイルを返す", () => {
        const log = makeLog({
            action_type: "WAIT",
            message: "[マ・クベ]のGelgoogは[ジャイアント・バズ]の弾薬が尽きており、攻撃手段がない",
        });
        const style = getLogStyle(log, false);
        expect(style.borderStyle).toBe("border-orange-500");
        expect(style.textStyle).toContain("text-orange-400");
    });

    it("旧形式: EN不足メッセージはオレンジ系スタイルを返す", () => {
        const log = makeLog({
            action_type: "WAIT",
            message: "GelgoogはEN不足のため攻撃できない（待機）",
        });
        const style = getLogStyle(log, false);
        expect(style.borderStyle).toBe("border-orange-500");
    });

    // ──────────────────────────────────────────────
    // 攻撃ログ（武器名付き新形式）
    // ──────────────────────────────────────────────
    it("武器名付き攻撃ログ（装甲なし）はデフォルトスタイルを返す", () => {
        const log = makeLog({
            action_type: "ATTACK",
            message: "[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！ (命中: 75%)",
        });
        const style = getLogStyle(log, false);
        expect(style.borderStyle).toBe("border-green-900");
        expect(style.textStyle).toBe("text-green-600");
    });

    it("武器名なし（格闘攻撃）はデフォルトスタイルを返す", () => {
        const log = makeLog({
            action_type: "ATTACK",
            message: "Zakuが[格闘]で攻撃！ (命中: 60%)",
        });
        const style = getLogStyle(log, false);
        expect(style.borderStyle).toBe("border-green-900");
    });

    // ──────────────────────────────────────────────
    // 装甲軽減（新形式）
    // ──────────────────────────────────────────────
    it("新形式・高軽減: 強固な装甲メッセージは紫系スタイルを返す", () => {
        const log = makeLog({
            action_type: "ATTACK",
            message: "[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！ -> 命中！ しかしAcguyの強固な対実弾装甲が衝撃を受け止め、ダメージは軽微に！（30ダメージ）",
        });
        const style = getLogStyle(log, false);
        expect(style.borderStyle).toBe("border-purple-500");
        expect(style.textStyle).toContain("text-purple-400");
    });

    it("新形式・低軽減: 装甲をわずかに弾くメッセージは紫系スタイルを返す", () => {
        const log = makeLog({
            action_type: "ATTACK",
            message: "[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！ -> 命中！ Acguyの対実弾装甲をわずかに弾きながらも、Acguyに50ダメージ！",
        });
        const style = getLogStyle(log, false);
        expect(style.borderStyle).toBe("border-purple-500");
    });

    it("旧形式: [対ビーム装甲によりXX%軽減] メッセージは紫系スタイルを返す", () => {
        const log = makeLog({
            action_type: "ATTACK",
            message: "Gundamの攻撃！ -> 命中！ [対ビーム装甲により30%軽減] Acguyに40ダメージ！",
        });
        const style = getLogStyle(log, false);
        expect(style.borderStyle).toBe("border-purple-500");
    });

    it("旧形式: [対実弾装甲によりXX%軽減] メッセージは紫系スタイルを返す", () => {
        const log = makeLog({
            action_type: "ATTACK",
            message: "Zakuの攻撃！ -> 命中！ [対実弾装甲により12%軽減] Gundamに55ダメージ！",
        });
        const style = getLogStyle(log, false);
        expect(style.borderStyle).toBe("border-purple-500");
    });

    // ──────────────────────────────────────────────
    // 地形・索敵
    // ──────────────────────────────────────────────
    it("DETECTION アクションはシアン系スタイルを返す", () => {
        const log = makeLog({
            action_type: "DETECTION",
            message: "Gundamが敵を発見！",
        });
        const style = getLogStyle(log, false);
        expect(style.borderStyle).toBe("border-cyan-500");
        expect(style.textStyle).toBe("text-cyan-400");
    });

    it("索敵メッセージはシアン系スタイルを返す", () => {
        const log = makeLog({
            action_type: "MOVE",
            message: "Zakuが索敵中 (残距離: 300m)",
        });
        const style = getLogStyle(log, false);
        expect(style.borderStyle).toBe("border-cyan-500");
    });

    // ──────────────────────────────────────────────
    // デフォルト（通常の攻撃・移動）
    // ──────────────────────────────────────────────
    it("通常の移動メッセージはデフォルトスタイルを返す", () => {
        const log = makeLog({
            action_type: "MOVE",
            message: "Zakuが接近中 (残距離: 100m)",
        });
        const style = getLogStyle(log, false);
        expect(style.borderStyle).toBe("border-green-900");
        expect(style.textStyle).toBe("text-green-600");
    });

    it("DESTROYED メッセージはデフォルトスタイルを返す", () => {
        const log = makeLog({
            action_type: "DESTROYED",
            message: "Acguy は爆散した...",
        });
        const style = getLogStyle(log, false);
        expect(style.borderStyle).toBe("border-green-900");
    });
});
