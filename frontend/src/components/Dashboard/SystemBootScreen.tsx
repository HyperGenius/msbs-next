/* frontend/src/components/Dashboard/SystemBootScreen.tsx */
"use client";

import { useEffect, useState } from "react";
import { SciFiHeading } from "@/components/ui";

const BOOT_SEQUENCE = [
  "INITIALIZING MOBILE SUIT BATTLE SYSTEM...",
  "LOADING PILOT DATABASE...",
  "SYNCHRONIZING BATTLE RECORDS...",
  "ESTABLISHING SECURE CHANNEL...",
  "CALIBRATING COMBAT PARAMETERS...",
  "SYSTEM READY.",
];

export default function SystemBootScreen() {
  const [visibleLines, setVisibleLines] = useState<number>(0);

  useEffect(() => {
    if (visibleLines >= BOOT_SEQUENCE.length) return;

    const timer = setTimeout(() => {
      setVisibleLines((prev) => prev + 1);
    }, 350);

    return () => clearTimeout(timer);
  }, [visibleLines]);

  const progress = Math.round((visibleLines / (BOOT_SEQUENCE.length || 1)) * 100);

  return (
    <main
      aria-label="システム起動中"
      className="min-h-screen bg-[#050505] text-[#00ff41] p-4 sm:p-6 md:p-8 font-mono flex flex-col items-center justify-center"
    >
      <div className="w-full max-w-2xl space-y-8">
        <SciFiHeading level={1} variant="primary" className="text-center">
          SYSTEM BOOTING
        </SciFiHeading>

        {/* ターミナル風ログ */}
        <div className="bg-[#0a0a0a] border border-[#00ff41]/30 p-4 sm:p-6 space-y-2 min-h-[200px]">
          {BOOT_SEQUENCE.slice(0, visibleLines).map((line, i) => (
            <div key={i} className="flex items-start gap-2 text-sm">
              <span className="text-[#00ff41]/50 select-none">{">"}</span>
              <span
                className={
                  i === visibleLines - 1
                    ? "text-[#00ff41] animate-pulse"
                    : "text-[#00ff41]/70"
                }
              >
                {line}
              </span>
            </div>
          ))}
          {/* カーソル点滅 */}
          {visibleLines < BOOT_SEQUENCE.length && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-[#00ff41]/50 select-none">{">"}</span>
              <span className="inline-block w-2 h-4 bg-[#00ff41] animate-pulse" />
            </div>
          )}
        </div>

        {/* プログレスバー */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-[#00ff41]/50 tracking-widest">
            <span>LOADING</span>
            <span>{progress}%</span>
          </div>
          <div
            className="relative h-2 bg-[#0a0a0a] border border-[#00ff41]/30 overflow-hidden"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full bg-[#00ff41] transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>
    </main>
  );
}
