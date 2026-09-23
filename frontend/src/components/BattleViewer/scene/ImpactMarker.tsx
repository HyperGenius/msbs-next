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

/** 着弾地点のフラッシュと、右上に上昇してフェードするダメージ数字。 */
export function ImpactMarker({ impact, onComplete }: { impact: ImpactState; onComplete: () => void }) {
    const { position, kind, text, color, caption, captionColor, delayMs, slot } = impact;
    const isBig = kind === "critical" || kind === "combo";
    const flash = kind === "critical" ? FLASH.critical : FLASH.normal;
    const numberMs = EFFECT_TIMING.damageNumberMs;

    // 数字には上昇とフェードの 2 つのアニメーションがあるため、フェードの終了だけで取り除く
    const handleAnimationEnd = (e: AnimationEvent<HTMLDivElement>) => {
        if (e.animationName === "bv-number-fade") onComplete();
    };

    return (
        <Html position={[position.x * POSITION_SCALE, position.y * POSITION_SCALE, position.z * POSITION_SCALE]} center>
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
