/* frontend/src/components/BattleViewer/ui/PlayerDestroyedBanner.tsx */
"use client";

import { useEffect, useState } from "react";

/** 「撃破されました」を見せてから「撤退します」へ切り替えるまでの時間（ミリ秒）。 */
const DESTROYED_MESSAGE_MS = 2000;

/**
 * 自機の撃破を知らせるウィンドウ。ビューアの中央に重ねて表示する。
 * 開くアニメーションの後に「撃破されました」を出し、一定時間で「撤退します」に切り替える。
 * 巻き戻しなどで表示が外れると、次に出すときは最初から始まる。
 */
export function PlayerDestroyedBanner() {
    const [isRetreating, setIsRetreating] = useState(false);

    useEffect(() => {
        const timer = setTimeout(() => setIsRetreating(true), DESTROYED_MESSAGE_MS);
        return () => clearTimeout(timer);
    }, []);

    return (
        <div role="alert" className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div
                className="bg-black/80 border border-red-600 rounded px-8 py-4 text-center font-mono shadow-[0_0_24px_rgba(220,38,38,0.4)]"
                style={{ animation: "bv-window-open 0.35s ease-out both" }}
            >
                {/* key を変えて、切り替わるたびにフェードインさせる */}
                <div
                    key={isRetreating ? "retreat" : "destroyed"}
                    className="animate-fade-in text-lg sm:text-2xl font-bold tracking-widest"
                >
                    {isRetreating ? (
                        <span className="text-amber-400">撤退します</span>
                    ) : (
                        <span className="text-red-500">撃破されました</span>
                    )}
                </div>
            </div>
        </div>
    );
}
