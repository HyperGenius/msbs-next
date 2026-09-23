/* frontend/src/components/BattleViewer/ui/HpBar.tsx */

"use client";

import { useState } from "react";

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
    // シークで時刻を戻すと HP が増える。そのときはチップを出さず、すぐに幅を合わせる
    const [prevCurrent, setPrevCurrent] = useState(current);
    const [increased, setIncreased] = useState(false);
    if (current !== prevCurrent) {
        setIncreased(current > prevCurrent);
        setPrevCurrent(current);
    }

    const ratio = max > 0 ? Math.max(0, Math.min(1, current / max)) : 0;
    const width = `${ratio * 100}%`;

    return (
        <div className="w-24 h-2 bg-gray-700 mt-1 rounded overflow-hidden border border-gray-600 relative">
            <div
                className="absolute inset-y-0 left-0 bg-gray-100"
                style={{ width, transition: increased ? "none" : CHIP_TRANSITION }}
            />
            <div
                className="absolute inset-y-0 left-0"
                style={{ width, backgroundColor: colorFunc(ratio), transition: increased ? "none" : BAR_TRANSITION }}
            />
        </div>
    );
}
