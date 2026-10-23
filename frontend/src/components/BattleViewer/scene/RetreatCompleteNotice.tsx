/* frontend/src/components/BattleViewer/scene/RetreatCompleteNotice.tsx */

"use client";

import { Html } from "@react-three/drei";
import { HIT_EFFECT_COLORS } from "../utils";
import { RETREAT_NOTICE_SECONDS, RetreatNotice } from "../utils/retreat";

const POSITION_SCALE = 0.05;

/**
 * 友軍が撤退ポイントに着いて離脱したことを、その場に「離脱」の文字で出す。
 * 経過時間に応じて薄くしながら浮かせる。経過はログの時刻から求めるので、再生位置を戻しても同じ見え方になる。
 */
export function RetreatCompleteNotice({
    notice,
    currentTimestamp,
}: {
    notice: RetreatNotice;
    currentTimestamp: number;
}) {
    const age = Math.max(0, currentTimestamp - notice.timestamp);
    const ratio = Math.min(1, age / RETREAT_NOTICE_SECONDS);
    return (
        <Html
            position={[notice.pos.x * POSITION_SCALE, notice.pos.y * POSITION_SCALE, notice.pos.z * POSITION_SCALE]}
            center
        >
            <div
                className="pointer-events-none select-none whitespace-nowrap font-bold text-sm"
                style={{
                    color: HIT_EFFECT_COLORS.tracerBeam,
                    opacity: 1 - ratio,
                    transform: `translateY(${-ratio * 24 - 12}px)`,
                    textShadow: "-1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000, 0 0 3px #000",
                }}
            >
                ↩ 離脱
            </div>
        </Html>
    );
}
