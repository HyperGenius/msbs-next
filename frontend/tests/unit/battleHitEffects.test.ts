/* frontend/tests/unit/battleHitEffects.test.ts */
import { describe, it, expect } from "vitest";
import { computeAttackEvents } from "@/components/BattleViewer/hooks/useBattleEvents";
import {
  EFFECT_TIMING,
  AttackEffects,
  missTracerEnd,
  spawnAttackEffects,
} from "@/components/BattleViewer/hooks/useAttackEffectQueue";
import {
  extractHudAttackLogs,
  formatHudLogLine,
  recentAttackLogRange,
} from "@/components/BattleViewer/hooks/useHudAttackLog";
import { AttackEvent } from "@/components/BattleViewer/types";
import { HIT_EFFECT_COLORS } from "@/components/BattleViewer/utils";
import { BattleLog } from "@/types/battle";

const PLAYER_ID = "player";
const ENEMY_ID = "enemy";

function makeLog(overrides: Partial<BattleLog> = {}): BattleLog {
  return {
    timestamp: 1,
    actor_id: PLAYER_ID,
    target_id: ENEMY_ID,
    action_type: "ATTACK",
    message: "ガンダムが[ビームライフル]で攻撃！ -> 命中！",
    position_snapshot: { x: 0, y: 0, z: 0 },
    weapon_name: "ビームライフル",
    damage: 150,
    ...overrides,
  };
}

function makeAttack(overrides: Partial<AttackEvent> = {}): AttackEvent {
  return {
    attackerId: PLAYER_ID,
    targetId: ENEMY_ID,
    weaponName: "ビームライフル",
    tracerKind: "BEAM",
    impact: "hit",
    damage: 150,
    ...overrides,
  };
}

const EMPTY: AttackEffects = { tracers: [], labels: [], impacts: [] };
const POSITIONS = new Map([
  [PLAYER_ID, { x: 0, y: 0, z: 0 }],
  [ENEMY_ID, { x: 400, y: 0, z: 0 }],
]);

function spawn(attacks: AttackEvent[], options: { active?: AttackEffects; now?: number; positions?: Map<string, { x: number; y: number; z: number }> } = {}) {
  let id = 0;
  return spawnAttackEffects({
    active: options.active ?? EMPTY,
    attacks,
    positions: options.positions ?? POSITIONS,
    playerId: PLAYER_ID,
    now: options.now ?? 1000,
    nextId: () => `id-${id++}`,
  });
}

describe("computeAttackEvents", () => {
  it("ATTACK / MISS / MELEE_COMBO を攻撃演出に変換する", () => {
    const events = computeAttackEvents([
      makeLog(),
      makeLog({ action_type: "MISS", damage: undefined }),
      makeLog({ action_type: "MELEE_COMBO", damage: 750, combo_count: 2, weapon_name: "ビームサーベル" }),
    ]);
    expect(events.map((e) => e.impact)).toEqual(["hit", "miss", "combo"]);
    expect(events[2].comboCount).toBe(2);
  });

  it("クリティカルは message か is_crit で判定する", () => {
    const [byMessage, byFlag] = computeAttackEvents([
      makeLog({ message: "ガンダムが攻撃！ -> ★★ クリティカルヒット！！" }),
      makeLog({ is_crit: true }),
    ]);
    expect(byMessage.impact).toBe("critical");
    expect(byFlag.impact).toBe("critical");
  });

  it("武器 ID が BEAM 武器なら武器名に関係なくビーム射線にする", () => {
    const [event] = computeAttackEvents(
      [makeLog({ weapon_name: "メガ粒子砲", weapon_id: "mega" })],
      new Set(["mega"]),
    );
    expect(event.tracerKind).toBe("BEAM");
  });

  it("武器名にビームを含まない武器は実弾射線にする", () => {
    const [event] = computeAttackEvents([makeLog({ weapon_name: "ザクマシンガン" })]);
    expect(event.tracerKind).toBe("BULLET");
  });

  it("ダメージ 0 の ATTACK は演出を作らない", () => {
    expect(computeAttackEvents([makeLog({ damage: 0 })])).toEqual([]);
  });
});

describe("spawnAttackEffects", () => {
  it("武器名は発射側に出し、被弾側には出さない", () => {
    const { labels, impacts } = spawn([makeAttack()]);
    expect(labels).toHaveLength(1);
    expect(labels[0].attackerId).toBe(PLAYER_ID);
    expect(labels[0].position).toEqual(POSITIONS.get(PLAYER_ID));
    expect(impacts[0].position).toEqual(POSITIONS.get(ENEMY_ID));
    expect(impacts[0].text).toBe("-150");
  });

  it("ビームは射線が届く時刻に着弾演出を始める", () => {
    const { tracers, impacts } = spawn([makeAttack()], { now: 1000 });
    expect(tracers[0].startAt).toBe(1000);
    expect(impacts[0].delayMs).toBe(EFFECT_TIMING.beamImpactDelayMs);
    expect(impacts[0].startAt).toBe(1000 + EFFECT_TIMING.beamImpactDelayMs);
  });

  it("実弾は飛翔時間の後に着弾し、飛翔時間は上下限に収まる", () => {
    const { tracers, impacts } = spawn([makeAttack({ tracerKind: "BULLET" })]);
    expect(tracers[0].durationMs).toBe(impacts[0].delayMs);
    expect(impacts[0].delayMs).toBeGreaterThanOrEqual(EFFECT_TIMING.bulletMinFlightMs);
    expect(impacts[0].delayMs).toBeLessThanOrEqual(EFFECT_TIMING.bulletMaxFlightMs);
  });

  it("連続ヒットの数字は段を分けて重ならない", () => {
    const { impacts } = spawn([makeAttack(), makeAttack(), makeAttack()]);
    expect(impacts.map((i) => i.slot)).toEqual([0, 1, 2]);
  });

  it("前のタイムスタンプの数字が表示中なら、その上の段に積む", () => {
    const first = spawn([makeAttack()], { now: 1000 });
    const second = spawn([makeAttack()], { active: first, now: 1100 });
    expect(second.impacts.map((i) => i.slot)).toEqual([0, 1]);
  });

  it("表示が終わった数字の段は再利用する", () => {
    const first = spawn([makeAttack()], { now: 1000 });
    const later = 1000 + EFFECT_TIMING.beamImpactDelayMs + EFFECT_TIMING.damageNumberMs + 1;
    const second = spawn([makeAttack()], { active: first, now: later });
    expect(second.impacts).toHaveLength(1);
    expect(second.impacts[0].slot).toBe(0);
  });

  it("同じ武器の連射は武器名を積まずに出し直す", () => {
    const first = spawn([makeAttack()], { now: 1000 });
    const second = spawn([makeAttack()], { active: first, now: 1100 });
    expect(second.labels).toHaveLength(1);
    expect(second.labels[0].startAt).toBe(1100);
  });

  it("格闘コンボは射線と武器名を出さず、ATTACK の着弾より後に数字を出す", () => {
    const { tracers, labels, impacts } = spawn([
      makeAttack({ weaponName: "ビームサーベル" }),
      makeAttack({ weaponName: "ビームサーベル", impact: "combo", damage: 750, comboCount: 2 }),
    ]);
    expect(tracers).toHaveLength(1);
    expect(labels).toHaveLength(1);
    expect(impacts[1].delayMs).toBe(impacts[0].delayMs + EFFECT_TIMING.comboExtraDelayMs);
    expect(impacts[1].caption).toBe("2HIT COMBO");
  });

  it("与ダメージ・被ダメージ・MISS で数字の色を分ける", () => {
    const { impacts } = spawn([
      makeAttack(),
      makeAttack({ attackerId: ENEMY_ID, targetId: PLAYER_ID }),
      makeAttack({ impact: "miss", damage: 0 }),
    ]);
    expect(impacts.map((i) => i.color)).toEqual([
      HIT_EFFECT_COLORS.dealt,
      HIT_EFFECT_COLORS.taken,
      HIT_EFFECT_COLORS.miss,
    ]);
    expect(impacts[2].text).toBe("MISS");
  });

  it("MISS の射線は目標を外れた位置へ伸びる", () => {
    const { tracers } = spawn([makeAttack({ impact: "miss", damage: 0 })]);
    expect(tracers[0].to).toEqual(missTracerEnd(POSITIONS.get(PLAYER_ID)!, POSITIONS.get(ENEMY_ID)!));
    expect(tracers[0].to).not.toEqual(POSITIONS.get(ENEMY_ID));
  });

  it("発射側の位置が分からない攻撃は、着弾演出だけを出す", () => {
    const positions = new Map([[PLAYER_ID, { x: 0, y: 0, z: 0 }]]);
    const { tracers, labels, impacts } = spawn([makeAttack({ attackerId: "unknown", targetId: PLAYER_ID })], {
      positions,
    });
    expect(tracers).toHaveLength(0);
    expect(labels).toHaveLength(0);
    expect(impacts).toHaveLength(1);
  });
});

describe("HUD ログ", () => {
  const names = new Map([
    [PLAYER_ID, "ガンダム"],
    [ENEMY_ID, "ザクII"],
  ]);

  it("発射側 ▶ 被弾側 武器名 結果 の形に整形する", () => {
    expect(formatHudLogLine(makeLog(), names, PLAYER_ID)).toEqual({
      text: "ガンダム ▶ ザクII  ビームライフル  -150",
      tone: "dealt",
    });
  });

  it("被ダメージ・MISS・コンボ・クリティカルを区別する", () => {
    const taken = formatHudLogLine(makeLog({ actor_id: ENEMY_ID, target_id: PLAYER_ID }), names, PLAYER_ID);
    const miss = formatHudLogLine(makeLog({ action_type: "MISS" }), names, PLAYER_ID);
    const combo = formatHudLogLine(makeLog({ action_type: "MELEE_COMBO", damage: 750, combo_count: 2 }), names, PLAYER_ID);
    const crit = formatHudLogLine(makeLog({ is_crit: true, damage: 350 }), names, PLAYER_ID);
    expect(taken?.tone).toBe("taken");
    expect(miss?.text.endsWith("MISS")).toBe(true);
    expect(miss?.tone).toBe("miss");
    expect(combo?.text.endsWith("-750 (2HIT COMBO)")).toBe(true);
    expect(crit?.text.endsWith("-350 CRITICAL")).toBe(true);
  });

  it("名前の分からないユニットが絡むログは出さない", () => {
    expect(formatHudLogLine(makeLog({ actor_id: "hidden" }), names, PLAYER_ID)).toBeNull();
  });

  it("現在時刻以前の直近ログの範囲を返す", () => {
    const attackLogs = extractHudAttackLogs([
      makeLog({ timestamp: 3 }),
      makeLog({ timestamp: 1 }),
      makeLog({ timestamp: 2 }),
      makeLog({ timestamp: 4 }),
      makeLog({ timestamp: 2.5, action_type: "MOVE" }),
    ]);
    expect(attackLogs.map((l) => l.timestamp)).toEqual([1, 2, 3, 4]);
    expect(recentAttackLogRange(attackLogs, 3, 2)).toEqual([1, 3]);
    expect(recentAttackLogRange(attackLogs, 0.5, 2)).toEqual([0, 0]);
  });
});
