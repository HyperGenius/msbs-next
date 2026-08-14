import { describe, it, expect } from "vitest";
import { getBattleSnapshot, SnapshotCache } from "@/components/BattleViewer/hooks/useBattleSnapshot";
import { BattleLog } from "@/types/battle";
import { MobileSuit } from "@/types/mobileSuit";
import { Weapon } from "@/types/weapon";

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

describe("getBattleSnapshot: 差分更新キャッシュ（Issue #465）", () => {
    const weapon: Weapon = {
        id: "w1",
        name: "Test Weapon",
        power: 10,
        range: 100,
        accuracy: 80,
        max_ammo: 5,
        en_cost: 10,
        cool_down_turn: 3,
    };
    const msWithWeapon: MobileSuit = { ...baseMs, weapons: [weapon], max_en: 100 };

    /** 位置・HP・EN・弾薬・向き・ターゲットが変化する一連のログ */
    const logs: BattleLog[] = [
        { timestamp: 1.0, actor_id: "unit-1", action_type: "MOVE", message: "m", position_snapshot: { x: 1, y: 0, z: 0 }, velocity_snapshot: { x: 1, y: 0, z: 0 }, heading: 10 },
        { timestamp: 2.0, actor_id: "unit-1", action_type: "TARGET_SELECTION", message: "t", position_snapshot: { x: 1, y: 0, z: 0 }, target_id: "enemy-1" },
        { timestamp: 3.0, actor_id: "unit-1", action_type: "ATTACK", message: "a", position_snapshot: { x: 1, y: 0, z: 0 }, target_id: "enemy-1", weapon_id: "w1" },
        { timestamp: 4.0, actor_id: "enemy-1", action_type: "ATTACK", message: "a2", position_snapshot: { x: 0, y: 0, z: 0 }, target_id: "unit-1", damage: 50 },
        { timestamp: 5.0, actor_id: "unit-1", action_type: "MOVE", message: "m2", position_snapshot: { x: 5, y: 0, z: 0 }, velocity_snapshot: { x: 0, y: 0, z: 0 }, heading: 90 },
        { timestamp: 6.0, actor_id: "unit-1", action_type: "ATTACK", message: "a3", position_snapshot: { x: 5, y: 0, z: 0 }, target_id: "enemy-1", weapon_id: "w1" },
    ];

    it("キャッシュを使って時系列順に進めた結果は、毎回全走査した結果と一致する", () => {
        const cache: SnapshotCache = new Map();
        const timestamps = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5];
        for (const ts of timestamps) {
            const cached = getBattleSnapshot("unit-1", msWithWeapon, logs, ts, cache);
            const fresh = getBattleSnapshot("unit-1", msWithWeapon, logs, ts);
            expect(cached).toEqual(fresh);
        }
    });

    it("シーク（巻き戻し）が発生してもキャッシュなしの結果と一致する", () => {
        const cache: SnapshotCache = new Map();
        const timestamps = [6.5, 5.5, 1.0, 4.5, 0.0, 6.5];
        for (const ts of timestamps) {
            const cached = getBattleSnapshot("unit-1", msWithWeapon, logs, ts, cache);
            const fresh = getBattleSnapshot("unit-1", msWithWeapon, logs, ts);
            expect(cached).toEqual(fresh);
        }
    });

    it("キーが異なれば同一ユニットでも独立したキャッシュとして扱われる（currentTimestamp / prevTimestamp の並走に対応）", () => {
        const cache: SnapshotCache = new Map();
        const current = getBattleSnapshot("unit-1", msWithWeapon, logs, 3.5, cache, "unit-1");
        const prev = getBattleSnapshot("unit-1", msWithWeapon, logs, 2.5, cache, "unit-1:prev");
        expect(current).toEqual(getBattleSnapshot("unit-1", msWithWeapon, logs, 3.5));
        expect(prev).toEqual(getBattleSnapshot("unit-1", msWithWeapon, logs, 2.5));
    });
});
