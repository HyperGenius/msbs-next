/* frontend/src/app/page.tsx */
"use client";

import { useState } from "react";
import { BattleLog, MobileSuit, BattleResponse } from "@/types/battle";
import BattleViewer from "@/components/BattleViewer";

export default function Home() {
  const [logs, setLogs] = useState<BattleLog[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [winner, setWinner] = useState<string | null>(null);
  const [currentTurn, setCurrentTurn] = useState(0);
  const [maxTurn, setMaxTurn] = useState(0);

  // テスト用の機体データ（Backendに送るもの）
  // 3D表示で見栄えがするように、少し初期位置を離しています
  const testData = {
    ms1: {
      id: "gundam",
      name: "ガンダム",
      max_hp: 1000,
      current_hp: 1000,
      armor: 100,
      mobility: 1.5,
      position: { x: -500, y: -500, z: 0 },
      weapons: [
        { id: "br", name: "ビームライフル", power: 300, range: 600, accuracy: 80 },
      ],
    } as MobileSuit,
    ms2: {
      id: "zaku",
      name: "ザクII",
      max_hp: 800,
      current_hp: 800,
      armor: 50,
      mobility: 1.0,
      position: { x: 500, y: 500, z: 0 },
      weapons: [
        { id: "mg", name: "ザクマシンガン", power: 100, range: 400, accuracy: 60 },
      ],
    } as MobileSuit,
  };

  const startBattle = async () => {
    setIsLoading(true);
    setLogs([]);
    setWinner(null);
    setCurrentTurn(0);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/battle/simulate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(testData),
      });

      if (!res.ok) {
        throw new Error("Network response was not ok");
      }

      const data: BattleResponse = await res.json();
      setLogs(data.logs);
      setWinner(data.winner_id);

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
        <header className="mb-8 border-b border-green-700 pb-4">
          <h1 className="text-3xl font-bold">MSBS-Next Simulator</h1>
          <p className="text-sm opacity-70">Phase 1: Prototype Environment</p>
        </header>

        {/* 3D Viewer Area: ログがある時だけ表示 */}
        {logs.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold mb-2 border-l-4 border-green-500 pl-2">Tactical Monitor</h2>

            {/* 3D Canvas Component */}
            <BattleViewer
              logs={logs}
              ms1={testData.ms1}
              ms2={testData.ms2}
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
              <p className="font-bold text-blue-400">UNIT 1: {testData.ms1.name}</p>
              <p className="font-bold text-red-400">UNIT 2: {testData.ms2.name}</p>
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
                return (
                  <li
                    key={index}
                    className={`border-l-2 pl-2 py-1 transition-colors ${isCurrentTurn
                        ? "border-green-400 bg-green-900/30 text-white"
                        : "border-green-900 text-green-600"
                      }`}
                  >
                    <span className="opacity-50 mr-4 w-16 inline-block">[Turn {log.turn}]</span>
                    <span className={`font-bold mr-2 ${log.actor_id === testData.ms1.id ? 'text-blue-400' : 'text-red-400'}`}>
                      {log.actor_id}:
                    </span>
                    <span>{log.message}</span>
                  </li>
                );
              })}

              {/* Winner Announcement */}
              {winner && (
                <li className="mt-8 text-center text-xl border-t border-green-500 pt-4 text-yellow-400 animate-pulse font-bold">
                  *** WINNER: {winner === testData.ms1.id ? testData.ms1.name : testData.ms2.name} ***
                </li>
              )}
            </ul>
          )}
        </div>
      </div>
    </main>
  );
}