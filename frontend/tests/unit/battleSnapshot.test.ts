import { describe, it, expect } from "vitest";
import {
    findLatestEnShortageEvent,
    getBattleSnapshot,
    isEnShortageLog,
    SnapshotCache,
} from "@/components/BattleViewer/hooks/useBattleSnapshot";
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

    it("まだ一度も攻撃していない戦闘開始直後はクールダウン警告を誤って出さない", () => {
        // cool_down_turn=3（0.3秒）に対し、ATTACKログが1件も無い状態で currentTimestamp=0.1 を計算する。
        // lastAttackTimestamp の初期値を 0 のままにすると 0.1 - 0 = 0.1 < 0.3 となり誤検知してしまう。
        const noAttackLogs: BattleLog[] = [
            { timestamp: 0.05, actor_id: "unit-1", action_type: "MOVE", message: "m", position_snapshot: { x: 0, y: 0, z: 0 }, velocity_snapshot: { x: 0, y: 0, z: 0 } },
        ];
        const cache: SnapshotCache = new Map();
        const cached = getBattleSnapshot("unit-1", msWithWeapon, noAttackLogs, 0.1, cache);
        const fresh = getBattleSnapshot("unit-1", msWithWeapon, noAttackLogs, 0.1);
        expect(cached.warnings).not.toContain("cooldown");
        expect(fresh.warnings).not.toContain("cooldown");
        expect(cached).toEqual(fresh);
    });
});

describe("getBattleSnapshot: EN残量の再構築（Issue #534）", () => {
    const beamRifle: Weapon = { id: "beam", name: "Beam Rifle", power: 10, range: 100, accuracy: 80, en_cost: 50 };
    const enMs: MobileSuit = { ...baseMs, weapons: [beamRifle], max_en: 200, en_recovery: 10, boost_en_cost: 20 };
    const pos = { x: 0, y: 0, z: 0 };

    function enLog(timestamp: number, actionType: BattleLog["action_type"], details?: Record<string, unknown>): BattleLog {
        return { timestamp, actor_id: "unit-1", action_type: actionType, message: "", position_snapshot: pos, weapon_id: "beam", details };
    }

    it("通常時は details.en を基準に en_recovery × 経過秒で回復する", () => {
        const logs = [enLog(1.0, "ATTACK", { en: 100 })];
        expect(getBattleSnapshot("unit-1", enMs, logs, 1.0).en).toBeCloseTo(100);
        expect(getBattleSnapshot("unit-1", enMs, logs, 3.5).en).toBeCloseTo(125);
    });

    it("回復は max_en で頭打ちになる", () => {
        const logs = [enLog(1.0, "ATTACK", { en: 150 })];
        expect(getBattleSnapshot("unit-1", enMs, logs, 20.0).en).toBe(200);
    });

    it("MISS ログの details.en も基準値として使う", () => {
        const logs = [enLog(1.0, "ATTACK", { en: 150 }), enLog(2.0, "MISS", { en: 110 })];
        expect(getBattleSnapshot("unit-1", enMs, logs, 3.0).en).toBeCloseTo(120);
    });

    it("ブースト中は回復せず boost_en_cost × 経過秒で減り、0 未満にならない", () => {
        const logs = [enLog(1.0, "BOOST_START", { en: 100 }), enLog(4.0, "BOOST_END", { reason: "EN 枯渇", en: 40, reason_code: "EN_DEPLETED" })];
        expect(getBattleSnapshot("unit-1", enMs, logs, 2.0).en).toBeCloseTo(80);
        // BOOST_END 後は終了時の記録値から回復に戻る
        expect(getBattleSnapshot("unit-1", enMs, logs, 5.0).en).toBeCloseTo(50);

        const longBoost = [enLog(1.0, "BOOST_START", { en: 30 })];
        expect(getBattleSnapshot("unit-1", enMs, longBoost, 10.0).en).toBe(0);
    });

    it("details.en の無い旧ログは en_cost 減算方式にフォールバックする（回復しない）", () => {
        const logs = [enLog(1.0, "ATTACK"), enLog(2.0, "ATTACK")];
        expect(getBattleSnapshot("unit-1", enMs, logs, 10.0).en).toBe(100);
    });

    it("他ユニットの details.en は自機の EN に影響しない", () => {
        const logs = [{ ...enLog(1.0, "ATTACK", { en: 0 }), actor_id: "enemy-1" }];
        expect(getBattleSnapshot("unit-1", enMs, logs, 2.0).en).toBe(200);
    });

    it("シーク（巻き戻し）してもキャッシュなしの結果と一致する", () => {
        const logs = [
            enLog(1.0, "ATTACK", { en: 150 }),
            enLog(2.0, "BOOST_START", { en: 160 }),
            enLog(4.0, "BOOST_END", { en: 120 }),
            enLog(6.0, "ATTACK", { en: 90 }),
        ];
        const cache: SnapshotCache = new Map();
        for (const ts of [7.0, 3.0, 5.0, 1.5, 8.0]) {
            expect(getBattleSnapshot("unit-1", enMs, logs, ts, cache).en).toBeCloseTo(
                getBattleSnapshot("unit-1", enMs, logs, ts).en
            );
        }
    });

    it("EN が少なくても3Dシーン用の警告に EN 不足を含めない", () => {
        const logs = [enLog(1.0, "ATTACK", { en: 0 })];
        expect(getBattleSnapshot("unit-1", enMs, logs, 1.0).warnings).toEqual([]);
    });
});

describe("EN不足イベントの検出（Issue #534）", () => {
    const pos = { x: 0, y: 0, z: 0 };

    it("reason_code が EN_SHORTAGE / EN_DEPLETED のログだけを EN 不足イベントとみなす", () => {
        const make = (actionType: BattleLog["action_type"], details?: Record<string, unknown>): BattleLog => ({
            timestamp: 1, actor_id: "unit-1", action_type: actionType, message: "", position_snapshot: pos, details,
        });
        expect(isEnShortageLog(make("WAIT", { reason_code: "EN_SHORTAGE" }))).toBe(true);
        expect(isEnShortageLog(make("BOOST_END", { reason: "EN 枯渇", en: 0, reason_code: "EN_DEPLETED" }))).toBe(true);
        expect(isEnShortageLog(make("BOOST_END", { reason: "最大継続時間", en: 50 }))).toBe(false);
        expect(isEnShortageLog(make("WAIT"))).toBe(false);
    });

    it("(from, to] の範囲にある最後のイベント時刻を返す", () => {
        const events = [1.0, 2.0, 3.0];
        expect(findLatestEnShortageEvent(events, 1.9, 2.0)).toBe(2.0);
        expect(findLatestEnShortageEvent(events, 0.5, 3.5)).toBe(3.0);
        // 始点ちょうどのイベントは前回の区間で通過済み
        expect(findLatestEnShortageEvent(events, 2.0, 2.9)).toBeNull();
        expect(findLatestEnShortageEvent(events, 3.0, 10.0)).toBeNull();
        expect(findLatestEnShortageEvent([], 0, 10)).toBeNull();
    });
});
