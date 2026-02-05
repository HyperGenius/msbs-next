/* frontend/src/app/page.tsx */
"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { BattleLog, MobileSuit } from "@/types/battle";
import { useMissions, useMobileSuits, useEntryStatus, entryBattle, cancelEntry } from "@/services/api";
import BattleViewer from "@/components/BattleViewer";
import Header from "@/components/Header";

export default function Home() {
  const { getToken, isSignedIn } = useAuth();
  const { missions, isLoading: missionsLoading } = useMissions();
  const { mobileSuits, isLoading: mobileSuitsLoading } = useMobileSuits();
  const { entryStatus, isLoading: entryStatusLoading, mutate: mutateEntryStatus } = useEntryStatus();
  const [logs, setLogs] = useState<BattleLog[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [winner, setWinner] = useState<string | null>(null);
  const [winLoss, setWinLoss] = useState<"WIN" | "LOSE" | "DRAW" | null>(null);
  const [currentTurn, setCurrentTurn] = useState(0);
  const [maxTurn, setMaxTurn] = useState(0);
  const [selectedMissionId, setSelectedMissionId] = useState<number>(1);
  // 表示用にstateを追加
  const [playerData, setPlayerData] = useState<MobileSuit | null>(null);
  const [enemiesData, setEnemiesData] = useState<MobileSuit[]>([]);
  const [entryLoading, setEntryLoading] = useState(false);


  const startBattle = async (missionId: number) => {
    setIsLoading(true);
    setLogs([]);
    setWinner(null);
    setWinLoss(null);
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
      const res = await fetch(`http://127.0.0.1:8000/api/battle/simulate?mission_id=${missionId}`, {
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

      // 勝敗を判定
      if (data.winner_id && data.player_info && data.winner_id === data.player_info.id) {
        setWinLoss("WIN");
      } else if (data.winner_id === "ENEMY") {
        setWinLoss("LOSE");
      } else {
        setWinLoss("DRAW");
      }

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

  const handleEntry = async () => {
    if (!mobileSuits || mobileSuits.length === 0) {
      alert("機体がありません。ガレージで機体を作成してください。");
      return;
    }

    setEntryLoading(true);
    try {
      // 最初の機体でエントリー
      // TODO: 将来的にユーザーが機体を選択できるようにする
      await entryBattle(mobileSuits[0].id);
      // エントリー状況を再取得
      await mutateEntryStatus();
      alert("エントリーが完了しました！");
    } catch (error) {
      console.error("Error creating entry:", error);
      alert(`エントリーに失敗しました: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setEntryLoading(false);
    }
  };

  const handleCancelEntry = async () => {
    setEntryLoading(true);
    try {
      await cancelEntry();
      // エントリー状況を再取得
      await mutateEntryStatus();
      alert("エントリーをキャンセルしました。");
    } catch (error) {
      console.error("Error cancelling entry:", error);
      alert(`キャンセルに失敗しました: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setEntryLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-900 text-green-400 p-8 font-mono">
      <div className="max-w-4xl mx-auto">
        <Header />

        {/* Battle Result Display */}
        {winLoss && (
          <div className="mb-8 text-center">
            <div
              className={`inline-block px-12 py-6 rounded-lg text-4xl font-bold animate-pulse ${
                winLoss === "WIN"
                  ? "bg-green-900 text-green-300 border-4 border-green-500"
                  : winLoss === "LOSE"
                  ? "bg-red-900 text-red-300 border-4 border-red-500"
                  : "bg-yellow-900 text-yellow-300 border-4 border-yellow-500"
              }`}
            >
              {winLoss === "WIN" && "★ MISSION COMPLETE ★"}
              {winLoss === "LOSE" && "✕ MISSION FAILED ✕"}
              {winLoss === "DRAW" && "- DRAW -"}
            </div>
          </div>
        )}

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

        {/* Entry Panel */}
        <div className="mb-8 bg-gray-800 p-6 rounded-lg border border-green-800">
          <h2 className="text-2xl font-bold mb-4 border-l-4 border-green-500 pl-2">
            ENTRY / 出撃登録
          </h2>
          
          {!isSignedIn ? (
            <div className="text-yellow-400 p-4 border border-yellow-700 rounded bg-yellow-900/20">
              エントリーするにはログインが必要です
            </div>
          ) : entryStatusLoading ? (
            <p className="text-gray-400">エントリー状況を確認中...</p>
          ) : entryStatus?.is_entered ? (
            <div className="space-y-4">
              <div className="p-4 border-2 border-green-500 rounded bg-green-900/30">
                <p className="text-green-300 font-bold mb-2">✓ エントリー済み</p>
                <p className="text-sm text-gray-300">
                  次回更新: {entryStatus.entry && new Date(entryStatus.entry.scheduled_at).toLocaleString('ja-JP')}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  使用機体ID: {entryStatus.entry?.mobile_suit_id}
                </p>
              </div>
              <button
                onClick={handleCancelEntry}
                disabled={entryLoading}
                className={`px-6 py-3 rounded font-bold transition-colors ${
                  entryLoading
                    ? "bg-gray-500 cursor-not-allowed text-gray-300"
                    : "bg-red-700 hover:bg-red-600 text-white"
                }`}
              >
                {entryLoading ? "処理中..." : "エントリーをキャンセル"}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-4 border border-gray-700 rounded bg-gray-900">
                <p className="text-gray-300 mb-2">
                  {entryStatus?.next_room 
                    ? `次回バトル: ${new Date(entryStatus.next_room.scheduled_at).toLocaleString('ja-JP')}`
                    : "次回バトルの予定を確認中..."}
                </p>
                <p className="text-sm text-gray-400">
                  エントリーすると次回の定期バトルに参加できます
                </p>
              </div>
              <button
                onClick={handleEntry}
                disabled={entryLoading || mobileSuitsLoading || !mobileSuits || mobileSuits.length === 0}
                className={`px-8 py-3 rounded font-bold text-black transition-colors shadow-lg ${
                  entryLoading || mobileSuitsLoading || !mobileSuits || mobileSuits.length === 0
                    ? "bg-gray-500 cursor-not-allowed"
                    : "bg-green-500 hover:bg-green-400 hover:shadow-green-500/50"
                }`}
              >
                {entryLoading ? "処理中..." : mobileSuitsLoading ? "機体確認中..." : "エントリーする"}
              </button>
              {mobileSuits && mobileSuits.length === 0 && (
                <p className="text-xs text-yellow-500">
                  ※ エントリーするには機体が必要です。ガレージで機体を作成してください。
                </p>
              )}
            </div>
          )}
        </div>

        {/* Mission Selection Panel */}
        <div className="mb-8 bg-gray-800 p-6 rounded-lg border border-green-800">
          <h2 className="text-2xl font-bold mb-4 border-l-4 border-green-500 pl-2">即時シミュレーション（テスト機能）</h2>
          <p className="text-sm text-gray-400 mb-4">※ 開発用の即時バトルシミュレーション機能です</p>
          
          {missionsLoading ? (
            <p className="text-gray-400">Loading missions...</p>
          ) : missions && missions.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {missions.map((mission) => (
                <button
                  key={mission.id}
                  onClick={() => setSelectedMissionId(mission.id)}
                  className={`p-4 rounded-lg border-2 transition-all text-left ${
                    selectedMissionId === mission.id
                      ? "border-green-500 bg-green-900/30"
                      : "border-gray-700 bg-gray-900 hover:border-green-700"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-lg">{mission.name}</span>
                    <span className="text-xs px-2 py-1 rounded bg-yellow-900 text-yellow-300">
                      難易度: {mission.difficulty}
                    </span>
                  </div>
                  <p className="text-sm text-gray-400">{mission.description}</p>
                  <p className="text-xs text-gray-500 mt-2">
                    敵機: {mission.enemy_config?.enemies?.length || 0} 機
                  </p>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-red-400 mb-4">ミッションが見つかりません。Backendでシードスクリプトを実行してください。</p>
          )}

          {/* Control Panel */}
          <div className="flex justify-between items-center">
            <div>
              <p className="font-bold text-blue-400">PLAYER: {playerData ? playerData.name : "Waiting for Data..."}</p>
              <p className="font-bold text-red-400">ENEMIES: {enemiesData.length > 0 ? `${enemiesData.length} units` : "Waiting for Data..."}</p>
            </div>
            <button
              onClick={() => startBattle(selectedMissionId)}
              disabled={isLoading || !missions || missions.length === 0}
              className={`px-8 py-3 rounded font-bold text-black transition-colors shadow-lg ${
                isLoading || !missions || missions.length === 0
                  ? "bg-gray-500 cursor-not-allowed"
                  : "bg-yellow-500 hover:bg-yellow-400 hover:shadow-yellow-500/50"
              }`}
            >
              {isLoading ? "CALCULATING..." : "即時シミュレーション実行"}
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