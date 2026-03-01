/* frontend/src/hooks/useUnreadBattleQueue.ts */
"use client";

import { useState, useEffect, useRef } from "react";
import { BattleResult, BattleRewards, MobileSuit } from "@/types/battle";

interface ModalResult {
  winLoss: "WIN" | "LOSE" | "DRAW";
  rewards: BattleRewards | null;
  msSnapshot?: MobileSuit | null;
  kills?: number;
}

interface UseUnreadBattleQueueOptions {
  isLoaded: boolean;
  isSignedIn: boolean | undefined;
  unreadBattles: BattleResult[] | undefined;
  showResultModal: boolean;
  setModalResult: (result: ModalResult | null) => void;
  setShowResultModal: (show: boolean) => void;
}

interface UseUnreadBattleQueueReturn {
  currentUnreadBattle: BattleResult | null;
  setCurrentUnreadBattle: (battle: BattleResult | null) => void;
}

/**
 * 未読バトル結果のキューイングとモーダル表示ロジックを管理するフック。
 * ログイン時に未読バトルをキューに積み、順番にモーダル表示する。
 */
export function useUnreadBattleQueue({
  isLoaded,
  isSignedIn,
  unreadBattles,
  showResultModal,
  setModalResult,
  setShowResultModal,
}: UseUnreadBattleQueueOptions): UseUnreadBattleQueueReturn {
  const [unreadQueue, setUnreadQueue] = useState<BattleResult[]>([]);
  const [currentUnreadBattle, setCurrentUnreadBattle] =
    useState<BattleResult | null>(null);
  const unreadShownRef = useRef(false);

  // ログイン時に未読バトル結果をキューに積む
  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    if (!unreadBattles || unreadBattles.length === 0) return;
    if (unreadShownRef.current) return;

    unreadShownRef.current = true;
    // unreadShownRef で一度だけ実行を保証するキュー初期化。意図的な setState-in-effect。
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUnreadQueue([...unreadBattles]);
  }, [isLoaded, isSignedIn, unreadBattles]);

  // 未読キューから次の結果を表示
  useEffect(() => {
    if (unreadQueue.length > 0 && !currentUnreadBattle && !showResultModal) {
      const [next, ...rest] = unreadQueue;
      // キューの先頭を取り出して順次モーダル表示するキュー処理。意図的な setState-in-effect。
      // eslint-disable-next-line react-hooks/set-state-in-effect
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
  }, [
    unreadQueue,
    currentUnreadBattle,
    showResultModal,
    setModalResult,
    setShowResultModal,
  ]);

  return { currentUnreadBattle, setCurrentUnreadBattle };
}
