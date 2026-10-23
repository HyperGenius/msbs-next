/* frontend/src/components/Dashboard/MissionSelector.tsx */
"use client";

import { AvailableMission, TheaterForecast } from "@/types/battle";
import { describeObjective } from "@/utils/missionName";
import {
  formatMinovskyDensity,
  getEnvironmentVisual,
} from "@/utils/theater";

interface MissionSelectorProps {
  missions: AvailableMission[];
  /** 今回の開催の戦域。作戦は全てこの戦域で戦う */
  theater: TheaterForecast | null;
  /** 選択中の作戦ID。null はデイリーバトルロイヤル */
  selectedMissionId: number | null;
  onSelect: (missionId: number | null) => void;
  disabled?: boolean;
}

/** 出撃先の1枚のカード */
function OptionCard({
  selected,
  disabled,
  onClick,
  title,
  badge,
  objective,
  description,
  theater,
}: {
  selected: boolean;
  disabled?: boolean;
  onClick: () => void;
  title: string;
  badge: string;
  objective: string;
  description: string;
  theater: TheaterForecast | null;
}) {
  const visual = theater ? getEnvironmentVisual(theater.environment_id) : null;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={selected}
      className={`w-full text-left p-3 border-2 font-mono transition-colors no-min-size ${
        selected
          ? "border-[#00ff41] bg-[#00ff41]/10"
          : "border-[#00ff41]/20 bg-[#0a0a0a] hover:border-[#00ff41]/50"
      } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className={`font-bold ${selected ? "text-[#00ff41]" : "text-white"}`}>
          {selected ? "◉ " : "○ "}
          {title}
        </span>
        <span className="shrink-0 text-[10px] text-[#00ff41]/60 border border-[#00ff41]/30 px-1.5 py-0.5">
          {badge}
        </span>
      </div>
      <p className="mt-1 text-xs text-[#ffb000]/90">目的: {objective}</p>
      <p className="mt-1 text-xs text-[#00ff41]/60">{description}</p>
      {theater && visual && (
        <p className="mt-2 pt-2 border-t border-[#00ff41]/10 text-xs text-[#00ff41]/70">
          <span aria-hidden="true">{visual.icon}</span>{" "}
          <span className={visual.textClass}>{theater.theater_name}</span>
          （{theater.environment_name}・ミノフスキー{" "}
          {formatMinovskyDensity(theater.minovsky_density)}）
        </p>
      )}
    </button>
  );
}

/**
 * 出撃先（デイリーバトルロイヤルか作戦）を選ぶカード一覧。
 * モバイル幅でも1列で読めるよう、縦に並べる。
 */
export default function MissionSelector({
  missions,
  theater,
  selectedMissionId,
  onSelect,
  disabled,
}: MissionSelectorProps) {
  // 作戦が無いときは選ぶ余地が無いので出さない
  if (missions.length === 0) return null;

  return (
    <div className="space-y-2 text-left">
      <p className="text-xs text-[#00ff41]/50 font-mono tracking-widest">出撃先を選択</p>
      <OptionCard
        selected={selectedMissionId === null}
        disabled={disabled}
        onClick={() => onSelect(null)}
        title="デイリーバトルロイヤル"
        badge="BATTLE ROYALE"
        objective="最後まで生き残り、敵を撃破する"
        description="他のプレイヤーと同じフィールドで戦う定期バトル"
        theater={theater}
      />
      {missions.map((mission) => (
        <OptionCard
          key={mission.id}
          selected={selectedMissionId === mission.id}
          disabled={disabled}
          onClick={() => onSelect(mission.id)}
          title={mission.name}
          badge={`作戦 ★${mission.difficulty}`}
          objective={describeObjective(mission)}
          description={mission.description}
          theater={theater}
        />
      ))}
    </div>
  );
}
