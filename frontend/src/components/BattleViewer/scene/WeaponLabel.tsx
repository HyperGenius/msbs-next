/* frontend/src/components/BattleViewer/scene/WeaponLabel.tsx */

"use client";

import { Html } from "@react-three/drei";
import { EFFECT_TIMING, WeaponLabelState } from "../hooks/useAttackEffectQueue";

const POSITION_SCALE = 0.05;
/** 同じ発射側で複数の武器ラベルを出すときの 1 段の高さ（px）。 */
const LABEL_SLOT_HEIGHT_PX = 24;

/** 発射側の少し上に `▶ 武器名` を出し、フェードで消す。 */
export function WeaponLabel({ label, onComplete }: { label: WeaponLabelState; onComplete: () => void }) {
    const { position, slot, color, weaponName } = label;

    return (
        <Html
            position={[position.x * POSITION_SCALE, position.y * POSITION_SCALE + 5, position.z * POSITION_SCALE]}
            center
        >
            <div
                className="pointer-events-none select-none whitespace-nowrap font-mono text-xs text-gray-100"
                style={{
                    transform: `translateY(${-slot * LABEL_SLOT_HEIGHT_PX}px)`,
                    background: "rgba(0, 0, 0, 0.72)",
                    borderLeft: `2px solid ${color}`,
                    padding: "2px 7px 2px 6px",
                    animation: `bv-weapon-label ${EFFECT_TIMING.weaponLabelMs}ms linear both`,
                }}
                onAnimationEnd={onComplete}
            >
                ▶ {weaponName}
            </div>
        </Html>
    );
}
