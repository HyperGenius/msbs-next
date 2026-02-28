"use client";

import { useRef, useState, useCallback, useEffect } from "react";

const HOLD_DURATION_MS = 1500;
const TICK_MS = 16; // ~60fps

interface HoldSciFiButtonProps {
  /** 長押し完了時に呼ばれるコールバック */
  onHoldComplete: () => void;
  /** ボタンが無効かどうか */
  disabled?: boolean;
  /** 処理中（確定後のローディング）かどうか */
  loading?: boolean;
  /** ボタン内に表示するラベル（デフォルト: "長押しで確定"） */
  label?: string;
  /** 処理中に表示するラベル（デフォルト: "処理中..."） */
  loadingLabel?: string;
  className?: string;
}

/**
 * 長押し確定ボタン。
 *
 * ボタンを押し続けると内部のプログレスゲージが 0→100% まで溜まり、
 * 満タンになった時点で `onHoldComplete` を呼び出す。
 * 途中で離すとゲージがリセットされる。
 */
export default function HoldSciFiButton({
  onHoldComplete,
  disabled = false,
  loading = false,
  label = "長押しで確定",
  loadingLabel = "処理中...",
  className = "",
}: HoldSciFiButtonProps) {
  const [progress, setProgress] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const firedRef = useRef(false);

  const startHold = useCallback(() => {
    if (disabled || loading) return;
    firedRef.current = false;

    intervalRef.current = setInterval(() => {
      setProgress((prev) => {
        const next = prev + (TICK_MS / HOLD_DURATION_MS) * 100;
        if (next >= 100) {
          // 満タン → インターバルを止めて発火
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          if (!firedRef.current) {
            firedRef.current = true;
            onHoldComplete();
          }
          return 100;
        }
        return next;
      });
    }, TICK_MS);
  }, [disabled, loading, onHoldComplete]);

  const cancelHold = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    // 発火済みの場合はリセットしない（ローディング中の見た目を保つ）
    if (!firedRef.current) {
      setProgress(0);
    }
  }, []);

  // loading が終わったらゲージをリセット
  useEffect(() => {
    if (!loading) {
      setProgress(0);
      firedRef.current = false;
    }
  }, [loading]);

  // アンマウント時のクリーンアップ
  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const isActive = !disabled && !loading;
  const isFull = progress >= 100;

  // ゲージの色
  const fillColor = isFull
    ? "bg-[#00f0ff]"
    : progress > 50
    ? "bg-[#00ff41]"
    : "bg-[#00ff41]/70";

  // ボーダー・テキスト色
  const borderColor = loading
    ? "border-gray-600"
    : isFull
    ? "border-[#00f0ff]"
    : "border-[#00ff41]";
  const textColor = loading || disabled ? "text-gray-500" : "text-black";

  return (
    <button
      className={`
        relative overflow-hidden
        w-full
        px-3 py-2
        font-bold font-mono text-sm
        border-2 ${borderColor}
        touch-manipulation
        select-none
        transition-colors duration-150
        ${disabled || loading ? "cursor-not-allowed opacity-60 bg-gray-700" : "cursor-pointer bg-[#050505]"}
        ${className}
      `.trim()}
      disabled={disabled || loading}
      onMouseDown={startHold}
      onMouseUp={cancelHold}
      onMouseLeave={cancelHold}
      onTouchStart={startHold}
      onTouchEnd={cancelHold}
      onTouchCancel={cancelHold}
      aria-label={loading ? loadingLabel : label}
    >
      {/* プログレスゲージ（背景を塗りつぶす） */}
      {!disabled && !loading && progress > 0 && (
        <span
          className={`absolute inset-y-0 left-0 ${fillColor} transition-none`}
          style={{ width: `${Math.min(progress, 100)}%` }}
          aria-hidden="true"
        />
      )}

      {/* テキスト（ゲージの上に重ねる） */}
      <span className={`relative z-10 flex items-center justify-center gap-1 ${textColor}`}>
        {loading ? (
          <>
            <span className="animate-spin inline-block">⟳</span>
            {loadingLabel}
          </>
        ) : (
          <>
            <span className="opacity-70">⏸</span>
            {label}
          </>
        )}
      </span>
    </button>
  );
}
