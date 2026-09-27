/* frontend/src/components/collection/TechnologyProgressCard.tsx */
import { PlayerTechnologyProgress } from "@/types/battle";
import { IconCpu } from "@/components/icons/TablerIcons";
import { UNAVAILABLE_MESSAGE, formatTheater } from "@/utils/blueprintCollection";
import { techProgressPercent } from "@/utils/technology";

interface TechnologyProgressCardProps {
  technology: PlayerTechnologyProgress;
}

/** 図鑑の技術タブで、技術1件の技術Lv・累計断片数・入手先を表示するカード */
export default function TechnologyProgressCard({ technology }: TechnologyProgressCardProps) {
  const isMax = technology.level >= technology.max_level;
  const percent = techProgressPercent(technology);
  const barBorder = isMax ? "border-[#00f0ff]/40" : "border-[#00ff41]/40";
  const barFill = isMax ? "bg-[#00f0ff]" : "bg-[#00ff41]";

  return (
    <div
      className={`flex items-start gap-3 border px-3 py-2 font-mono ${
        isMax
          ? "border-[#00f0ff]/60 bg-[#00f0ff]/5 text-[#00f0ff]"
          : "border-[#00ff41]/30 bg-[#0a0a0a] text-[#00ff41]"
      }`}
      data-testid="technology-progress-card"
    >
      <IconCpu className="w-7 h-7 shrink-0 mt-1" />
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-baseline justify-between gap-2">
          <p className="text-sm sm:text-base font-bold text-white truncate" title={technology.name}>
            {technology.name}
          </p>
          <span className="shrink-0 text-sm font-bold">
            Lv{technology.level}
            <span className="opacity-60">/{technology.max_level}</span>
          </span>
        </div>
        {technology.description && (
          <p className="text-[11px] text-gray-400">{technology.description}</p>
        )}

        <div
          className={`h-1.5 border bg-[#0a0a0a] ${barBorder}`}
          role="progressbar"
          aria-label={`${technology.name} の次のLvまでの進捗`}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
        >
          <div className={`h-full transition-all ${barFill}`} style={{ width: `${percent}%` }} />
        </div>
        <p className="text-[11px] opacity-80">
          累計 {technology.fragment_count} 個
          {isMax
            ? `・最大Lv（以降の断片は +${technology.overflow_credit_value.toLocaleString()} C に換金）`
            : `・次のLvまであと ${technology.fragments_to_next_level ?? 0} 個`}
        </p>

        {technology.obtainable_theaters.length === 0 ? (
          <p className="text-[11px] opacity-60">{UNAVAILABLE_MESSAGE}</p>
        ) : (
          <div className="flex flex-wrap items-center gap-1 text-[11px]">
            <span className="opacity-70">入手先</span>
            {technology.obtainable_theaters.map((theater) => (
              <span key={theater.label} className="border border-[#00ff41]/40 px-1.5 text-[#00ff41]">
                {formatTheater(theater)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
