"use client";

import { useState, useEffect } from "react";
import { SciFiButton, SciFiPanel, SciFiHeading } from "@/components/ui";

interface OnboardingStep {
  title: string;
  message: string;
  targetSelector?: string; // CSS selector for highlighting
  position?: "top" | "bottom" | "left" | "right" | "center";
}

interface OnboardingOverlayProps {
  show: boolean;
  onComplete: () => void;
  startStep?: number; // Add option to start from a specific step
}

const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    title: "ようこそパイロット！",
    message:
      "新規登録ありがとうございます！あなたには初期機体として Zaku II (Starter) が配備されています。さっそくバトルの準備を始めましょう。",
    position: "center",
  },
  {
    title: "ステップ 1: ガレージ (Hangar)",
    message:
      "まず画面上部の [Hangar] リンクから、あなたの機体を確認しましょう。機体の性能やカスタマイズをチェックできます。",
    targetSelector: "a[href='/garage']",
    position: "bottom",
  },
  {
    title: "ステップ 2: バトルエントリー",
    message:
      "準備ができたらダッシュボードからバトルにエントリーしましょう。バトルは毎日21時に開催されます。",
    targetSelector: ".mission-selection-panel",
    position: "top",
  },
  {
    title: "ステップ 3: 報酬の獲得",
    message:
      "バトルが完了すると報酬を獲得できます。獲得したクレジットと経験値で機体を強化できます。",
    position: "center",
  },
  {
    title: "ステップ 4: Engineering へ",
    message:
      "画面上部のメニューから [Engineering] を開いて、機体の強化やカスタマイズを行いましょう。装備の購入や機体性能の向上が可能です。",
    targetSelector: "a[href='/garage/engineering']",
    position: "bottom",
  },
];

export default function OnboardingOverlay({
  show,
  onComplete,
  startStep = 0,
}: OnboardingOverlayProps) {
  const [currentStep, setCurrentStep] = useState(startStep);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (show) {
      setIsVisible(true);
      setCurrentStep(startStep); // Reset to the specified start step when showing
    }
  }, [show, startStep]);

  // Highlight target element based on current step
  useEffect(() => {
    if (!show || !isVisible) return;

    const step = ONBOARDING_STEPS[currentStep];
    if (!step.targetSelector) return;

    // Wait for element to be rendered
    const timeoutId = setTimeout(() => {
      const targetElement = document.querySelector(step.targetSelector!);
      if (targetElement) {
        targetElement.classList.add("tutorial-highlight");
      }
    }, 100);

    return () => {
      clearTimeout(timeoutId);
      // Remove highlight from any previously highlighted element
      const highlightedElements = document.querySelectorAll(".tutorial-highlight");
      highlightedElements.forEach((el) => {
        el.classList.remove("tutorial-highlight");
      });
    };
  }, [show, isVisible, currentStep]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      const highlightedElements = document.querySelectorAll(".tutorial-highlight");
      highlightedElements.forEach((el) => {
        el.classList.remove("tutorial-highlight");
      });
    };
  }, []);

  if (!show || !isVisible) return null;

  const step = ONBOARDING_STEPS[currentStep];
  const isLastStep = currentStep === ONBOARDING_STEPS.length - 1;

  const handleNext = () => {
    if (isLastStep) {
      setIsVisible(false);
      setTimeout(() => {
        onComplete();
      }, 300);
    } else {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleSkip = () => {
    setIsVisible(false);
    setTimeout(() => {
      onComplete();
    }, 300);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="max-w-2xl w-full mx-4">
        <SciFiPanel
          variant="primary"
          className={`transform transition-all duration-500 ${
            isVisible ? "scale-100 opacity-100" : "scale-75 opacity-0"
          }`}
        >
          <div className="p-8">
            {/* プログレスバー */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-[#00ff41]/60">
                  STEP {currentStep + 1} / {ONBOARDING_STEPS.length}
                </span>
                <button
                  onClick={handleSkip}
                  className="text-xs text-[#00ff41]/60 hover:text-[#00ff41] transition-colors"
                >
                  SKIP
                </button>
              </div>
              <div className="h-2 bg-[#0a0a0a] rounded-full overflow-hidden border border-[#00ff41]/30">
                <div
                  className="h-full bg-gradient-to-r from-[#00ff41] to-[#00cc33] transition-all duration-500"
                  style={{
                    width: `${
                      ((currentStep + 1) / ONBOARDING_STEPS.length) * 100
                    }%`,
                  }}
                />
              </div>
            </div>

            {/* コンテンツ */}
            <div className="mb-8">
              <SciFiHeading level={2} variant="primary" className="mb-4">
                {step.title}
              </SciFiHeading>
              <p className="text-[#00ff41]/80 text-lg leading-relaxed">
                {step.message}
              </p>
            </div>

            {/* ナビゲーションボタン */}
            <div className="flex gap-4">
              {currentStep > 0 && (
                <SciFiButton
                  onClick={() => setCurrentStep(currentStep - 1)}
                  variant="accent"
                  size="md"
                  className="flex-1"
                >
                  &lt; BACK
                </SciFiButton>
              )}
              <SciFiButton
                onClick={handleNext}
                variant="primary"
                size="md"
                className="flex-1"
              >
                {isLastStep ? "FINISH" : "NEXT >"}
              </SciFiButton>
            </div>

            {/* 装飾エフェクト */}
            <div className="mt-6 flex items-center justify-center gap-2">
              {ONBOARDING_STEPS.map((_, index) => (
                <div
                  key={index}
                  className={`h-2 w-2 rounded-full transition-all duration-300 ${
                    index === currentStep
                      ? "bg-[#00ff41] w-8"
                      : index < currentStep
                      ? "bg-[#00ff41]/50"
                      : "bg-[#00ff41]/20"
                  }`}
                />
              ))}
            </div>
          </div>
        </SciFiPanel>
      </div>
    </div>
  );
}
