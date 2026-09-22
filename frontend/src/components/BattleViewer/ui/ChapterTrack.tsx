/* frontend/src/components/BattleViewer/ui/ChapterTrack.tsx */
"use client";

import { useEffect, useMemo, useRef } from "react";
import { ChapterEvent } from "../hooks/useBattleChapters";

interface ChapterTrackProps {
  chapters: ChapterEvent[];
  currentTimestamp: number;
  onSeek: (timestamp: number) => void;
}

/**
 * 3Dビューア直下に常駐する「チャプタートラック」（Issue #521）。
 * 有意なイベントのみを表示し、読むログではなくジャンプ先として機能する。
 * 再生位置に同期して現在のチャプターをハイライトし、自動スクロールで追従する。
 */
export default function ChapterTrack({ chapters, currentTimestamp, onSeek }: ChapterTrackProps) {
  const trackRef = useRef<HTMLDivElement>(null);
  const chipRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

  const currentChapterId = useMemo(() => {
    let current: ChapterEvent | null = null;
    for (const chapter of chapters) {
      if (chapter.timestamp <= currentTimestamp) {
        current = chapter;
      } else {
        break;
      }
    }
    return current?.id ?? null;
  }, [chapters, currentTimestamp]);

  useEffect(() => {
    if (!currentChapterId) return;
    const chip = chipRefs.current.get(currentChapterId);
    chip?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
  }, [currentChapterId]);

  if (chapters.length === 0) return null;

  return (
    <div className="mt-2">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-gray-500 tracking-widest">CHAPTERS</span>
        <span className="text-[10px] text-gray-600">再生位置と連動・クリックでジャンプ</span>
      </div>
      <div ref={trackRef} className="flex gap-1.5 overflow-x-auto pb-1">
        {chapters.map((chapter) => {
          const isCurrent = chapter.id === currentChapterId;
          return (
            <button
              key={chapter.id}
              ref={(el) => {
                if (el) chipRefs.current.set(chapter.id, el);
                else chipRefs.current.delete(chapter.id);
              }}
              onClick={() => onSeek(chapter.timestamp)}
              className="flex-none rounded-full px-2.5 py-1 text-[11px] whitespace-nowrap border transition-colors"
              style={
                isCurrent
                  ? { backgroundColor: chapter.accentColor, borderColor: chapter.accentColor, color: "#0b0f16" }
                  : { backgroundColor: "transparent", borderColor: chapter.accentColor, color: chapter.accentColor }
              }
            >
              <span className="mr-1">{chapter.icon}</span>
              {chapter.timestamp.toFixed(1)}s {chapter.label}
              {chapter.detail && <span className="ml-1 font-bold">{chapter.detail}</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}
