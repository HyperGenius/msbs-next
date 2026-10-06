/* frontend/src/components/BattleViewer/scene/ImpactMarker.tsx */

"use client";

import type { AnimationEvent, CSSProperties } from "react";
import { Html } from "@react-three/drei";
import { EFFECT_TIMING, ImpactState } from "../hooks/useAttackEffectQueue";
import { HIT_EFFECT_COLORS } from "../utils";

const POSITION_SCALE = 0.05;

// 数字は被弾側の中心から右上にずらして出す。連続ヒットは 1 段ずつ上に積む。
const NUMBER_OFFSET_X_PX = 22;
const NUMBER_OFFSET_Y_PX = 18;
const NUMBER_SLOT_HEIGHT_PX = 24;

// 緑のグリッドに数字の輪郭が埋もれないよう、黒で縁取る
const TEXT_OUTLINE =
    "-1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000, 0 0 3px #000";

const FLASH = {
    normal: { durationMs: 160, ringSizePx: 44, ringWidthPx: 2, coreSizePx: 10 },
    critical: { durationMs: 240, ringSizePx: 68, ringWidthPx: 3, coreSizePx: 16 },
} as const;

// 鍔迫り合いの火花の本数と長さ。角度は等間隔から少しずつずらし、放射が整いすぎないようにする。
const CLASH_SPARK_COUNT = 10;
const CLASH_SPARK_LENGTH_PX = 18;
const CLASH_SPARK_MS = 420;
// 武器名ラベルは機体の上に出るため、文字は火花の下に置いて重ならないようにする。
const CLASH_TEXT_OFFSET_Y_PX = 18;

function toScenePosition(position: ImpactState["position"]): [number, number, number] {
    return [position.x * POSITION_SCALE, position.y * POSITION_SCALE, position.z * POSITION_SCALE];
}

/** 鍔迫り合いの火花と「鍔迫り合い！」の文字。両機の中間に出す。 */
function ClashMarker({ impact, onComplete }: { impact: ImpactState; onComplete: () => void }) {
    const handleAnimationEnd = (e: AnimationEvent<HTMLDivElement>) => {
        if (e.animationName === "bv-clash-text") onComplete();
    };

    return (
        <Html position={toScenePosition(impact.position)} center>
            <div className="pointer-events-none select-none relative w-0 h-0">
                <div
                    className="absolute left-0 top-0 rounded-full"
                    style={{
                        "--bv-ring-size": `${FLASH.critical.ringSizePx}px`,
                        border: `${FLASH.critical.ringWidthPx}px solid ${HIT_EFFECT_COLORS.flashRing}`,
                        transform: "translate(-50%, -50%)",
                        animation: `bv-flash-ring ${FLASH.critical.durationMs}ms ease-out both`,
                    } as CSSProperties}
                />
                {Array.from({ length: CLASH_SPARK_COUNT }, (_, i) => (
                    <div
                        key={i}
                        className="absolute left-0 top-0 rounded-full"
                        style={{
                            "--bv-spark-angle": `${(360 / CLASH_SPARK_COUNT) * i + (i % 3) * 11}deg`,
                            width: CLASH_SPARK_LENGTH_PX,
                            height: 2,
                            marginTop: -1,
                            background: HIT_EFFECT_COLORS.flashCore,
                            boxShadow: `0 0 4px ${HIT_EFFECT_COLORS.flashRing}`,
                            transformOrigin: "0 50%",
                            animation: `bv-clash-spark ${CLASH_SPARK_MS}ms ease-out both`,
                        } as CSSProperties}
                    />
                ))}
                <div
                    className="absolute left-0 whitespace-nowrap font-bold leading-none"
                    style={{
                        top: CLASH_TEXT_OFFSET_Y_PX,
                        color: impact.color,
                        textShadow: TEXT_OUTLINE,
                        fontSize: 20,
                        animation: `bv-clash-text ${EFFECT_TIMING.clashTextMs}ms ease-out both`,
                    }}
                    onAnimationEnd={handleAnimationEnd}
                >
                    {impact.text}
                </div>
            </div>
        </Html>
    );
}

/** 着弾地点のフラッシュと、右上に上昇してフェードするダメージ数字。鍔迫り合いは火花と文字にする。 */
export function ImpactMarker({ impact, onComplete }: { impact: ImpactState; onComplete: () => void }) {
    if (impact.kind === "clash") return <ClashMarker impact={impact} onComplete={onComplete} />;
    return <DamageMarker impact={impact} onComplete={onComplete} />;
}

function DamageMarker({ impact, onComplete }: { impact: ImpactState; onComplete: () => void }) {
    const { position, kind, text, color, caption, captionColor, delayMs, slot } = impact;
    const isBig = kind === "critical" || kind === "combo";
    const flash = kind === "critical" ? FLASH.critical : FLASH.normal;
    const numberMs = EFFECT_TIMING.damageNumberMs;

    // 数字には上昇とフェードの 2 つのアニメーションがあるため、フェードの終了だけで取り除く
    const handleAnimationEnd = (e: AnimationEvent<HTMLDivElement>) => {
        if (e.animationName === "bv-number-fade") onComplete();
    };

    return (
        <Html position={toScenePosition(position)} center>
            <div className="pointer-events-none select-none relative w-0 h-0">
                {kind !== "miss" && (
                    <>
                        <div
                            className="absolute left-0 top-0 rounded-full"
                            style={{
                                "--bv-ring-size": `${flash.ringSizePx}px`,
                                border: `${flash.ringWidthPx}px solid ${HIT_EFFECT_COLORS.flashRing}`,
                                transform: "translate(-50%, -50%)",
                                animation: `bv-flash-ring ${flash.durationMs}ms ease-out ${delayMs}ms both`,
                            } as CSSProperties}
                        />
                        <div
                            className="absolute left-0 top-0 rounded-full"
                            style={{
                                width: flash.coreSizePx,
                                height: flash.coreSizePx,
                                background: HIT_EFFECT_COLORS.flashCore,
                                animation: `bv-flash-core ${flash.durationMs}ms ease-out ${delayMs}ms both`,
                            }}
                        />
                    </>
                )}
                <div
                    className="absolute whitespace-nowrap font-mono font-bold tabular-nums leading-none"
                    style={{
                        left: NUMBER_OFFSET_X_PX,
                        bottom: NUMBER_OFFSET_Y_PX + slot * NUMBER_SLOT_HEIGHT_PX,
                        color,
                        textShadow: TEXT_OUTLINE,
                        fontSize: isBig ? 22 : 16,
                        animation: [
                            `bv-number-rise ${numberMs}ms cubic-bezier(0.33, 1, 0.68, 1) ${delayMs}ms both`,
                            `bv-number-fade ${numberMs}ms linear ${delayMs}ms both`,
                        ].join(", "),
                    }}
                    onAnimationEnd={handleAnimationEnd}
                >
                    {text}
                    {caption && (
                        <span className="ml-1 text-[10px]" style={{ color: captionColor ?? color }}>
                            {caption}
                        </span>
                    )}
                </div>
            </div>
        </Html>
    );
}
