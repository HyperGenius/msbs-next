/* frontend/src/components/BattleViewer/ui/ComboEffect.tsx */

"use client";

import { useEffect, useState } from "react";
import { BattleLog } from "@/types/battle";

interface ComboEffectProps {
    logs: BattleLog[];
    currentTimestamp: number;
}

interface ComboState {
    combo_count: number;
    combo_message: string;
    visible: boolean;
}

/** コンボ数に応じた色を返す */
function getComboColor(comboCount: number): string {
    if (comboCount >= 3) return "#ff2200"; // 赤 (3連コンボ)
    if (comboCount === 2) return "#ff7700"; // オレンジ (2連コンボ)
    return "#ffdd00"; // 黄 (1連コンボ)
}

/**
 * BattleViewer に重ねて格闘コンボエフェクトを表示するコンポーネント (Phase C)
 *
 * `MELEE_COMBO` ログを検出し、combo_message をアニメーション表示する。
 * コンボ数に応じてエフェクト色・サイズが変化する（1連: 黄、2連: オレンジ、3連: 赤）。
 */
export function ComboEffect({ logs, currentTimestamp }: ComboEffectProps) {
    const [comboState, setComboState] = useState<ComboState | null>(null);

    useEffect(() => {
        // 現在タイムスタンプの MELEE_COMBO ログを検出
        const comboLog = logs.find(
            (log) =>
                log.action_type === "MELEE_COMBO" &&
                Math.abs(log.timestamp - currentTimestamp) < 1e-9 &&
                log.combo_message
        );

        if (!comboLog || !comboLog.combo_message || !comboLog.combo_count) return;

        setComboState({
            combo_count: comboLog.combo_count,
            combo_message: comboLog.combo_message,
            visible: true,
        });

        // 一定時間後にフェードアウト
        const timer = setTimeout(() => {
            setComboState((prev) => (prev ? { ...prev, visible: false } : null));
        }, 1800);

        return () => clearTimeout(timer);
    }, [logs, currentTimestamp]);

    if (!comboState) return null;

    const color = getComboColor(comboState.combo_count);
    const fontSize =
        comboState.combo_count >= 3 ? "text-4xl" : comboState.combo_count === 2 ? "text-3xl" : "text-2xl";

    return (
        <div
            className={`absolute inset-0 flex items-center justify-center pointer-events-none z-10 transition-opacity duration-500 ${
                comboState.visible ? "opacity-100" : "opacity-0"
            }`}
        >
            <div className="flex flex-col items-center gap-1 animate-bounce">
                {/* コンボカウンター */}
                <div
                    className={`font-black tracking-widest ${fontSize}`}
                    style={{
                        color,
                        textShadow: `0 0 20px ${color}, 0 0 40px ${color}, 0 0 60px ${color}`,
                        WebkitTextStroke: "1px rgba(0,0,0,0.5)",
                    }}
                >
                    ×{comboState.combo_count}
                </div>
                {/* コンボメッセージ */}
                <div
                    className="font-bold text-lg tracking-wide"
                    style={{
                        color,
                        textShadow: `0 0 10px ${color}, 0 0 20px ${color}`,
                    }}
                >
                    {comboState.combo_message}
                </div>
            </div>
        </div>
    );
}
