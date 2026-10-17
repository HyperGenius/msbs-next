/* frontend/src/components/BattleViewer/ui/PlayerDestroyedBanner.tsx */
"use client";

import { useEffect, useState } from "react";
import { EXPLOSION_DURATION_MS } from "../scene/DestroyedExplosion";

/** 「撃破されました」を見せてから「戦闘終了」へ切り替えるまでの時間（ミリ秒）。 */
const DESTROYED_MESSAGE_MS = 2000;

export interface PlayerDestroyedRewards {
    exp: number;
    credits: number;
}

interface PlayerDestroyedBannerProps {
    rewards?: PlayerDestroyedRewards | null;
}

/**
 * 自機の撃破を知らせるウィンドウ。ビューアの中央に重ねて表示する。
 * 爆発が終わる頃にウィンドウを開いて「撃破されました」を出し、一定時間で「戦闘終了」と獲得量に切り替える。
 * 巻き戻しなどで表示が外れると、次に出すときは最初から始まる。
 */
export function PlayerDestroyedBanner({ rewards }: PlayerDestroyedBannerProps) {
    const [isFinished, setIsFinished] = useState(false);

    useEffect(() => {
        const timer = setTimeout(() => setIsFinished(true), EXPLOSION_DURATION_MS + DESTROYED_MESSAGE_MS);
        return () => clearTimeout(timer);
    }, []);

    return (
        <div role="alert" className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div
                className="bg-black/80 border border-red-600 rounded px-8 py-4 text-center font-mono shadow-[0_0_24px_rgba(220,38,38,0.4)] min-w-[220px]"
                style={{ animation: `bv-window-open 0.35s ease-out ${EXPLOSION_DURATION_MS}ms both` }}
            >
                {/* key を変えて、切り替わるたびにフェードインさせる */}
                <div key={isFinished ? "finished" : "destroyed"} className="animate-fade-in">
                    {isFinished ? (
                        <>
                            <div className="text-amber-400 text-lg sm:text-2xl font-bold tracking-widest">戦闘終了</div>
                            {rewards && (
                                <dl className="mt-3 text-xs sm:text-sm text-gray-200 grid grid-cols-[auto_auto] gap-x-4 gap-y-1 justify-center text-left">
                                    <dt className="text-gray-400">獲得EXP</dt>
                                    <dd className="text-right tabular-nums">{rewards.exp.toLocaleString()}</dd>
                                    <dt className="text-gray-400">獲得クレジット</dt>
                                    <dd className="text-right tabular-nums">{rewards.credits.toLocaleString()} C</dd>
                                </dl>
                            )}
                        </>
                    ) : (
                        <div className="text-red-500 text-lg sm:text-2xl font-bold tracking-widest">撃破されました</div>
                    )}
                </div>
            </div>
        </div>
    );
}
