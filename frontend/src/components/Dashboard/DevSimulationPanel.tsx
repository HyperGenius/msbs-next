/**
 * DevSimulationPanel
 * 開発環境（NODE_ENV === "development"）でのみ表示される即時シミュレーションパネル
 */
import { BattleLog, Mission, MobileSuit } from "@/types/battle";
import { SciFiPanel, SciFiButton, SciFiHeading } from "@/components/ui";

interface DevSimulationPanelProps {
  missions: Mission[] | undefined;
  missionsLoading: boolean;
  selectedMissionId: number;
  setSelectedMissionId: (id: number) => void;
  playerData: MobileSuit | null;
  enemiesData: MobileSuit[];
  isLoading: boolean;
  startBattle: (missionId: number) => void;
  logs: BattleLog[];
  currentTurn: number;
  winner: string | null;
}

export default function DevSimulationPanel({
  missions,
  missionsLoading,
  selectedMissionId,
  setSelectedMissionId,
  playerData,
  enemiesData,
  isLoading,
  startBattle,
  logs,
  currentTurn,
  winner,
}: DevSimulationPanelProps) {
  if (process.env.NODE_ENV !== "development") return null;

  return (
    <SciFiPanel variant="secondary" className="mb-4 sm:mb-8 mission-selection-panel">
      <div className="p-4 sm:p-6">
        <SciFiHeading level={2} className="mb-4 text-xl sm:text-2xl" variant="secondary">
          即時シミュレーション（テスト機能）
        </SciFiHeading>
        <p className="text-xs sm:text-sm text-[#ffb000]/60 mb-4">※ 開発用の即時バトルシミュレーション機能です</p>

        {missionsLoading ? (
          <p className="text-[#00ff41]/60">Loading missions...</p>
        ) : missions && missions.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 mb-6">
            {missions.map((mission) => (
              <button
                key={mission.id}
                onClick={() => setSelectedMissionId(mission.id)}
                className={`p-3 sm:p-4 border-2 transition-all text-left touch-manipulation ${
                  selectedMissionId === mission.id
                    ? "border-[#ffb000] bg-[#ffb000]/10 sf-border-glow-amber"
                    : "border-[#ffb000]/30 bg-[#0a0a0a] hover:border-[#ffb000]/50"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-base sm:text-lg text-[#ffb000]">{mission.name}</span>
                  <span className="text-[10px] sm:text-xs px-2 py-1 bg-[#ffb000]/20 text-[#ffb000] border border-[#ffb000]/50">
                    難易度: {mission.difficulty}
                  </span>
                </div>
                <p className="text-xs sm:text-sm text-[#00ff41]/60">{mission.description}</p>
                <div className="flex items-center justify-between mt-2">
                  <p className="text-[10px] sm:text-xs text-[#00ff41]/50">
                    敵機: {mission.enemy_config?.enemies?.length || 0} 機
                  </p>
                  {mission.environment && (
                    <span className="text-[10px] sm:text-xs px-2 py-1 bg-[#00f0ff]/20 text-[#00f0ff] border border-[#00f0ff]/50">
                      環境: {mission.environment}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        ) : (
          <p className="text-red-400 mb-4 text-sm">ミッションが見つかりません。Backendでシードスクリプトを実行してください。</p>
        )}

        {/* Control Panel */}
        <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-4">
          <div className="space-y-1 text-sm sm:text-base">
            <p className="font-bold text-[#00f0ff]">PLAYER: {playerData ? playerData.name : "Waiting for Data..."}</p>
            <p className="font-bold text-[#ffb000]">ENEMIES: {enemiesData.length > 0 ? `${enemiesData.length} units` : "Waiting for Data..."}</p>
          </div>
          <SciFiButton
            onClick={() => startBattle(selectedMissionId)}
            disabled={isLoading || !missions || missions.length === 0}
            variant="secondary"
            size="lg"
            data-action="start-simulation"
            className="w-full sm:w-auto"
          >
            {isLoading ? "CALCULATING..." : "即時シミュレーション実行"}
          </SciFiButton>
        </div>

        {/* Text Log Area */}
        <div className="mt-6 bg-black p-4 rounded border border-green-900 min-h-[400px] max-h-[600px] overflow-y-auto shadow-inner font-mono text-sm">
          {logs.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center opacity-30 min-h-[300px]">
              <p>-- NO BATTLE DATA --</p>
              <p className="text-xs mt-2">Initialize simulation to view logs</p>
            </div>
          ) : (
            <ul className="space-y-1">
              {logs.map((log, index) => {
                // 現在のターンに対応するログをハイライト
                const isCurrentTurn = log.turn === currentTurn;

                // ログ表示用: playerDataなどがnullの場合はIDをそのまま表示
                const actorName = log.actor_id === playerData?.id ? playerData.name
                  : enemiesData.find(e => e.id === log.actor_id)?.name
                    || log.actor_id;
                const isPlayer = log.actor_id === playerData?.id;

                // メッセージタイプに応じたスタイルを決定するヘルパー関数
                const getLogStyle = () => {
                  // リソース関連メッセージ判定
                  const isResourceMessage = log.message.includes("弾切れ") ||
                                          log.message.includes("EN不足") ||
                                          log.message.includes("クールダウン") ||
                                          log.message.includes("待機");

                  // 地形・索敵関連メッセージ判定
                  const isTerrainMessage = log.action_type === "DETECTION" ||
                                         log.message.includes("地形") ||
                                         log.message.includes("索敵");

                  // 属性関連メッセージ判定
                  const isAttributeMessage = log.message.includes("BEAM") ||
                                           log.message.includes("PHYSICAL") ||
                                           log.message.includes("ビーム") ||
                                           log.message.includes("実弾");

                  if (isCurrentTurn) {
                    return {
                      borderStyle: "border-green-400",
                      bgStyle: "bg-green-900/30",
                      textStyle: "text-white"
                    };
                  }

                  if (isResourceMessage) {
                    return {
                      borderStyle: "border-orange-500",
                      bgStyle: "",
                      textStyle: "text-orange-400 font-semibold"
                    };
                  }

                  if (isTerrainMessage) {
                    return {
                      borderStyle: "border-cyan-500",
                      bgStyle: "",
                      textStyle: "text-cyan-400"
                    };
                  }

                  if (isAttributeMessage) {
                    return {
                      borderStyle: "border-purple-500",
                      bgStyle: "",
                      textStyle: "text-purple-400"
                    };
                  }

                  return {
                    borderStyle: "border-green-900",
                    bgStyle: "",
                    textStyle: "text-green-600"
                  };
                };

                const { borderStyle, bgStyle, textStyle } = getLogStyle();

                return (
                  <li
                    key={index}
                    className={`border-l-2 pl-2 py-1 transition-colors ${borderStyle} ${bgStyle} ${textStyle}`}
                  >
                    <span className="opacity-50 mr-4 w-16 inline-block">[Turn {log.turn}]</span>
                    <span className={`font-bold mr-2 ${isPlayer ? 'text-blue-400' : 'text-red-400'}`}>
                      {actorName}:
                    </span>
                    <span>{log.message}</span>
                  </li>
                );
              })}

              {/* Winner Announcement */}
              {winner && playerData && (
                <li className="mt-8 text-center text-xl border-t border-green-500 pt-4 text-yellow-400 animate-pulse font-bold">
                  *** WINNER: {winner === playerData.id ? playerData.name : "ENEMY FORCES"} ***
                </li>
              )}
            </ul>
          )}
        </div>
      </div>
    </SciFiPanel>
  );
}
