/* frontend/src/components/Dashboard/TheaterForecastCard.tsx */
import { MinovskyLevel, MobileSuit, TheaterForecast } from "@/types/battle";
import { getRankColor } from "@/utils/rankUtils";
import {
  formatForecastDate,
  getEnvironmentVisual,
  getMinovskyLevelLabel,
  getTerrainGradeFor,
  isUnsuitableTerrainGrade,
} from "@/utils/theater";

interface TheaterForecastCardProps {
  /** 予報。取得前は undefined */
  forecasts?: TheaterForecast[];
  /** エントリー中の機体。渡すとその環境の地形適正を表示する */
  mobileSuit?: MobileSuit;
}

const MINOVSKY_LEVEL_COLORS: Record<MinovskyLevel, string> = {
  LOW: "text-[#00ff41]",
  MEDIUM: "text-[#ffb000]",
  HIGH: "text-red-400",
};

/**
 * 今回の戦域（環境・ミノフスキー濃度・ヒント・機体の地形適正）と、
 * 次回以降の戦域の予報を表示するカード
 */
export default function TheaterForecastCard({
  forecasts,
  mobileSuit,
}: TheaterForecastCardProps) {
  if (!forecasts) return null;

  const current = forecasts.find((f) => f.is_current);
  const upcoming = forecasts.filter((f) => !f.is_current);

  if (!current && upcoming.length === 0) {
    return (
      <div className="bg-[#0a0a0a] border border-[#00ff41]/20 p-3 font-mono text-xs text-[#00ff41]/50">
        現在、戦域の予報はありません
      </div>
    );
  }

  return (
    <div
      className={`bg-[#0a0a0a] border-2 p-4 font-mono ${
        current ? getEnvironmentVisual(current.environment_id).borderClass : "border-[#00ff41]/20"
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-[#00ff41]/50 tracking-widest">今回の戦域</span>
        {current && (
          <span className="text-xs text-[#00ff41]/40">
            {formatForecastDate(current.scheduled_at)}
          </span>
        )}
      </div>

      {current ? (
        <CurrentTheater forecast={current} mobileSuit={mobileSuit} />
      ) : (
        <p className="text-xs text-[#00ff41]/50">今回の戦域の情報はありません</p>
      )}

      {upcoming.length > 0 && (
        <ul className="mt-3 pt-3 border-t border-[#00ff41]/10 space-y-1.5 text-xs">
          {upcoming.map((f, i) => {
            const visual = getEnvironmentVisual(f.environment_id);
            const date = formatForecastDate(f.scheduled_at);
            return (
              <li key={f.scheduled_at} className="flex items-baseline gap-2">
                <span className="text-[#00ff41]/40 shrink-0">
                  {i === 0 ? `次回 ${date}` : date}
                </span>
                <span aria-hidden="true">{visual.icon}</span>
                <span className="text-[#00ff41]/80 min-w-0">
                  <span className={visual.textClass}>{f.theater_name}</span>{" "}
                  <span className="whitespace-nowrap">
                    （{f.environment_name}・ミノフスキー{" "}
                    <span className={MINOVSKY_LEVEL_COLORS[f.minovsky_level]}>
                      {getMinovskyLevelLabel(f.minovsky_level)}
                    </span>
                    ）
                  </span>
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/** 今回の戦域の詳細と、エントリー中の機体の地形適正 */
function CurrentTheater({
  forecast,
  mobileSuit,
}: {
  forecast: TheaterForecast;
  mobileSuit?: MobileSuit;
}) {
  const visual = getEnvironmentVisual(forecast.environment_id);
  const grade = mobileSuit ? getTerrainGradeFor(mobileSuit, forecast) : null;

  return (
    <>
      <div className="flex items-center gap-3">
        <span className="text-2xl" aria-hidden="true">
          {visual.icon}
        </span>
        <div className="min-w-0">
          <div className={`font-bold text-lg ${visual.textClass}`}>{forecast.theater_name}</div>
          <div className="text-xs text-[#00ff41]/60">環境: {forecast.environment_name}</div>
        </div>
      </div>

      <div className="mt-3 flex items-baseline justify-between text-xs">
        <span className="text-[#00ff41]/50">ミノフスキー濃度</span>
        <span>
          <span className="text-white font-bold text-base">
            {Math.round(forecast.minovsky_density * 100)}%
          </span>{" "}
          <span className={MINOVSKY_LEVEL_COLORS[forecast.minovsky_level]}>
            （{getMinovskyLevelLabel(forecast.minovsky_level)}）
          </span>
        </span>
      </div>

      {forecast.hint && (
        <p className="mt-2 text-xs text-[#ffb000]/80">▶ {forecast.hint}</p>
      )}

      {mobileSuit && grade && (
        <div className="mt-3 pt-3 border-t border-[#00ff41]/10 text-xs">
          <div className="flex items-baseline gap-2">
            <span className="text-[#00ff41]/50">あなたの機体:</span>
            <span className="text-[#00ff41]/80">
              {forecast.environment_name}適正{" "}
              <span className={`font-bold ${getRankColor(grade)}`}>{grade}</span>
            </span>
          </div>
          {isUnsuitableTerrainGrade(grade) && (
            <p className="mt-1 text-red-400">⚠ この戦域には不向き。機体の組み替えを検討してください</p>
          )}
        </div>
      )}
    </>
  );
}
