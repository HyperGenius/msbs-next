/* frontend/src/app/page.tsx */
"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { BattleLog, MobileSuit } from "@/types/battle";
import BattleViewer from "@/components/BattleViewer";
import Header from "@/components/Header";

export default function Home() {
  const { getToken } = useAuth();
  const [logs, setLogs] = useState<BattleLog[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [winner, setWinner] = useState<string | null>(null);
  const [currentTurn, setCurrentTurn] = useState(0);
  const [maxTurn, setMaxTurn] = useState(0);
  // 表示用にstateを追加
  const [playerData, setPlayerData] = useState<MobileSuit | null>(null);
  const [enemiesData, setEnemiesData] = useState<MobileSuit[]>([]);


  const startBattle = async () => {
    setIsLoading(true);
    setLogs([]);
    setWinner(null);
    setCurrentTurn(0);

    try {
      const token = await getToken();
      const headers: HeadersInit = {
        "Content-Type": "application/json",
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      // バックエンドからデータを取得
      const res = await fetch("http://127.0.0.1:8000/api/battle/simulate", {
        method: "POST",
        headers,
        body: ""
      });

      if (!res.ok) {
        throw new Error("Network response was not ok");
      }

      const data = await res.json(); // 型定義を interface BattleResponseWithInfo に更新するとベター

      setLogs(data.logs);
      setWinner(data.winner_id);

      // DBから取得した機体情報をセット
      setPlayerData(data.player_info);
      setEnemiesData(data.enemies_info);

      // 最大ターン数を計算して設定
      const lastTurn = data.logs.length > 0 ? data.logs[data.logs.length - 1].turn : 0;
      setMaxTurn(lastTurn);

    } catch (error) {
      console.error("Error fetching battle logs:", error);
      alert("通信エラーが発生しました。Backendが起動しているか確認してください。");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-900 text-green-400 p-8 font-mono">
      <div className="max-w-4xl mx-auto">
        <Header />

        {/* 3D Viewer Area: ログがある時だけ表示 */}
        {logs.length > 0 && playerData && enemiesData.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold mb-2 border-l-4 border-green-500 pl-2">Tactical Monitor</h2>

            {/* 3D Canvas Component */}
            <BattleViewer
              logs={logs}
              player={playerData}
              enemies={enemiesData}
              currentTurn={currentTurn}
            />

            {/* Turn Controller */}
            <div className="flex items-center gap-4 bg-gray-800 p-4 rounded border border-green-800 mt-2">
              <button
                onClick={() => setCurrentTurn(Math.max(0, currentTurn - 1))}
                className="px-4 py-2 bg-green-900 hover:bg-green-800 rounded font-bold transition-colors"
                disabled={currentTurn <= 0}
              >
                &lt; PREV
              </button>

              <div className="flex-grow flex flex-col px-4">
                <input
                  type="range"
                  min="0"
                  max={maxTurn}
                  value={currentTurn}
                  onChange={(e) => setCurrentTurn(Number(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-green-500"
                />
                <div className="flex justify-between text-xs mt-1 text-gray-400">
                  <span>Start</span>
                  <span>Turn: {currentTurn} / {maxTurn}</span>
                  <span>End</span>
                </div>
              </div>

              <button
                onClick={() => setCurrentTurn(Math.min(maxTurn, currentTurn + 1))}
                className="px-4 py-2 bg-green-900 hover:bg-green-800 rounded font-bold transition-colors"
                disabled={currentTurn >= maxTurn}
              >
                NEXT &gt;
              </button>
            </div>
          </div>
        )}

        {/* Control Panel */}
        <div className="mb-8 bg-gray-800 p-6 rounded-lg border border-green-800">
          <div className="flex justify-between items-center mb-4">
            <div>
              <p className="font-bold text-blue-400">PLAYER: {playerData ? playerData.name : "Waiting for Data..."}</p>
              <p className="font-bold text-red-400">ENEMIES: {enemiesData.length > 0 ? `${enemiesData.length} units` : "Waiting for Data..."}</p>
            </div>
            <button
              onClick={startBattle}
              disabled={isLoading}
              className={`px-8 py-3 rounded font-bold text-black transition-colors shadow-lg ${isLoading
                ? "bg-gray-500 cursor-not-allowed"
                : "bg-green-500 hover:bg-green-400 hover:shadow-green-500/50"
                }`}
            >
              {isLoading ? "CALCULATING..." : "START SIMULATION"}
            </button>
          </div>
        </div>

        {/* Text Log Area */}
        <div className="bg-black p-4 rounded border border-green-900 min-h-[400px] max-h-[600px] overflow-y-auto shadow-inner font-mono text-sm">
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

                return (
                  <li
                    key={index}
                    className={`border-l-2 pl-2 py-1 transition-colors ${isCurrentTurn
                      ? "border-green-400 bg-green-900/30 text-white"
                      : "border-green-900 text-green-600"
                      }`}
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
    </main>
  );
}