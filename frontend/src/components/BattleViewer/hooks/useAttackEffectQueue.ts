/* frontend/src/components/BattleViewer/hooks/useAttackEffectQueue.ts */

import { useCallback, useEffect, useRef, useState } from "react";
import { AttackEvent, ImpactKind, TracerKind } from "../types";
import { HIT_EFFECT_COLORS } from "../utils";

type Vec3 = { x: number; y: number; z: number };

/** 演出の時間（ms）。着弾側の演出は射線が届いた時刻に合わせて始める。 */
export const EFFECT_TIMING = {
    /** ビーム射線の表示時間。伸び切った後にフェードする。 */
    beamTracerMs: 220,
    beamImpactDelayMs: 150,
    /** 実弾の飛翔速度（m/ms）。距離が変わっても飛翔時間が極端にならないよう上下限を付ける。 */
    bulletSpeedMPerMs: 1.6,
    bulletMinFlightMs: 120,
    bulletMaxFlightMs: 350,
    /** 格闘コンボの追撃は、同じ組の ATTACK の着弾からこの時間だけ遅らせる。 */
    comboExtraDelayMs: 200,
    weaponLabelMs: 900,
    damageNumberMs: 850,
} as const;

const MAX_TRACERS = 20;
const MAX_WEAPON_LABELS = 8;
const MAX_IMPACTS = 15;

// MISS の射線は目標の横上方へ外し、少し先まで伸ばす（ゲーム座標の m）。
const MISS_SIDE_OFFSET_M = 30;
const MISS_UP_OFFSET_M = 20;
const MISS_OVERSHOOT = 1.2;

export interface TracerState {
    id: string;
    kind: TracerKind;
    from: Vec3;
    to: Vec3;
    color: string;
    /** Date.now() 基準の開始時刻。 */
    startAt: number;
    durationMs: number;
}

export interface WeaponLabelState {
    id: string;
    attackerId: string;
    weaponName: string;
    color: string;
    position: Vec3;
    startAt: number;
    /** 同じ発射側で同時に出ているラベルの段。0 が最下段。 */
    slot: number;
}

export interface ImpactState {
    id: string;
    targetId: string;
    kind: ImpactKind;
    position: Vec3;
    text: string;
    color: string;
    caption?: string;
    captionColor?: string;
    /** Date.now() 基準の着弾時刻。 */
    startAt: number;
    /** スポーンから着弾までの時間。CSS の animation-delay に使う。 */
    delayMs: number;
    /** 同じ被弾側で同時に出ている数字の段。0 が最下段。 */
    slot: number;
}

export interface AttackEffects {
    tracers: TracerState[];
    labels: WeaponLabelState[];
    impacts: ImpactState[];
}

const EMPTY_EFFECTS: AttackEffects = { tracers: [], labels: [], impacts: [] };

function distance(a: Vec3, b: Vec3): number {
    return Math.hypot(b.x - a.x, b.y - a.y, b.z - a.z);
}

function bulletFlightMs(from: Vec3, to: Vec3): number {
    const ms = distance(from, to) / EFFECT_TIMING.bulletSpeedMPerMs;
    return Math.min(EFFECT_TIMING.bulletMaxFlightMs, Math.max(EFFECT_TIMING.bulletMinFlightMs, ms));
}

/** MISS 射線の終点。射線に直交する水平方向へずらし、目標を通り過ぎる位置に置く。 */
export function missTracerEnd(from: Vec3, to: Vec3): Vec3 {
    const dx = to.x - from.x;
    const dz = to.z - from.z;
    const len = Math.hypot(dx, dz) || 1;
    const aimed = {
        x: to.x + (-dz / len) * MISS_SIDE_OFFSET_M,
        y: to.y + MISS_UP_OFFSET_M,
        z: to.z + (dx / len) * MISS_SIDE_OFFSET_M,
    };
    return {
        x: from.x + (aimed.x - from.x) * MISS_OVERSHOOT,
        y: from.y + (aimed.y - from.y) * MISS_OVERSHOOT,
        z: from.z + (aimed.z - from.z) * MISS_OVERSHOOT,
    };
}

function lowestFreeSlot(used: Iterable<number>): number {
    const taken = new Set(used);
    let slot = 0;
    while (taken.has(slot)) slot++;
    return slot;
}

function impactText(attack: AttackEvent): Pick<ImpactState, "text" | "caption" | "captionColor"> {
    if (attack.impact === "miss") return { text: "MISS" };
    const text = `-${attack.damage}`;
    if (attack.impact === "critical") return { text, caption: "CRITICAL" };
    if (attack.impact === "combo") return { text, caption: `${attack.comboCount ?? 1}HIT COMBO` };
    if (attack.resistPercent !== undefined) {
        return { text, caption: `RESIST ${attack.resistPercent}%`, captionColor: HIT_EFFECT_COLORS.resist };
    }
    return { text };
}

function impactColor(attack: AttackEvent, playerId: string): string {
    if (attack.impact === "miss") return HIT_EFFECT_COLORS.miss;
    return attack.targetId === playerId ? HIT_EFFECT_COLORS.taken : HIT_EFFECT_COLORS.dealt;
}

function countEffects(effects: AttackEffects): number {
    return effects.tracers.length + effects.labels.length + effects.impacts.length;
}

/** 表示期間を過ぎた演出を取り除く。onComplete が呼ばれなかった演出が残り続けるのを防ぐ。 */
export function pruneExpiredEffects(effects: AttackEffects, now: number): AttackEffects {
    return {
        tracers: effects.tracers.filter((t) => t.startAt + t.durationMs > now),
        labels: effects.labels.filter((l) => l.startAt + EFFECT_TIMING.weaponLabelMs > now),
        impacts: effects.impacts.filter((i) => i.startAt + EFFECT_TIMING.damageNumberMs > now),
    };
}

/**
 * 1 タイムスタンプ分の攻撃から演出をスポーンし、表示中の演出に追加する。
 *
 * 位置が分からないユニット（未索敵など）が絡む攻撃は、射線と武器名を出さない。
 * 被弾側の位置が分かれば、着弾演出だけは出す。
 */
export function spawnAttackEffects(params: {
    active: AttackEffects;
    attacks: AttackEvent[];
    positions: ReadonlyMap<string, Vec3>;
    playerId: string;
    now: number;
    nextId: () => string;
}): AttackEffects {
    const { attacks, positions, playerId, now, nextId } = params;
    const active = pruneExpiredEffects(params.active, now);
    const tracers = [...active.tracers];
    let labels = [...active.labels];
    const impacts = [...active.impacts];
    const impactDelayByPair = new Map<string, number>();

    for (const attack of attacks) {
        const from = positions.get(attack.attackerId);
        const to = positions.get(attack.targetId);
        const pairKey = `${attack.attackerId}>${attack.targetId}`;
        const tracerColor =
            attack.tracerKind === "BEAM" ? HIT_EFFECT_COLORS.tracerBeam : HIT_EFFECT_COLORS.tracerBullet;
        let impactDelay: number;

        if (attack.impact === "combo") {
            // 追撃は直前の格闘 ATTACK と同じ射線上で起きるため、射線と武器名を重ねて出さない
            impactDelay =
                (impactDelayByPair.get(pairKey) ?? EFFECT_TIMING.beamImpactDelayMs) + EFFECT_TIMING.comboExtraDelayMs;
        } else {
            const flightMs =
                from && to && attack.tracerKind === "BULLET" ? bulletFlightMs(from, to) : EFFECT_TIMING.beamImpactDelayMs;
            impactDelay = flightMs;
            impactDelayByPair.set(pairKey, impactDelay);

            if (from && to) {
                tracers.push({
                    id: nextId(),
                    kind: attack.tracerKind,
                    from,
                    to: attack.impact === "miss" ? missTracerEnd(from, to) : to,
                    color: tracerColor,
                    startAt: now,
                    durationMs: attack.tracerKind === "BEAM" ? EFFECT_TIMING.beamTracerMs : flightMs,
                });
            }

            if (from && attack.weaponName) {
                // 同じ武器の連射はラベルを積まず、出し直して表示時間を延ばす
                labels = labels.filter(
                    (l) => !(l.attackerId === attack.attackerId && l.weaponName === attack.weaponName),
                );
                const slot = lowestFreeSlot(
                    labels.filter((l) => l.attackerId === attack.attackerId).map((l) => l.slot),
                );
                labels.push({
                    id: nextId(),
                    attackerId: attack.attackerId,
                    weaponName: attack.weaponName,
                    color: tracerColor,
                    position: from,
                    startAt: now,
                    slot,
                });
            }
        }

        if (!to) continue;
        const startAt = now + impactDelay;
        // 表示期間が重なる同じ被弾側の数字と段を分け、連続ヒットの数字が重ならないようにする
        const slot = lowestFreeSlot(
            impacts
                .filter(
                    (i) =>
                        i.targetId === attack.targetId &&
                        i.startAt < startAt + EFFECT_TIMING.damageNumberMs &&
                        startAt < i.startAt + EFFECT_TIMING.damageNumberMs,
                )
                .map((i) => i.slot),
        );
        impacts.push({
            id: nextId(),
            targetId: attack.targetId,
            kind: attack.impact,
            position: to,
            color: impactColor(attack, playerId),
            ...impactText(attack),
            startAt,
            delayMs: impactDelay,
            slot,
        });
    }

    return {
        tracers: tracers.slice(-MAX_TRACERS),
        labels: labels.slice(-MAX_WEAPON_LABELS),
        impacts: impacts.slice(-MAX_IMPACTS),
    };
}

/**
 * 攻撃演出（射線・武器名・着弾）をタイムスタンプをまたいで保持する。
 * 演出は currentTimestamp が変わった時だけスポーンする。
 */
export function useAttackEffectQueue({
    attacks,
    positions,
    playerId,
    currentTimestamp,
}: {
    attacks: AttackEvent[];
    positions: ReadonlyMap<string, Vec3>;
    playerId: string;
    currentTimestamp: number;
}) {
    const [effects, setEffects] = useState<AttackEffects>(EMPTY_EFFECTS);
    const idCounterRef = useRef(0);

    useEffect(() => {
        const now = Date.now();
        if (attacks.length === 0) {
            // 攻撃が無い時刻でも期限切れの演出は掃除する。何も消えない時は再レンダーしない
            setEffects((prev) => {
                const pruned = pruneExpiredEffects(prev, now);
                return countEffects(pruned) === countEffects(prev) ? prev : pruned;
            });
            return;
        }
        const nextId = () => `fx-${idCounterRef.current++}`;
        setEffects((prev) => spawnAttackEffects({ active: prev, attacks, positions, playerId, now, nextId }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [currentTimestamp]);

    const removeTracer = useCallback((id: string) => {
        setEffects((prev) => ({ ...prev, tracers: prev.tracers.filter((t) => t.id !== id) }));
    }, []);
    const removeLabel = useCallback((id: string) => {
        setEffects((prev) => ({ ...prev, labels: prev.labels.filter((l) => l.id !== id) }));
    }, []);
    const removeImpact = useCallback((id: string) => {
        setEffects((prev) => ({ ...prev, impacts: prev.impacts.filter((i) => i.id !== id) }));
    }, []);

    return { ...effects, removeTracer, removeLabel, removeImpact };
}
