/* frontend/src/hooks/useOnboarding.ts */
"use client";

import { useState, useEffect, useRef, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
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
  handleOnboardingComplete: () => void;
}

type OnboardingDecision = "SHOW" | "COMPLETED" | null;

// 同じタブでの書き込みでは storage イベントが発火しない。
// その場合は handleOnboardingComplete の setState による再描画で値を読み直す。
function subscribeStorage(onChange: () => void) {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function readOnboardingCompleted() {
  return localStorage.getItem(ONBOARDING_COMPLETED_KEY) === "true";
}

/**
 * オンボーディング（初回チュートリアル）に関するロジックを管理するフック。
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

  // パイロット未作成時は /onboarding へリダイレクト
  useEffect(() => {
    if (!isLoaded || !isSignedIn || pilotLoading) return;

    if (pilotNotFound && !pilot) {
      router.push("/onboarding");
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

  // オンボーディングの表示判定。判定結果が変わった描画で state に反映する。
  const onboardingCompleted = useSyncExternalStore(
    subscribeStorage,
    readOnboardingCompleted,
    () => false,
  );
  const isReady =
    isLoaded &&
    isSignedIn &&
    !mobileSuitsLoading &&
    !battlesLoading &&
    !pilotLoading;
  const isFirstTimeUser =
    !!mobileSuits &&
    mobileSuits.length <= 1 &&
    !!battles &&
    battles.length === 0;
  const onboardingDecision: OnboardingDecision = !isReady
    ? null
    : isFirstTimeUser && !onboardingCompleted
      ? "SHOW"
      : onboardingCompleted
        ? "COMPLETED"
        : null;

  const [prevDecision, setPrevDecision] = useState<OnboardingDecision>(null);
  if (onboardingDecision !== prevDecision) {
    setPrevDecision(onboardingDecision);
    if (onboardingDecision === "SHOW") {
      setShowOnboarding(true);
      setOnboardingState("NOT_STARTED");
    } else if (onboardingDecision === "COMPLETED") {
      setOnboardingState("COMPLETED");
    }
  }

  const handleOnboardingComplete = () => {
    setShowOnboarding(false);
    setOnboardingState("COMPLETED");
    if (typeof window !== "undefined") {
      localStorage.setItem(ONBOARDING_COMPLETED_KEY, "true");
    }
  };

  return {
    showOnboarding,
    setShowOnboarding,
    onboardingState,
    handleOnboardingComplete,
  };
}

