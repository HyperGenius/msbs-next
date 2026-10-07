/* frontend/src/components/BattleViewer/hooks/useHudAttackLog.ts */

import { useMemo } from "react";
import { BattleLog } from "@/types/battle";
import { isCriticalLog } from "./useBattleEvents";

/** HUD ログ 1 行。tone は行の色分けに使う。 */
export interface HudLogLine {
    key: string;
    text: string;
    tone: "dealt" | "taken" | "miss" | "clash";
}

function isHudAttackLog(log: BattleLog): boolean {
    if (!log.actor_id || !log.target_id) return false;
    if (log.action_type === "MISS" || log.action_type === "MELEE_CLASH") return true;
    return (log.action_type === "ATTACK" || log.action_type === "MELEE_COMBO") && !!log.damage && log.damage > 0;
}

/** 全ログから HUD に出す攻撃ログを抜き出し、時刻順に並べる。 */
export function extractHudAttackLogs(logs: BattleLog[]): BattleLog[] {
    return logs.filter(isHudAttackLog).sort((a, b) => a.timestamp - b.timestamp);
}

/** 時刻順の攻撃ログのうち、currentTimestamp より後にある最初のログの位置を返す。 */
export function attackLogEnd(attackLogs: BattleLog[], currentTimestamp: number): number {
    // 再生中は毎 tick 呼ばれるため、二分探索で探す
    let lo = 0;
    let hi = attackLogs.length;
    while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (attackLogs[mid].timestamp <= currentTimestamp + 1e-9) lo = mid + 1;
        else hi = mid;
    }
    return lo;
}

function resultText(log: BattleLog): string {
    if (log.action_type === "MISS") return "MISS";
    if (log.action_type === "MELEE_CLASH") return "鍔迫り合い";
    if (log.action_type === "MELEE_COMBO") return `-${log.damage} (${log.combo_count ?? 1}HIT COMBO)`;
    return isCriticalLog(log) ? `-${log.damage} CRITICAL` : `-${log.damage}`;
}

/**
 * 攻撃ログを `ガンダム ▶ ザクII  ビームライフル  -150` の形に整形する。
 * 名前が分からないユニット（未索敵の敵など）が絡むログは null を返す。
 */
export function formatHudLogLine(
    log: BattleLog,
    names: ReadonlyMap<string, string>,
    playerId: string,
): Omit<HudLogLine, "key"> | null {
    const actorName = names.get(log.actor_id);
    const targetName = log.target_id ? names.get(log.target_id) : undefined;
    if (!actorName || !targetName) return null;

    if (log.action_type === "MELEE_CLASH") {
        return { text: `${actorName} ⚔ ${targetName}  ${resultText(log)}`, tone: "clash" };
    }
    const parts = [`${actorName} ▶ ${targetName}`, log.weapon_name, resultText(log)].filter(Boolean);
    const tone = log.action_type === "MISS" ? "miss" : log.target_id === playerId ? "taken" : "dealt";
    return { text: parts.join("  "), tone };
}

/**
 * HUD に出す行を選ぶ。名前の分かる行のうち、新しい順に最大 limit 件を古い順で返す。
 * currentTimestamp から maxAgeSeconds 以上前の行は出さない。
 */
export function selectHudLogLines(params: {
    attackLogs: BattleLog[];
    currentTimestamp: number;
    names: ReadonlyMap<string, string>;
    playerId: string;
    limit: number;
    maxAgeSeconds: number;
}): HudLogLine[] {
    const { attackLogs, currentTimestamp, names, playerId, limit, maxAgeSeconds } = params;
    const lines: HudLogLine[] = [];
    // 名前の分からない行は件数に数えない。数えると、未索敵の機体同士の交戦が多い戦闘で表示中の行が押し出される
    for (let i = attackLogEnd(attackLogs, currentTimestamp) - 1; i >= 0 && lines.length < limit; i--) {
        if (currentTimestamp - attackLogs[i].timestamp >= maxAgeSeconds) break;
        const line = formatHudLogLine(attackLogs[i], names, playerId);
        // key は attackLogs 上の位置にする。再生が進んでも既存の行を再マウントしない
        if (line) lines.push({ ...line, key: `hud-${i}` });
    }
    return lines.reverse();
}

/** HUD に出す直近の攻撃ログ行を返す。 */
export function useHudAttackLog({
    logs,
    currentTimestamp,
    names,
    playerId,
    limit,
    maxAgeSeconds,
}: {
    logs: BattleLog[];
    currentTimestamp: number;
    names: ReadonlyMap<string, string>;
    playerId: string;
    limit: number;
    /** リプレイ時刻で数える。一時停止中は行が消えない。 */
    maxAgeSeconds: number;
}): HudLogLine[] {
    const attackLogs = useMemo(() => extractHudAttackLogs(logs), [logs]);

    return useMemo(
        () => selectHudLogLines({ attackLogs, currentTimestamp, names, playerId, limit, maxAgeSeconds }),
        [attackLogs, currentTimestamp, names, playerId, limit, maxAgeSeconds],
    );
}
