/* frontend/src/utils/logFormatter.ts */

import { BattleLog } from "@/types/battle";

export interface LogStyle {
    borderStyle: string;
    bgStyle: string;
    textStyle: string;
}

/**
 * バトルログのメッセージ内容に応じたスタイルを返す純粋関数。
 *
 * @param log         バトルログエントリ
 * @param isCurrentTurn 現在のターンかどうか
 * @returns CSSクラス文字列を格納した LogStyle オブジェクト
 */
export function getLogStyle(log: BattleLog, isCurrentTurn: boolean): LogStyle {
    if (isCurrentTurn) {
        return {
            borderStyle: "border-green-400",
            bgStyle: "bg-green-900/30",
            textStyle: "text-white",
        };
    }

    // リソース関連メッセージ判定（待機・弾切れ・EN不足・クールダウン）
    const isResourceMessage =
        log.message.includes("弾薬が尽きており") ||
        log.message.includes("弾切れ") ||
        log.message.includes("ENが枯渇") ||
        log.message.includes("EN不足") ||
        log.message.includes("冷却を待ちながら") ||
        log.message.includes("クールダウン") ||
        log.message.includes("待機");

    if (isResourceMessage) {
        return {
            borderStyle: "border-orange-500",
            bgStyle: "",
            textStyle: "text-orange-400 font-semibold",
        };
    }

    // 地形・索敵関連メッセージ判定
    const isTerrainMessage =
        log.action_type === "DETECTION" ||
        log.message.includes("地形") ||
        log.message.includes("索敵");

    if (isTerrainMessage) {
        return {
            borderStyle: "border-cyan-500",
            bgStyle: "",
            textStyle: "text-cyan-400",
        };
    }

    // 属性・装甲関連メッセージ判定
    // 旧形式（[対XXX装甲によりYY%軽減]）および新形式（強固な対XX装甲 / 対XX装甲をわずかに）に対応
    const isAttributeMessage =
        log.message.includes("対ビーム装甲") ||
        log.message.includes("対実弾装甲") ||
        log.message.includes("装甲が衝撃を受け止め") ||
        log.message.includes("装甲をわずかに弾きながら") ||
        log.message.includes("ビーム") ||
        log.message.includes("実弾") ||
        log.message.includes("BEAM") ||
        log.message.includes("PHYSICAL");

    if (isAttributeMessage) {
        return {
            borderStyle: "border-purple-500",
            bgStyle: "",
            textStyle: "text-purple-400",
        };
    }

    // デフォルトスタイル
    return {
        borderStyle: "border-green-900",
        bgStyle: "",
        textStyle: "text-green-600",
    };
}
