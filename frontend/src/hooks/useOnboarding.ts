/* frontend/src/hooks/useOnboarding.ts */
"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { createPilot } from "@/services/api";
import { MobileSuit, BattleResult, Pilot } from "@/types/battle";
import { ONBOARDING_COMPLETED_KEY, OnboardingState } from "@/constants";

interface UseOnboardingOptions {
  isLoaded: boolean;
  isSignedIn: boolean | undefined;
  pilot: Pilot | undefined;
  pilotLoading: boolean;
  pilotNotFound: boolean;
  mobileSuits: MobileSuit[] | undefined;
  mobileSuitsLoading: boolean;
  battles: BattleResult[] | undefined;
  battlesLoading: boolean;
  router: ReturnType<typeof useRouter>;
  mutatePilot: () => void;
  mutateMobileSuits: () => void;
  mutateUnreadBattles: () => void;
}

interface UseOnboardingReturn {
  showOnboarding: boolean;
  setShowOnboarding: (show: boolean) => void;
  onboardingState: OnboardingState;
  setOnboardingState: (state: OnboardingState) => void;
  showStarterSelection: boolean;
  starterSelectionLoading: boolean;
  handleOnboardingComplete: () => void;
  handleStarterSelection: (unitId: "zaku_ii" | "gm") => Promise<void>;
}

/**
 * オンボーディング（初回チュートリアル・スターター選択）に関するロジックを管理するフック。
 * パイロットが存在しない場合の /onboarding へのリダイレクト、
 * ログイン時の SWR キャッシュ強制更新も担う。
 */
export function useOnboarding({
  isLoaded,
  isSignedIn,
  pilot,
  pilotLoading,
  pilotNotFound,
  mobileSuits,
  mobileSuitsLoading,
  battles,
  battlesLoading,
  router,
  mutatePilot,
  mutateMobileSuits,
  mutateUnreadBattles,
}: UseOnboardingOptions): UseOnboardingReturn {
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingState, setOnboardingState] =
    useState<OnboardingState>("NOT_STARTED");
  const [showStarterSelection, setShowStarterSelection] = useState(false);
  const [starterSelectionLoading, setStarterSelectionLoading] = useState(false);

  // スターター選択モーダルの表示判定
  useEffect(() => {
    if (!isLoaded || !isSignedIn || pilotLoading) return;

    if (pilotNotFound && !pilot) {
      router.push("/onboarding");
    } else if (pilot) {
      setShowStarterSelection(false);
    }
  }, [isLoaded, isSignedIn, pilot, pilotLoading, pilotNotFound, router]);

  // ログイン成功時に SWR キャッシュを強制更新
  const prevIsSignedInRef = useRef<boolean | undefined>(undefined);
  useEffect(() => {
    if (isLoaded && isSignedIn && prevIsSignedInRef.current !== true) {
      mutateMobileSuits();
      mutatePilot();
      mutateUnreadBattles();
    }
    prevIsSignedInRef.current = isSignedIn;
  }, [isLoaded, isSignedIn, mutateMobileSuits, mutatePilot, mutateUnreadBattles]);

  // オンボーディングの表示判定
  useEffect(() => {
    if (
      !isLoaded ||
      !isSignedIn ||
      mobileSuitsLoading ||
      battlesLoading ||
      pilotLoading
    )
      return;

    const onboardingCompleted =
      typeof window !== "undefined" &&
      localStorage.getItem(ONBOARDING_COMPLETED_KEY) === "true";

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
  }, [
    isLoaded,
    isSignedIn,
    mobileSuits,
    mobileSuitsLoading,
    battles,
    battlesLoading,
    pilotLoading,
  ]);

  const handleOnboardingComplete = () => {
    if (onboardingState === "NOT_STARTED") {
      setShowOnboarding(false);
      setOnboardingState("BATTLE_STARTED");
    } else if (onboardingState === "BATTLE_FINISHED") {
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
      await createPilot("New Pilot", unitId);
      await mutatePilot();
      await mutateMobileSuits();
      setShowStarterSelection(false);
      setShowOnboarding(true);
      setOnboardingState("NOT_STARTED");
    } catch (error) {
      console.error("Error creating pilot:", error);
      alert(
        `パイロット作成に失敗しました: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    } finally {
      setStarterSelectionLoading(false);
    }
  };

  return {
    showOnboarding,
    setShowOnboarding,
    onboardingState,
    setOnboardingState,
    showStarterSelection,
    starterSelectionLoading,
    handleOnboardingComplete,
    handleStarterSelection,
  };
}
