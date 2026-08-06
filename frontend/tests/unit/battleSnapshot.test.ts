import { describe, it, expect } from "vitest";
import { getBattleSnapshot } from "@/components/BattleViewer/hooks/useBattleSnapshot";
import { BattleLog } from "@/types/battle";
import { MobileSuit } from "@/types/mobileSuit";

/** テスト用の最小構成MS */
const baseMs: MobileSuit = {
    id: "unit-1",
    name: "Test MS",
    max_hp: 1000,
    current_hp: 1000,
    armor: 0,
    mobility: 1,
    position: { x: 0, y: 0, z: 0 },
    weapons: [],
    side: "PLAYER",
    tactics: { priority: "CLOSEST", range: "RANGED" },
};

/** velocity_snapshot 付きの MOVE ログを1件作るヘルパー */
function moveLog(timestamp: number): BattleLog {
    return {
        timestamp,
        actor_id: "unit-1",
        action_type: "MOVE",
        message: "moving",
        position_snapshot: { x: 10, y: 0, z: 10 },
        velocity_snapshot: { x: 5, y: 0, z: 5 },
    };
}

describe("getBattleSnapshot: velocity外挿のdt上限", () => {
    it("直近のvelocity_snapshotからの経過時間が短い場合は外挿する", () => {
        const logs = [moveLog(10.0)];
        const snapshot = getBattleSnapshot("unit-1", baseMs, logs, 10.5); // dt = 0.5s
        expect(snapshot.pos.x).toBeCloseTo(10 + 5 * 0.5);
    });

    it("撃破後など長時間velocity_snapshotが更新されない場合は外挿を打ち切り、最後の位置に留める", () => {
        const logs = [
            moveLog(10.0),
            {
                timestamp: 10.1,
                actor_id: "unit-1",
                action_type: "DESTROYED",
                message: "destroyed",
                position_snapshot: { x: 10, y: 0, z: 10 },
                // DESTROYED ログには velocity_snapshot が含まれない
            } as BattleLog,
        ];
        // 撃破から45秒後まで再生位置を進めても、外挿によって遠方へズレてはいけない
        const snapshot = getBattleSnapshot("unit-1", baseMs, logs, 55.0);
        expect(snapshot.pos.x).toBe(10);
        expect(snapshot.pos.z).toBe(10);
    });
});
