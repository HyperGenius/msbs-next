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

    const interval = setInterval(() => {
      const next = Math.round((currentTimestampRef.current + step) * 10) / 10;
      if (next >= maxTimestamp) {
        onTimestampChangeRef.current(maxTimestamp);
        setIsPlaying(false);
      } else {
        onTimestampChangeRef.current(next);
      }
    }, 100);

    return () => clearInterval(interval);
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
