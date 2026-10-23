/* frontend/src/components/BattleViewer/utils/retreat.ts */
import { BattleLog } from "@/types/battle";

/** 離脱の表示を残す時間（ゲーム内秒）。再生位置を戻したときも同じ見え方になるよう、ログの時刻から求める */
export const RETREAT_NOTICE_SECONDS = 3;

/** 離脱の通知 1 件分 */
export interface RetreatNotice {
    unitId: string;
    timestamp: number;
    pos: { x: number; y: number; z: number };
}

/** 指定時刻までに撤退ポイントへ到達して離脱したユニットの ID を返す（RETREAT_COMPLETE） */
export function getRetreatedUnitIds(logs: BattleLog[], currentTimestamp: number): Set<string> {
    const ids = new Set<string>();
    for (const log of logs) {
        if (log.timestamp > currentTimestamp) break;
        if (log.action_type === "RETREAT_COMPLETE") ids.add(String(log.actor_id));
    }
    return ids;
}

/** 直近 `RETREAT_NOTICE_SECONDS` 秒以内に離脱したユニットの通知を返す */
export function getRecentRetreatNotices(logs: BattleLog[], currentTimestamp: number): RetreatNotice[] {
    const notices: RetreatNotice[] = [];
    for (const log of logs) {
        if (log.timestamp > currentTimestamp) break;
        if (
            log.action_type === "RETREAT_COMPLETE" &&
            log.position_snapshot &&
            currentTimestamp - log.timestamp < RETREAT_NOTICE_SECONDS
        ) {
            notices.push({
                unitId: String(log.actor_id),
                timestamp: log.timestamp,
                pos: log.position_snapshot,
            });
        }
    }
    return notices;
}
