/* frontend/src/app/page.tsx */
"use client";

import { useState, useEffect, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import { BattleLog, BattleResult, MobileSuit, BattleRewards } from "@/types/battle";
import { useMissions, useMobileSuits, useEntryStatus, useEntryCount, entryBattle, cancelEntry, usePilot, useBattleHistory, useUnreadBattleResults, markBattleAsRead, createPilot } from "@/services/api";
import BattleViewer from "@/components/BattleViewer";
import CountdownTimer from "@/components/Dashboard/CountdownTimer";
import EntryDashboard from "@/components/Dashboard/EntryDashboard";
import BattleResultModal from "@/components/Dashboard/BattleResultModal";
import EntrySelectionModal from "@/components/Dashboard/EntrySelectionModal";
import OnboardingOverlay from "@/components/Tutorial/OnboardingOverlay";
import StarterSelectionModal from "@/components/Tutorial/StarterSelectionModal";
import { SciFiPanel, SciFiButton, SciFiHeading, SciFiSelect } from "@/components/ui";
import DevSimulationPanel from "@/components/Dashboard/DevSimulationPanel";

const ONBOARDING_COMPLETED_KEY = "msbs_onboarding_completed";

type OnboardingState = "NOT_STARTED" | "BATTLE_STARTED" | "BATTLE_FINISHED" | "COMPLETED";

export default function Home() {
  const { getToken, isSignedIn, isLoaded } = useAuth();
  const { missions, isLoading: missionsLoading } = useMissions();
  const { mobileSuits, isLoading: mobileSuitsLoading, mutate: mutateMobileSuits } = useMobileSuits();
  const { entryStatus, isLoading: entryStatusLoading, mutate: mutateEntryStatus } = useEntryStatus();
  const { entryCount, mutate: mutateEntryCount } = useEntryCount();
  const { pilot, isLoading: pilotLoading, isError: pilotError, mutate: mutatePilot } = usePilot();
  const { battles, isLoading: battlesLoading } = useBattleHistory(1);
  const { unreadBattles, mutate: mutateUnreadBattles } = useUnreadBattleResults();
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
  const [rewards, setRewards] = useState<BattleRewards | null>(null);
  const [currentEnvironment, setCurrentEnvironment] = useState<string>("SPACE");
  const [showResultModal, setShowResultModal] = useState(false);
  const [modalResult, setModalResult] = useState<{
    winLoss: "WIN" | "LOSE" | "DRAW";
    rewards: BattleRewards | null;
    msSnapshot?: MobileSuit | null;
    kills?: number;
  } | null>(null);
  // 未読バトル結果モーダル用キュー
  const [unreadQueue, setUnreadQueue] = useState<BattleResult[]>([]);
  const [currentUnreadBattle, setCurrentUnreadBattle] = useState<BattleResult | null>(null);
  const unreadShownRef = useRef(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showEntryModal, setShowEntryModal] = useState(false);
  const [onboardingState, setOnboardingState] = useState<OnboardingState>("NOT_STARTED");
  const [showStarterSelection, setShowStarterSelection] = useState(false);
  const [starterSelectionLoading, setStarterSelectionLoading] = useState(false);

  // スターター選択モーダルの表示判定
  useEffect(() => {
    if (!isLoaded || !isSignedIn || pilotLoading) return;

    // パイロットが存在しない場合のみスターター選択を表示
    if (pilotError && !pilot) {
      setShowStarterSelection(true);
    } else if (pilot) {
      // パイロットが存在する場合はモーダルを非表示
      setShowStarterSelection(false);
    }
  }, [isLoaded, isSignedIn, pilot, pilotLoading, pilotError]);

  // ログイン成功時にSWRキャッシュを強制更新
  const prevIsSignedInRef = useRef<boolean | undefined>(undefined);
  useEffect(() => {
    if (isLoaded && isSignedIn && prevIsSignedInRef.current !== true) {
      mutateMobileSuits();
      mutatePilot();
      mutateUnreadBattles();
    }
    prevIsSignedInRef.current = isSignedIn;
  }, [isLoaded, isSignedIn, mutateMobileSuits, mutatePilot, mutateUnreadBattles]);

  // ログイン時に未読バトル結果をキューに積む
  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    if (!unreadBattles || unreadBattles.length === 0) return;
    if (unreadShownRef.current) return;

    unreadShownRef.current = true;
    setUnreadQueue([...unreadBattles]);
  }, [isLoaded, isSignedIn, unreadBattles]);

  // 未読キューから次の結果を表示
  useEffect(() => {
    if (unreadQueue.length > 0 && !currentUnreadBattle && !showResultModal) {
      const [next, ...rest] = unreadQueue;
      setCurrentUnreadBattle(next);
      setUnreadQueue(rest);
      const rewardsFromBattle: BattleRewards | null =
        next.exp_gained !== undefined
          ? {
              exp_gained: next.exp_gained ?? 0,
              credits_gained: next.credits_gained ?? 0,
              level_before: next.level_before ?? 0,
              level_after: next.level_after ?? 0,
              total_exp: 0,
              total_credits: 0,
            }
          : null;
      setModalResult({
        winLoss: next.win_loss,
        rewards: rewardsFromBattle,
        msSnapshot: (next.ms_snapshot as MobileSuit | null) ?? null,
        kills: next.kills,
      });
      setShowResultModal(true);
    }
  }, [unreadQueue, currentUnreadBattle, showResultModal]);

  // オンボーディングの表示判定
  useEffect(() => {
    if (!isLoaded || !isSignedIn || mobileSuitsLoading || battlesLoading || pilotLoading) return;

    // localStorage からオンボーディング完了状態を確認
    const onboardingCompleted =
      typeof window !== "undefined" &&
      localStorage.getItem(ONBOARDING_COMPLETED_KEY) === "true";

    // 初回ユーザー判定: 機体が1機以下（スターターのみ）でバトル履歴がない
    const isFirstTimeUser =
      mobileSuits &&
      mobileSuits.length <= 1 &&
      battles &&
      battles.length === 0;

    if (isFirstTimeUser && !onboardingCompleted) {
      setShowOnboarding(true);
      setOnboardingState("NOT_STARTED");
    } else if (onboardingCompleted) {
      setOnboardingState("COMPLETED");
    }
  }, [isLoaded, isSignedIn, mobileSuits, mobileSuitsLoading, battles, battlesLoading, pilotLoading]);

  const handleOnboardingComplete = () => {
    if (onboardingState === "NOT_STARTED") {
      // 最初のチュートリアル（バトル開始まで）が完了
      setShowOnboarding(false);
      setOnboardingState("BATTLE_STARTED");
    } else if (onboardingState === "BATTLE_FINISHED") {
      // バトル後のチュートリアル完了
      setShowOnboarding(false);
      setOnboardingState("COMPLETED");
      if (typeof window !== "undefined") {
        localStorage.setItem(ONBOARDING_COMPLETED_KEY, "true");
      }
    }
  };

  const handleStarterSelection = async (unitId: "zaku_ii" | "gm") => {
    setStarterSelectionLoading(true);
    try {
      // パイロットを作成
      await createPilot("New Pilot", unitId);
      // パイロット情報と機体情報を再取得
      await mutatePilot();
      await mutateMobileSuits();
      // スターター選択モーダルを閉じる
      setShowStarterSelection(false);
      // オンボーディングを開始
      setShowOnboarding(true);
      setOnboardingState("NOT_STARTED");
    } catch (error) {
      console.error("Error creating pilot:", error);
      alert(`パイロット作成に失敗しました: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setStarterSelectionLoading(false);
    }
  };

  // カウントダウンタイマー用の次回バトル時刻を計算
  const getNextBattleTime = (): Date | null => {
    if (!entryStatus?.next_room?.scheduled_at) return null;
    return new Date(entryStatus.next_room.scheduled_at);
  };

  // シミュレーション実行時に結果モーダルを表示
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
  }, [winLoss, rewards, playerData]);


  const startBattle = async (missionId: number) => {
    setIsLoading(true);
    setLogs([]);
    setWinner(null);
    setWinLoss(null);
    setCurrentTurn(0);
    setRewards(null);

    try {
      const token = await getToken();
      const headers: HeadersInit = {
        "Content-Type": "application/json",
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      // ミッション情報を取得して環境を設定
      const selectedMission = missions?.find(m => m.id === missionId);
      if (selectedMission?.environment) {
        setCurrentEnvironment(selectedMission.environment);
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

      // 報酬情報をセット
      if (data.rewards) {
        setRewards(data.rewards);
        // パイロット情報を再取得
        mutatePilot();
      }

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

    // 機体が1機のみの場合は即座にエントリー
    if (mobileSuits.length === 1) {
      await executeEntry(mobileSuits[0].id);
    } else {
      // 複数機体がある場合はモーダルを表示
      setShowEntryModal(true);
    }
  };

  const executeEntry = async (mobileSuitId: string) => {
    setEntryLoading(true);
    try {
      await entryBattle(mobileSuitId);
      // エントリー状況を再取得
      await mutateEntryStatus();
      // エントリー数を再取得
      await mutateEntryCount();
      // alert("エントリーが完了しました！");
      // モーダルを閉じる
      setShowEntryModal(false);
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
      // エントリー数を再取得
      await mutateEntryCount();
      // alert("エントリーをキャンセルしました。");
    } catch (error) {
      console.error("Error cancelling entry:", error);
      alert(`キャンセルに失敗しました: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setEntryLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#050505] text-[#00ff41] p-4 sm:p-6 md:p-8 font-mono">
      <div className="max-w-4xl mx-auto">

        {/* Battle Result Display */}
        {winLoss && (
          <div className="mb-4 sm:mb-8 text-center">
            <SciFiPanel
              variant={winLoss === "WIN" ? "primary" : winLoss === "LOSE" ? "secondary" : "accent"}
              chiseled={true}
            >
              <div className="px-6 sm:px-12 py-4 sm:py-6 text-2xl sm:text-4xl font-bold animate-pulse">
                {winLoss === "WIN" && "★ MISSION COMPLETE ★"}
                {winLoss === "LOSE" && "✕ MISSION FAILED ✕"}
                {winLoss === "DRAW" && "- DRAW -"}
              </div>
            </SciFiPanel>
          </div>
        )}

        {/* Rewards Display */}
        {rewards && (
          <SciFiPanel variant="secondary" className="mb-4 sm:mb-8">
            <div className="p-4 sm:p-6">
              <SciFiHeading level={2} variant="secondary" className="mb-4 text-xl sm:text-2xl">
                獲得報酬
              </SciFiHeading>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-[#0a0a0a]/70 p-3 sm:p-4 border-2 border-[#00ff41]/30">
                  <p className="text-xs sm:text-sm text-[#00ff41]/60 mb-2">経験値</p>
                  <p className="text-2xl sm:text-3xl font-bold text-[#00ff41]">+{rewards.exp_gained}</p>
                  <p className="text-xs text-[#00ff41]/50 mt-2">
                    累積: {rewards.total_exp} EXP
                  </p>
                </div>
                <div className="bg-[#0a0a0a]/70 p-3 sm:p-4 border-2 border-[#ffb000]/30">
                  <p className="text-xs sm:text-sm text-[#ffb000]/60 mb-2">クレジット</p>
                  <p className="text-2xl sm:text-3xl font-bold text-[#ffb000]">+{rewards.credits_gained.toLocaleString()}</p>
                  <p className="text-xs text-[#ffb000]/50 mt-2">
                    所持金: {rewards.total_credits.toLocaleString()} CR
                  </p>
                </div>
              </div>
              {rewards.level_after > rewards.level_before && (
                <div className="mt-4 p-3 sm:p-4 bg-[#ffb000]/20 border-2 border-[#ffb000] animate-pulse">
                  <p className="text-center text-lg sm:text-xl font-bold text-[#ffb000]">
                    🎉 LEVEL UP! Lv.{rewards.level_before} → Lv.{rewards.level_after} 🎉
                  </p>
                </div>
              )}
            </div>
          </SciFiPanel>
        )}

        {/* 3D Viewer Area: ログがある時だけ表示 */}
        {logs.length > 0 && playerData && enemiesData.length > 0 && (
          <div className="mb-4 sm:mb-8">
            <SciFiHeading level={2} className="mb-4 text-xl sm:text-2xl" variant="accent">
              Tactical Monitor - {currentEnvironment}
            </SciFiHeading>

            {/* 3D Canvas Component */}
            <BattleViewer
              logs={logs}
              player={playerData}
              enemies={enemiesData}
              currentTurn={currentTurn}
              environment={currentEnvironment}
            />

            {/* Turn Controller */}
            <SciFiPanel variant="accent" className="mt-2">
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-4 p-3 sm:p-4">
                <div className="flex gap-2 sm:hidden">
                  <SciFiButton
                    onClick={() => setCurrentTurn(Math.max(0, currentTurn - 1))}
                    disabled={currentTurn <= 0}
                    variant="accent"
                    size="sm"
                    className="flex-1"
                  >
                    &lt; PREV
                  </SciFiButton>
                  <SciFiButton
                    onClick={() => setCurrentTurn(Math.min(maxTurn, currentTurn + 1))}
                    disabled={currentTurn >= maxTurn}
                    variant="accent"
                    size="sm"
                    className="flex-1"
                  >
                    NEXT &gt;
                  </SciFiButton>
                </div>
                <SciFiButton
                  onClick={() => setCurrentTurn(Math.max(0, currentTurn - 1))}
                  disabled={currentTurn <= 0}
                  variant="accent"
                  size="sm"
                  className="hidden sm:block"
                >
                  &lt; PREV
                </SciFiButton>

                <div className="flex-grow flex flex-col px-2 sm:px-4">
                  <input
                    type="range"
                    min="0"
                    max={maxTurn}
                    value={currentTurn}
                    onChange={(e) => setCurrentTurn(Number(e.target.value))}
                    className="w-full h-2 bg-[#0a0a0a] rounded-lg appearance-none cursor-pointer accent-[#00f0ff] touch-manipulation"
                  />
                  <div className="flex justify-between text-[10px] sm:text-xs mt-1 text-[#00f0ff]/60">
                    <span>Start</span>
                    <span>Turn: {currentTurn} / {maxTurn}</span>
                    <span>End</span>
                  </div>
                </div>

                <SciFiButton
                  onClick={() => setCurrentTurn(Math.min(maxTurn, currentTurn + 1))}
                  disabled={currentTurn >= maxTurn}
                  variant="accent"
                  size="sm"
                  className="hidden sm:block"
                >
                  NEXT &gt;
                </SciFiButton>
              </div>
            </SciFiPanel>
          </div>
        )}

        {/* Countdown Timer */}
        <div className="mb-4 sm:mb-8">
          <CountdownTimer targetTime={getNextBattleTime()} />
        </div>

        {/* Entry Dashboard */}
        <div className="mb-4 sm:mb-8 bg-gray-800 p-4 sm:p-6 rounded-lg border border-green-800">
          <h2 className="text-xl sm:text-2xl font-bold mb-4 border-l-4 border-green-500 pl-2">
            ENTRY / 出撃登録
          </h2>
          
          {!isSignedIn ? (
            <div className="text-yellow-400 p-4 border border-yellow-700 rounded bg-yellow-900/20">
              エントリーするにはログインが必要です
            </div>
          ) : entryStatusLoading ? (
            <p className="text-gray-400">エントリー状況を確認中...</p>
          ) : (
            <EntryDashboard
              isEntered={entryStatus?.is_entered || false}
              entryCount={entryCount}
              mobileSuit={
                entryStatus?.is_entered && mobileSuits
                  ? mobileSuits.find((ms) => ms.id === entryStatus.entry?.mobile_suit_id)
                  : undefined
              }
              onEntry={handleEntry}
              onCancel={handleCancelEntry}
              isLoading={entryLoading}
              disabled={!mobileSuits || mobileSuits.length === 0}
            />
          )}
        </div>

        {/* Battle Result Modal */}
        {showResultModal && modalResult && (
          <BattleResultModal
            winLoss={modalResult.winLoss}
            rewards={modalResult.rewards}
            msSnapshot={modalResult.msSnapshot}
            kills={modalResult.kills}
            onClose={async () => {
              setShowResultModal(false);
              // 未読バトル結果を既読にする（CONTINUEを押したタイミング）
              if (currentUnreadBattle) {
                try {
                  await markBattleAsRead(currentUnreadBattle.id);
                  await mutateUnreadBattles();
                } catch (e) {
                  console.error("Failed to mark battle as read:", e);
                }
                setCurrentUnreadBattle(null);
              }
              // 初回バトル終了後、オンボーディングを再開
              // onboardingState が BATTLE_STARTED の場合のみ再開（これは初回チュートリアル中のみ）
              if (onboardingState === "BATTLE_STARTED") {
                setOnboardingState("BATTLE_FINISHED");
                setShowOnboarding(true);
              }
            }}
          />
        )}

        {/* Entry Selection Modal */}
        {showEntryModal && mobileSuits && (
          <EntrySelectionModal
            mobileSuits={mobileSuits}
            onSelect={executeEntry}
            onCancel={() => setShowEntryModal(false)}
            isLoading={entryLoading}
          />
        )}

        {/* Starter Selection Modal */}
        {showStarterSelection && (
          <StarterSelectionModal
            onSelect={handleStarterSelection}
            isLoading={starterSelectionLoading}
          />
        )}

        {/* Onboarding Overlay */}
        <OnboardingOverlay
          show={showOnboarding}
          onComplete={handleOnboardingComplete}
          startStep={onboardingState === "BATTLE_FINISHED" ? 4 : 0}
        />

        {/* Mission Selection Panel (開発環境のみ表示) */}
        <DevSimulationPanel
          missions={missions}
          missionsLoading={missionsLoading}
          selectedMissionId={selectedMissionId}
          setSelectedMissionId={setSelectedMissionId}
          playerData={playerData}
          enemiesData={enemiesData}
          isLoading={isLoading}
          startBattle={startBattle}
        />

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
                  
                  // スタイルの構築
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
                  
                  // デフォルトスタイル
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
    </main>
  );
}