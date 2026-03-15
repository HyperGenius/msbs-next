import { SciFiButton } from "@/components/ui";

interface NavButtonsProps {
  onBack?: () => void;
  onNext?: () => void;
  onSubmit?: () => void;
  nextDisabled?: boolean;
  submitDisabled?: boolean;
  submitLabel?: string;
}

export function NavButtons({
  onBack,
  onNext,
  onSubmit,
  nextDisabled = false,
  submitDisabled = false,
  submitLabel = "▶ LET'S GO",
}: NavButtonsProps) {
  return (
    <div className="flex gap-3">
      {onBack && (
        <SciFiButton
          type="button"
          variant="secondary"
          size="lg"
          onClick={onBack}
          className="flex-1"
        >
          ◀ BACK
        </SciFiButton>
      )}
      {onNext && (
        <SciFiButton
          type="button"
          variant="primary"
          size="lg"
          onClick={onNext}
          disabled={nextDisabled}
          className="flex-1"
        >
          ▶ NEXT
        </SciFiButton>
      )}
      {onSubmit && (
        <SciFiButton
          type="button"
          variant="primary"
          size="lg"
          onClick={onSubmit}
          disabled={submitDisabled}
          className="flex-1"
        >
          {submitLabel}
        </SciFiButton>
      )}
    </div>
  );
}
