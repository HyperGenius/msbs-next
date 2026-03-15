/* frontend/src/app/page.tsx */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { BattleRewards, MobileSuit } from "@/types/battle";
import {
  useMissions,
  useMobileSuits,
  useEntryStatus,
  useEntryCount,
  usePilot,
  useBattleHistory,
  useUnreadBattleResults,
  markBattleAsRead,
} from "@/services/api";
import BattleViewer from "@/components/BattleViewer";
import CountdownTimer from "@/components/Dashboard/CountdownTimer";
import EntryDashboard from "@/components/Dashboard/EntryDashboard";
import BattleResultModal from "@/components/Dashboard/BattleResultModal";
import EntrySelectionModal from "@/components/Dashboard/EntrySelectionModal";
import OnboardingOverlay from "@/components/Tutorial/OnboardingOverlay";
import { SciFiHeading } from "@/components/ui";
import DevSimulationPanel from "@/components/Dashboard/DevSimulationPanel";
import BattleResultAnnouncer from "@/components/Dashboard/BattleResultAnnouncer";
import RewardPanel from "@/components/Dashboard/RewardPanel";
import TurnController from "@/components/Dashboard/TurnController";
import { useOnboarding } from "@/hooks/useOnboarding";
import { useBattleSimulation } from "@/hooks/useBattleSimulation";
import { useUnreadBattleQueue } from "@/hooks/useUnreadBattleQueue";
import { useEntryAction } from "@/hooks/useEntryAction";

type ModalResult = {
  winLoss: "WIN" | "LOSE" | "DRAW";
  rewards: BattleRewards | null;
  msSnapshot?: MobileSuit | null;
  kills?: number;
};

export default function Home() {
  const router = useRouter();
  const { getToken, isSignedIn, isLoaded } = useAuth();
  const { missions, isLoading: missionsLoading } = useMissions();
  const { mobileSuits, isLoading: mobileSuitsLoading, mutate: mutateMobileSuits } = useMobileSuits();
  const { entryStatus, isLoading: entryStatusLoading, mutate: mutateEntryStatus } = useEntryStatus();
  const { entryCount, mutate: mutateEntryCount } = useEntryCount();
  const { pilot, isLoading: pilotLoading, isNotFound: pilotNotFound, mutate: mutatePilot } = usePilot();
  const { battles, isLoading: battlesLoading } = useBattleHistory(1);
  const { unreadBattles, mutate: mutateUnreadBattles } = useUnreadBattleResults();

  // バトル結果モーダルの状態（シミュレーション・未読キュー共通）
  const [showResultModal, setShowResultModal] = useState(false);
  const [modalResult, setModalResult] = useState<ModalResult | null>(null);

  const {
    showOnboarding,
    setShowOnboarding,
    onboardingState,
    setOnboardingState,
    handleOnboardingComplete,
  } = useOnboarding({
    isLoaded,
    isSignedIn,
    pilot,
    pilotLoading,
    pilotNotFound: pilotNotFound ?? false,
    mobileSuits,
    mobileSuitsLoading,
    battles,
    battlesLoading,
    router,
    mutatePilot,
    mutateMobileSuits,
    mutateUnreadBattles,
  });

  const {
    logs,
    isLoading,
    winner,
    winLoss,
    currentTurn,
    setCurrentTurn,
    maxTurn,
    selectedMissionId,
    setSelectedMissionId,
    playerData,
    enemiesData,
    rewards,
    currentEnvironment,
    startBattle,
  } = useBattleSimulation({
    getToken,
    missions,
    mutatePilot,
    setModalResult,
    setShowResultModal,
  });

  const { currentUnreadBattle, setCurrentUnreadBattle } = useUnreadBattleQueue({
    isLoaded,
    isSignedIn,
    unreadBattles,
    showResultModal,
    setModalResult,
    setShowResultModal,
  });

  const {
    entryLoading,
    showEntryModal,
    setShowEntryModal,
    handleEntry,
    executeEntry,
    handleCancelEntry,
  } = useEntryAction({ mobileSuits, mutateEntryStatus, mutateEntryCount });

  const getNextBattleTime = (): Date | null => {
    if (!entryStatus?.next_room?.scheduled_at) return null;
    return new Date(entryStatus.next_room.scheduled_at);
  };

  return (
    <main className="min-h-screen bg-[#050505] text-[#00ff41] p-4 sm:p-6 md:p-8 font-mono">
      <div className="max-w-4xl mx-auto">

        {/* Battle Result Announcer (WIN / LOSE / DRAW) */}
        <BattleResultAnnouncer winLoss={winLoss} />

        {/* Rewards Display */}
        <RewardPanel rewards={rewards} />

        {/* 3D Viewer Area: ログがある時だけ表示 */}
        {logs.length > 0 && playerData && enemiesData.length > 0 && (
          <div className="mb-4 sm:mb-8">
            <SciFiHeading level={2} className="mb-4 text-xl sm:text-2xl" variant="accent">
              Tactical Monitor - {currentEnvironment}
            </SciFiHeading>
            <BattleViewer
              logs={logs}
              player={playerData}
              enemies={enemiesData}
              currentTurn={currentTurn}
              environment={currentEnvironment}
            />
            <TurnController
              currentTurn={currentTurn}
              maxTurn={maxTurn}
              onTurnChange={setCurrentTurn}
            />
          </div>
        )}

        {/* Countdown Timer */}
        <div className="mb-4 sm:mb-6">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[#00ff41]/40 font-mono text-xs tracking-widest">{"// NEXT BATTLE"}</span>
            <div className="flex-1 h-px bg-[#00ff41]/20"></div>
          </div>
          <CountdownTimer targetTime={getNextBattleTime()} />
        </div>

        {/* Entry Dashboard */}
        <div className="mb-4 sm:mb-8">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[#00ff41]/40 font-mono text-xs tracking-widest">{"// CURRENT ENTRY"}</span>
            <div className="flex-1 h-px bg-[#00ff41]/20"></div>
          </div>
          {!isSignedIn ? (
            <div className="text-[#ffb000] p-4 border border-[#ffb000]/30 font-mono text-sm bg-[#0a0a0a]">
              エントリーするにはログインが必要です
            </div>
          ) : entryStatusLoading ? (
            <p className="text-[#00ff41]/50 font-mono text-sm">エントリー状況を確認中...</p>
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
              // 未読バトル結果を既読にする（CONTINUE を押したタイミング）
              if (currentUnreadBattle) {
                try {
                  await markBattleAsRead(currentUnreadBattle.id);
                  await mutateUnreadBattles();
                } catch (e) {
                  console.error("Failed to mark battle as read:", e);
                }
                setCurrentUnreadBattle(null);
              }
              // 初回バトル終了後、オンボーディングを再開（初回チュートリアル中のみ）
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

        {/* Onboarding Overlay */}
        <OnboardingOverlay
          show={showOnboarding}
          onComplete={handleOnboardingComplete}
          startStep={onboardingState === "BATTLE_FINISHED" ? 4 : 0}
        />

        {/* Mission Selection Panel & Text Log (開発環境のみ表示) */}
        <DevSimulationPanel
          missions={missions}
          missionsLoading={missionsLoading}
          selectedMissionId={selectedMissionId}
          setSelectedMissionId={setSelectedMissionId}
          playerData={playerData}
          enemiesData={enemiesData}
          isLoading={isLoading}
          startBattle={startBattle}
          logs={logs}
          currentTurn={currentTurn}
          winner={winner}
        />
      </div>
    </main>
  );
}