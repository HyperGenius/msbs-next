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

  if (isProcessing) {
    return (
      <div className="bg-yellow-900/30 border-2 border-yellow-500 rounded-lg p-6 text-center">
        <div className="text-yellow-400 text-sm font-bold mb-2 tracking-widest">
          STATUS
        </div>
        <div className="text-4xl font-bold text-yellow-300 animate-pulse">
          集計中...
        </div>
        <div className="text-xs text-yellow-500 mt-2">
          バトル処理を実行しています
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-r from-green-900/20 to-blue-900/20 border-2 border-green-500 rounded-lg p-6 text-center">
      <div className="text-green-400 text-sm font-bold mb-2 tracking-widest">
        NEXT BATTLE IN
      </div>
      <div className="text-5xl md:text-6xl font-bold text-green-300 font-mono tracking-wider">
        {timeLeft}
      </div>
      <div className="text-xs text-gray-400 mt-2">
        毎日 JST 21:00 / UTC 12:00
      </div>
    </div>
  );
}
