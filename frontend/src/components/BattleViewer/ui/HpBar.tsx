/* frontend/src/components/BattleViewer/ui/HpBar.tsx */

"use client";

import { useLayoutEffect, useRef } from "react";

// チップ（減った分の白い帯）は本体より遅れて縮む。
// 本体と同じ幅を遅延付きトランジションで追うため、HP が下がった時だけ本体との差が白く見える。
// 連続ヒット中は幅が変わるたびに遅延がやり直されるため、コンボの合計分が残ってから縮む。
const BAR_TRANSITION = "width 150ms ease-out";
const CHIP_TRANSITION = "width 500ms ease-in 400ms";

/** HP バー。被弾時は減った分を一瞬白く残してから削る。 */
export function HpBar({
    current,
    max,
    colorFunc,
}: {
    current: number;
    max: number;
    colorFunc: (ratio: number) => string;
}) {
    const barRef = useRef<HTMLDivElement>(null);
    const chipRef = useRef<HTMLDivElement>(null);
    const prevCurrentRef = useRef(current);

    // シークで時刻を戻すと HP が増える。そのときはチップを出さず、すぐに幅を合わせる。
    // transition は幅の変更と同じコミット内（描画前）に書き換える。
    // ブラウザは変更後の transition で幅のトランジションを判定するため、増加時はアニメーションしない。
    useLayoutEffect(() => {
        const increased = current > prevCurrentRef.current;
        prevCurrentRef.current = current;
        if (barRef.current) barRef.current.style.transition = increased ? "none" : BAR_TRANSITION;
        if (chipRef.current) chipRef.current.style.transition = increased ? "none" : CHIP_TRANSITION;
    }, [current]);

    const ratio = max > 0 ? Math.max(0, Math.min(1, current / max)) : 0;
    const width = `${ratio * 100}%`;

    return (
        <div className="w-24 h-2 bg-gray-700 mt-1 rounded overflow-hidden border border-gray-600 relative">
            <div ref={chipRef} className="absolute inset-y-0 left-0 bg-gray-100" style={{ width }} />
            <div
                ref={barRef}
                className="absolute inset-y-0 left-0"
                style={{ width, backgroundColor: colorFunc(ratio) }}
            />
        </div>
    );
}
