/* frontend/src/components/BattleViewer/__stories__/battleScenarioFixtures.ts */

import { BattleLog, MobileSuit, Vector3 } from "@/types/battle";
import {
    attackHitLog,
    destroyedLog,
    detectionLog,
    makeMobileSuit,
    meleeComboLog,
    missLog,
    moveLog,
    PLAYER_ID,
    WEAPONS,
} from "./battleLogFixtures";

/** [時刻（秒）, 位置] の組。間は線形補間する。 */
type Keyframe = [number, Vector3];

// MOVE ログの出力間隔（秒）。
// getBattleSnapshot の速度外挿は 1 秒で打ち切られるため、それより短くする。
const MOVE_LOG_INTERVAL_S = 0.5;

function positionAt(keyframes: Keyframe[], t: number): Vector3 {
    const next = keyframes.findIndex(([kt]) => kt >= t);
    if (next === -1) return keyframes[keyframes.length - 1][1];
    if (next === 0) return keyframes[0][1];
    const [t0, p0] = keyframes[next - 1];
    const [t1, p1] = keyframes[next];
    const r = (t - t0) / (t1 - t0);
    return { x: p0.x + (p1.x - p0.x) * r, y: p0.y + (p1.y - p0.y) * r, z: p0.z + (p1.z - p0.z) * r };
}

function velocityAt(keyframes: Keyframe[], t: number): Vector3 {
    const next = keyframes.findIndex(([kt]) => kt > t);
    if (next <= 0) return { x: 0, y: 0, z: 0 };
    const [t0, p0] = keyframes[next - 1];
    const [t1, p1] = keyframes[next];
    const dt = t1 - t0;
    return { x: (p1.x - p0.x) / dt, y: (p1.y - p0.y) / dt, z: (p1.z - p0.z) / dt };
}

/** 生存中の各時刻について、キーフレーム上の位置と速度を持つ MOVE ログを作る。 */
function moveLogs(unit: MobileSuit, keyframes: Keyframe[], until: number): BattleLog[] {
    const logs: BattleLog[] = [];
    for (let i = 0; i * MOVE_LOG_INTERVAL_S <= until + 1e-9; i++) {
        const t = Math.round(i * MOVE_LOG_INTERVAL_S * 10) / 10;
        logs.push(moveLog(t, unit, positionAt(keyframes, t), velocityAt(keyframes, t)));
    }
    return logs;
}

export interface BattleScenario {
    logs: BattleLog[];
    player: MobileSuit;
    enemies: MobileSuit[];
}

/**
 * 自機 1 機と敵 2 機の短いバトルを作る。
 * Hit / Miss / Critical / 格闘コンボ / 撃破 / 途中索敵を一通り含む。
 */
export function buildSkirmishScenario(): BattleScenario {
    const playerPath: Keyframe[] = [
        [0, { x: 2200, y: 0, z: 2500 }],
        [4.5, { x: 2488, y: 0, z: 2500 }],
        [7.0, { x: 2560, y: 0, z: 2740 }],
        [8.0, { x: 2560, y: 0, z: 2740 }],
    ];
    const zakuPath: Keyframe[] = [
        [0, { x: 2800, y: 0, z: 2500 }],
        [4.5, { x: 2512, y: 0, z: 2500 }],
    ];
    const rickDomPath: Keyframe[] = [
        [0, { x: 2700, y: 0, z: 2950 }],
        [7.0, { x: 2580, y: 0, z: 2760 }],
    ];

    const player = makeMobileSuit({
        id: PLAYER_ID,
        name: "ガンダム",
        side: "PLAYER",
        position: playerPath[0][1],
        weapons: [WEAPONS.BEAM_RIFLE, WEAPONS.BEAM_SABER],
    });
    const zaku = makeMobileSuit({
        id: "story-enemy-zaku",
        name: "ザクII (NPC)",
        side: "ENEMY",
        position: zakuPath[0][1],
        weapons: [WEAPONS.MACHINE_GUN, WEAPONS.HEAT_HAWK],
        is_npc: true,
    });
    const rickDom = makeMobileSuit({
        id: "story-enemy-rickdom",
        name: "リック・ドム (NPC)",
        side: "ENEMY",
        position: rickDomPath[0][1],
        weapons: [WEAPONS.MACHINE_GUN, WEAPONS.HEAT_HAWK],
        is_npc: true,
    });

    const pp = (t: number) => positionAt(playerPath, t);
    const zp = (t: number) => positionAt(zakuPath, t);
    const rp = (t: number) => positionAt(rickDomPath, t);
    const { BEAM_RIFLE, BEAM_SABER, MACHINE_GUN } = WEAPONS;

    const events: BattleLog[] = [
        detectionLog(0, player, zaku, pp(0)),
        attackHitLog({ timestamp: 1.0, actor: player, target: zaku, actorPos: pp(1.0), weapon: BEAM_RIFLE, damage: 150 }),
        missLog({ timestamp: 1.5, actor: zaku, target: player, actorPos: zp(1.5), weapon: MACHINE_GUN }),
        detectionLog(2.0, player, rickDom, pp(2.0)),
        attackHitLog({ timestamp: 2.5, actor: player, target: zaku, actorPos: pp(2.5), weapon: BEAM_RIFLE, damage: 350, isCrit: true }),
        attackHitLog({ timestamp: 3.0, actor: rickDom, target: player, actorPos: rp(3.0), weapon: MACHINE_GUN, damage: 60 }),
        attackHitLog({ timestamp: 3.5, actor: zaku, target: player, actorPos: zp(3.5), weapon: MACHINE_GUN, damage: 40 }),
        attackHitLog({ timestamp: 4.5, actor: player, target: zaku, actorPos: pp(4.5), weapon: BEAM_SABER, damage: 250 }),
        meleeComboLog({ timestamp: 4.5, actor: player, target: zaku, actorPos: pp(4.5), weapon: BEAM_SABER, comboCount: 2, totalDamage: 750 }),
        destroyedLog(4.5, zaku, zp(4.5)),
        missLog({ timestamp: 5.5, actor: rickDom, target: player, actorPos: rp(5.5), weapon: MACHINE_GUN }),
        attackHitLog({ timestamp: 6.0, actor: player, target: rickDom, actorPos: pp(6.0), weapon: BEAM_RIFLE, damage: 200 }),
        attackHitLog({ timestamp: 7.0, actor: player, target: rickDom, actorPos: pp(7.0), weapon: BEAM_SABER, damage: 250 }),
        meleeComboLog({ timestamp: 7.0, actor: player, target: rickDom, actorPos: pp(7.0), weapon: BEAM_SABER, comboCount: 3, totalDamage: 1125 }),
        destroyedLog(7.0, rickDom, rp(7.0)),
    ];

    // 同時刻では MOVE ログを演出ログより前に並べる（sort は安定ソート）
    const logs = [
        ...moveLogs(player, playerPath, 8.0),
        ...moveLogs(zaku, zakuPath, 4.5),
        ...moveLogs(rickDom, rickDomPath, 7.0),
        ...events,
    ].sort((a, b) => a.timestamp - b.timestamp);

    return { logs, player, enemies: [zaku, rickDom] };
}
