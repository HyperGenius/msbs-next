"use client";

import { TheaterRotationSlot } from "@/types/admin";
import { formatJstDate } from "@/lib/theater";

interface TheaterRotationPanelProps {
  rotation: TheaterRotationSlot[] | undefined;
  isLoading: boolean;
  isError: boolean;
}

const MINOVSKY_LEVEL_LABELS: Record<TheaterRotationSlot["minovsky_level"], string> = {
  LOW: "低",
  MEDIUM: "中",
  HIGH: "高",
};

const thClass = "px-2 py-1 text-left text-[#ffb000]/80 font-normal";
const tdClass = "px-2 py-1";

/** 今回と今後の開催の戦域・濃度。戦域を保存すると取り直す */
export default function TheaterRotationPanel({ rotation, isLoading, isError }: TheaterRotationPanelProps) {
  if (isLoading) {
    return <p className="text-[#ffb000] animate-pulse py-6 text-center text-xs">LOADING...</p>;
  }
  if (isError) {
    return <p className="py-6 text-center text-xs text-red-400">ローテーションを取得できません</p>;
  }
  if (!rotation || rotation.length === 0) {
    return <p className="py-6 text-center text-xs text-[#00ff41]/40">有効な戦域が無い</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b border-[#00ff41]/30">
            <th className={thClass}>開催日 (JST)</th>
            <th className={thClass}>戦域</th>
            <th className={thClass}>環境</th>
            <th className={`${thClass} text-right`}>ミノフスキー濃度</th>
          </tr>
        </thead>
        <tbody>
          {rotation.map((slot) => (
            <tr
              key={slot.scheduled_at}
              className={`border-b border-[#00ff41]/10 ${slot.is_current ? "bg-[#ffb000]/10" : ""}`}
            >
              <td className={tdClass}>
                {formatJstDate(slot.scheduled_at)}
                {slot.is_current && <span className="ml-1 text-[#ffb000]">今回（確定）</span>}
              </td>
              <td className={tdClass}>{slot.theater_name}</td>
              <td className={tdClass}>{slot.environment_name}</td>
              <td className={`${tdClass} text-right`}>
                {Math.round(slot.minovsky_density * 100)}%
                <span className="ml-1 text-[#00ff41]/40">（{MINOVSKY_LEVEL_LABELS[slot.minovsky_level]}）</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
