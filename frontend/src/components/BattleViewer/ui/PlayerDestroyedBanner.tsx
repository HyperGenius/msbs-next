/* frontend/src/components/BattleViewer/ui/PlayerDestroyedBanner.tsx */

/** 自機が撃破されたことを示すバナー。ビューアの中央に重ねて表示する。 */
export function PlayerDestroyedBanner() {
    return (
        <div
            role="alert"
            className="absolute inset-0 flex items-center justify-center pointer-events-none animate-fade-in"
        >
            <div className="bg-black/70 border border-red-600 rounded px-6 py-3 text-center font-mono">
                <div className="text-red-500 text-lg sm:text-2xl font-bold tracking-widest">自機が撃破されました</div>
                <div className="text-red-400/70 text-[10px] sm:text-xs mt-1">MS DESTROYED</div>
            </div>
        </div>
    );
}
