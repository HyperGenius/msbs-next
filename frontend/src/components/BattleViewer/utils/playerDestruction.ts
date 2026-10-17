/* frontend/src/components/BattleViewer/utils/playerDestruction.ts */
import { BattleLog } from "@/types/battle";

/** 自機の撃破後も再生を続ける秒数。撃破演出を見せ切るための猶予。 */
export const PLAYER_DESTROYED_GRACE_S = 3;

/** 自機の最初の撃破ログの時刻を返す。撃破されていなければ null。 */
export function findPlayerDestroyedAt(logs: BattleLog[], playerId: string): number | null {
    const log = logs.find((l) => l.action_type === "DESTROYED" && l.actor_id === playerId);
    return log ? log.timestamp : null;
}

/**
 * 閲覧できる最大の時刻を返す。
 * 自機の撃破後の敵の動きは意図的に見せないため、撃破時刻に猶予を足した時刻で打ち切る。
 */
export function getPlaybackLimit(maxTimestamp: number, playerDestroyedAt: number | null): number {
    if (playerDestroyedAt === null) return maxTimestamp;
    return Math.min(maxTimestamp, playerDestroyedAt + PLAYER_DESTROYED_GRACE_S);
}
