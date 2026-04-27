/* frontend/src/hooks/useBattleSimulation.ts */
"use client";

import { useState, useEffect } from "react";
import { BattleLog, BattleRewards, Mission, MobileSuit } from "@/types/battle";

interface ModalResult {
  winLoss: "WIN" | "LOSE" | "DRAW";
  rewards: BattleRewards | null;
  msSnapshot?: MobileSuit | null;
  kills?: number;
}

interface UseBattleSimulationOptions {
  getToken: () => Promise<string | null>;
  missions: Mission[] | undefined;
  mutatePilot: () => void;
  setModalResult: (result: ModalResult | null) => void;
  setShowResultModal: (show: boolean) => void;
}

interface UseBattleSimulationReturn {
  logs: BattleLog[];
  isLoading: boolean;
  winner: string | null;
  winLoss: "WIN" | "LOSE" | "DRAW" | null;
  currentTimestamp: number;
  setCurrentTimestamp: (timestamp: number) => void;
  maxTimestamp: number;
  selectedMissionId: number;
  setSelectedMissionId: (id: number) => void;
  playerData: MobileSuit | null;
  enemiesData: MobileSuit[];
  rewards: BattleRewards | null;
  currentEnvironment: string;
  startBattle: (missionId: number) => Promise<void>;
}

/**
 * 開発用の即時バトルシミュレーション処理と状態管理を担うフック。
 * シミュレーション完了時に結果モーダルの表示も要求する。
 */
export function useBattleSimulation({
  getToken,
  missions,
  mutatePilot,
  setModalResult,
  setShowResultModal,
}: UseBattleSimulationOptions): UseBattleSimulationReturn {
  const [logs, setLogs] = useState<BattleLog[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [winner, setWinner] = useState<string | null>(null);
  const [winLoss, setWinLoss] = useState<"WIN" | "LOSE" | "DRAW" | null>(null);
  const [currentTimestamp, setCurrentTimestamp] = useState(0);
  const [maxTimestamp, setMaxTimestamp] = useState(0);
  const [selectedMissionId, setSelectedMissionId] = useState<number>(1);
  const [playerData, setPlayerData] = useState<MobileSuit | null>(null);
  const [enemiesData, setEnemiesData] = useState<MobileSuit[]>([]);
  const [rewards, setRewards] = useState<BattleRewards | null>(null);
  const [currentEnvironment, setCurrentEnvironment] =
    useState<string>("SPACE");

  // シミュレーション完了時に結果モーダルを表示
  useEffect(() => {
    if (winLoss && rewards) {
      setModalResult({
        winLoss,
        rewards,
        msSnapshot: playerData,
        kills: rewards.kills,
      });
      setShowResultModal(true);
    }
  }, [winLoss, rewards, playerData, setModalResult, setShowResultModal]);

  const startBattle = async (missionId: number) => {
    setIsLoading(true);
    setLogs([]);
    setWinner(null);
    setWinLoss(null);
    setCurrentTimestamp(0);
    setRewards(null);

    try {
      const token = await getToken();
      const headers: HeadersInit = {
        "Content-Type": "application/json",
      };

      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const selectedMission = missions?.find((m) => m.id === missionId);
      if (selectedMission?.environment) {
        setCurrentEnvironment(selectedMission.environment);
      }

      const res = await fetch(
        `http://127.0.0.1:8000/api/battle/simulate?mission_id=${missionId}`,
        {
          method: "POST",
          headers,
          body: "",
        }
      );

      if (!res.ok) {
        throw new Error("Network response was not ok");
      }

      const data = await res.json();

      setLogs(data.logs);
      setWinner(data.winner_id);

      if (
        data.winner_id &&
        data.player_info &&
        data.winner_id === data.player_info.id
      ) {
        setWinLoss("WIN");
      } else if (data.winner_id === "ENEMY") {
        setWinLoss("LOSE");
      } else {
        setWinLoss("DRAW");
      }

      setPlayerData(data.player_info);
      setEnemiesData(data.enemies_info);

      if (data.rewards) {
        setRewards(data.rewards);
        mutatePilot();
      }

      const lastTimestamp =
        data.logs.length > 0 ? data.logs[data.logs.length - 1].timestamp : 0;
      setMaxTimestamp(lastTimestamp);
    } catch (error) {
      console.error("Error fetching battle logs:", error);
      alert(
        "通信エラーが発生しました。Backendが起動しているか確認してください。"
      );
    } finally {
      setIsLoading(false);
    }
  };

  return {
    logs,
    isLoading,
    winner,
    winLoss,
    currentTimestamp,
    setCurrentTimestamp,
    maxTimestamp,
    selectedMissionId,
    setSelectedMissionId,
    playerData,
    enemiesData,
    rewards,
    currentEnvironment,
    startBattle,
  };
}
