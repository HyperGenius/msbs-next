/* frontend/src/components/history/TurnController.tsx */
"use client";

import { useState, useEffect, useRef } from "react";

interface TurnControllerProps {
  currentTimestamp: number;
  maxTimestamp: number;
  onTimestampChange: (timestamp: number) => void;
}

export default function TurnController({ currentTimestamp, maxTimestamp, onTimestampChange }: TurnControllerProps) {
  const step = 0.1;
  const [isPlaying, setIsPlaying] = useState(false);
  const currentTimestampRef = useRef(currentTimestamp);
  const onTimestampChangeRef = useRef(onTimestampChange);

  useEffect(() => {
    currentTimestampRef.current = currentTimestamp;
  }, [currentTimestamp]);

  useEffect(() => {
    onTimestampChangeRef.current = onTimestampChange;
  }, [onTimestampChange]);

  useEffect(() => {
    if (!isPlaying) return;

    // requestAnimationFrame + 経過時間ベースで駆動する。setInterval(固定100ms)は
    // 処理落ちがあっても遅延を自動補正しないため、負荷が高い環境では再生が実時間から
    // 乖離し続けていた（Issue #467）。rAFのタイムスタンプ差分から経過秒数を積算することで、
    // 1フレームが遅れても次フレームでまとめて追いつける。
    let rafId: number;
    let lastFrameTime: number | null = null;
    let elapsedSinceLastStep = 0;

    const tick = (frameTime: number) => {
      if (lastFrameTime === null) {
        lastFrameTime = frameTime;
        rafId = requestAnimationFrame(tick);
        return;
      }

      elapsedSinceLastStep += (frameTime - lastFrameTime) / 1000;
      lastFrameTime = frameTime;

      // stepごとの再生ステップに相当する経過時間が溜まったら、その分だけまとめて進める
      // （閾値を step 自体から算出することで、step を変更した場合も再生クロックと整合する）
      if (elapsedSinceLastStep >= step) {
        const stepsToAdvance = Math.floor(elapsedSinceLastStep / step);
        elapsedSinceLastStep -= stepsToAdvance * step;

        const next = Math.round((currentTimestampRef.current + step * stepsToAdvance) * 10) / 10;
        if (next >= maxTimestamp) {
          onTimestampChangeRef.current(maxTimestamp);
          setIsPlaying(false);
          return;
        }
        onTimestampChangeRef.current(next);
      }

      rafId = requestAnimationFrame(tick);
    };

    rafId = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(rafId);
  }, [isPlaying, maxTimestamp]);

  const handlePlayPause = () => {
    if (currentTimestamp >= maxTimestamp) {
      onTimestampChange(0);
    }
    setIsPlaying((prev) => !prev);
  };

  const handleStop = () => {
    setIsPlaying(false);
    onTimestampChange(0);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    setIsPlaying(false);
    onTimestampChange(Math.round(Number(e.target.value) * 10) / 10);
  };

  return (
    <div className="mt-2 p-3 bg-gray-900 border border-green-800 rounded">
      <div className="flex items-center gap-3">
        <button
          onClick={handleStop}
          aria-label="停止"
          className="px-3 py-1 bg-green-900 hover:bg-green-800 rounded text-sm font-bold transition-colors"
        >
          ⏹
        </button>
        <button
          onClick={handlePlayPause}
          aria-label={isPlaying ? "一時停止" : "再生"}
          className="px-3 py-1 bg-green-900 hover:bg-green-800 rounded text-sm font-bold transition-colors"
        >
          {isPlaying ? "⏸" : "▶"}
        </button>
        <div className="flex-grow flex flex-col">
          <input
            type="range"
            min="0"
            max={maxTimestamp}
            step={step}
            value={currentTimestamp}
            onChange={handleSeek}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-green-500"
          />
          <div className="flex justify-between text-xs mt-1 text-green-600/60">
            <span>Start</span>
            <span>Time: {currentTimestamp.toFixed(1)}s / {maxTimestamp.toFixed(1)}s</span>
            <span>End</span>
          </div>
        </div>
      </div>
    </div>
  );
}
