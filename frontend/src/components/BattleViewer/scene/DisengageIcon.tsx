/* frontend/src/components/BattleViewer/scene/DisengageIcon.tsx */

"use client";

import { useState } from "react";
import { Html } from "@react-three/drei";
import { EFFECT_TIMING } from "../hooks/useAttackEffectQueue";
import { HIT_EFFECT_COLORS } from "../utils";

const POSITION_SCALE = 0.05;

// 機体の球のすぐ右上に出す。被弾時のダメージ数字と重ならないよう、数字より機体寄りに置く。
const ICON_OFFSET_X_PX = 12;
const ICON_OFFSET_Y_PX = 8;

const TEXT_OUTLINE =
    "-1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000, 0 0 3px #000";

/**
 * 自機の仕切り直しを、自機の右上に `↩` で一瞬だけ出す。
 * `triggeredAt` が新しい時刻に変わるたびに出し直す。寿命は実時間で数える。
 */
export function DisengageIcon({
    position,
    triggeredAt,
}: {
    position: { x: number; y: number; z: number };
    /** 自機が仕切り直した時刻。現在時刻に DISENGAGE が無いときは null。 */
    triggeredAt: number | null;
}) {
    const [lastTriggeredAt, setLastTriggeredAt] = useState(triggeredAt);
    const [shownAt, setShownAt] = useState(triggeredAt);
    // triggeredAt は次のコマで null に戻る。アイコンは寿命が尽きるまで shownAt で出し続ける。
    if (triggeredAt !== lastTriggeredAt) {
        setLastTriggeredAt(triggeredAt);
        if (triggeredAt !== null) setShownAt(triggeredAt);
    }
    if (shownAt === null) return null;

    return (
        <Html
            position={[position.x * POSITION_SCALE, position.y * POSITION_SCALE, position.z * POSITION_SCALE]}
            center
        >
            <div className="pointer-events-none select-none relative w-0 h-0">
                <div
                    key={shownAt}
                    className="absolute font-bold leading-none"
                    style={{
                        left: ICON_OFFSET_X_PX,
                        bottom: ICON_OFFSET_Y_PX,
                        color: HIT_EFFECT_COLORS.tracerBeam,
                        textShadow: TEXT_OUTLINE,
                        fontSize: 18,
                        animation: `bv-disengage-icon ${EFFECT_TIMING.disengageIconMs}ms linear both`,
                    }}
                    onAnimationEnd={() => setShownAt(null)}
                >
                    ↩
                </div>
            </div>
        </Html>
    );
}
