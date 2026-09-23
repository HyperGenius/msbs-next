/* frontend/src/components/BattleViewer/hooks/useBattleEvents.ts */

import { useMemo } from "react";
import { BattleLog } from "@/types/battle";
import { AttackEvent, TracerKind } from "../types";
import { isBeamWeapon, RESIST_PATTERN } from "../utils";

/** useBattleEvents の返却型 */
export interface BattleEventsResult {
    /** 現在タイムスタンプの攻撃。ログの出現順に並ぶ。 */
    attacks: AttackEvent[];
    /** 現在タイムスタンプで攻撃アクション中のユニット ID セット（射撃反動アニメーション用） */
    attackingUnitIds: Set<string>;
    /** 現在タイムスタンプでクリティカルを受けたユニット ID セット（機体フラッシュ用） */
    criticalTargetIds: Set<string>;
}

export function isCriticalLog(log: BattleLog): boolean {
    return log.is_crit === true || log.message.includes("クリティカルヒット");
}

function resolveTracerKind(log: BattleLog, beamWeaponIds: ReadonlySet<string>): TracerKind {
    if (log.weapon_id && beamWeaponIds.has(log.weapon_id)) return "BEAM";
    return isBeamWeapon(log.weapon_name) ? "BEAM" : "BULLET";
}

// RESIST の判定文字列は現行バックエンドの文言と一致していない。
// 判定を直すまで本番では resistPercent が付かない。
function parseResistPercent(message: string): number | undefined {
    if (!message.includes("対ビーム装甲により") && !message.includes("対実弾装甲により")) {
        return undefined;
    }
    const match = message.match(RESIST_PATTERN);
    return match ? Number(match[1]) : undefined;
}

/**
 * 1 タイムスタンプ分のログから攻撃演出データを作る。
 *
 * @param beamWeaponIds `type === "BEAM"` の武器 ID。武器名だけでビームか判定できない武器を補う。
 */
export function computeAttackEvents(
    timestampLogs: BattleLog[],
    beamWeaponIds: ReadonlySet<string> = new Set(),
): AttackEvent[] {
    const attacks: AttackEvent[] = [];
    for (const log of timestampLogs) {
        if (!log.actor_id || !log.target_id) continue;
        const base = {
            attackerId: log.actor_id,
            targetId: log.target_id,
            weaponName: log.weapon_name,
            tracerKind: resolveTracerKind(log, beamWeaponIds),
        };

        if (log.action_type === "MISS") {
            attacks.push({ ...base, impact: "miss", damage: 0 });
        } else if (log.action_type === "MELEE_COMBO" && log.damage && log.damage > 0) {
            attacks.push({ ...base, impact: "combo", damage: log.damage, comboCount: log.combo_count ?? 1 });
        } else if (log.action_type === "ATTACK" && log.damage && log.damage > 0) {
            attacks.push({
                ...base,
                impact: isCriticalLog(log) ? "critical" : "hit",
                damage: log.damage,
                resistPercent: parseResistPercent(log.message),
            });
        }
    }
    return attacks;
}

/**
 * @param timestampLogs 現在タイムスタンプ分にフィルタ済みのログ（呼び出し元で計算し、他コンポーネントと共有する。Issue #467）
 */
export function useBattleEvents(
    timestampLogs: BattleLog[],
    beamWeaponIds: ReadonlySet<string>,
): BattleEventsResult {
    return useMemo(() => {
        const attacks = computeAttackEvents(timestampLogs, beamWeaponIds);

        const attackingUnitIds = new Set<string>();
        for (const log of timestampLogs) {
            if ((log.action_type === "ATTACK" || log.action_type === "MELEE_COMBO") && log.actor_id) {
                attackingUnitIds.add(log.actor_id);
            }
        }

        const criticalTargetIds = new Set(
            attacks.filter((a) => a.impact === "critical").map((a) => a.targetId),
        );

        return { attacks, attackingUnitIds, criticalTargetIds };
    }, [timestampLogs, beamWeaponIds]);
}
