interface StepIndicatorProps {
  currentStep: 1 | 2 | 3;
  totalSteps?: number;
}

export function StepIndicator({ currentStep, totalSteps = 3 }: StepIndicatorProps) {
  return (
    <div className="text-center">
      <div className="flex justify-center gap-2 mt-3">
        {Array.from({ length: totalSteps }, (_, i) => i + 1).map((n) => (
          <div
            key={n}
            className={`h-1 w-16 transition-all duration-300 ${
              currentStep >= n ? "bg-[#00ff41]" : "bg-[#00ff41]/20"
            }`}
          />
        ))}
      </div>
      <p className="text-[#00ff41]/40 text-xs mt-2">
        STEP {currentStep} / {totalSteps}
      </p>
    </div>
  );
}
