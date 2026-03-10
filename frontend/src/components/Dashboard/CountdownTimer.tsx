"use client";

import { useState, useEffect } from "react";

interface CountdownTimerProps {
  targetTime: Date | null;
}

export default function CountdownTimer({ targetTime }: CountdownTimerProps) {
  const [timeLeft, setTimeLeft] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (!targetTime) {
      setTimeLeft("--:--:--");
      return;
    }

    const updateCountdown = () => {
      const now = new Date();
      const diff = targetTime.getTime() - now.getTime();

      // 時間になった場合
      if (diff <= 0) {
        setIsProcessing(true);
        setTimeLeft("00:00:00");
        return;
      }

      // 時間、分、秒を計算
      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      setTimeLeft(
        `${hours.toString().padStart(2, "0")}:${minutes
          .toString()
          .padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`
      );
      setIsProcessing(false);
    };

    // 初回実行
    updateCountdown();

    // 1秒ごとに更新
    const interval = setInterval(updateCountdown, 1000);

    return () => clearInterval(interval);
  }, [targetTime]);

  const formattedStartTime = targetTime
    ? new Intl.DateTimeFormat("ja-JP", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).format(targetTime)
    : null;

  if (isProcessing) {
    return (
      <div className="bg-[#0a0a0a] border-2 border-[#ffb000]/50 p-4 sm:p-6 text-center">
        <div className="text-[#ffb000]/60 text-xs font-bold mb-2 tracking-widest">
          STATUS
        </div>
        <div className="text-3xl sm:text-4xl font-bold text-[#ffb000] animate-pulse font-mono">
          集計中...
        </div>
        <div className="text-xs text-[#ffb000]/40 mt-2">
          バトル処理を実行しています
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#0a0a0a] border-2 border-[#00ff41]/30 p-4 sm:p-6 text-center">
      <div className="text-[#00ff41]/50 text-xs font-bold mb-2 tracking-widest">
        NEXT BATTLE IN
      </div>
      <div className="text-4xl sm:text-5xl md:text-6xl font-bold text-[#00ff41] font-mono tracking-wider">
        {timeLeft}
      </div>
      {formattedStartTime && (
        <div className="text-xs text-[#00ff41]/50 mt-2 font-mono">
          START: {formattedStartTime}
        </div>
      )}
      {!formattedStartTime && (
        <div className="text-xs text-[#00ff41]/30 mt-2">
          毎日 JST 21:00 / UTC 12:00
        </div>
      )}
    </div>
  );
}
