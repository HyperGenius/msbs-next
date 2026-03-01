/* frontend/src/components/Dashboard/BattleResultAnnouncer.tsx */
import { SciFiPanel } from "@/components/ui";

interface BattleResultAnnouncerProps {
  winLoss: "WIN" | "LOSE" | "DRAW" | null;
}

/**
 * バトル結果（WIN / LOSE / DRAW）を大きく表示するアナウンスパネル。
 */
export default function BattleResultAnnouncer({
  winLoss,
}: BattleResultAnnouncerProps) {
  if (!winLoss) return null;

  return (
    <div className="mb-4 sm:mb-8 text-center">
      <SciFiPanel
        variant={
          winLoss === "WIN"
            ? "primary"
            : winLoss === "LOSE"
            ? "secondary"
            : "accent"
        }
        chiseled={true}
      >
        <div className="px-6 sm:px-12 py-4 sm:py-6 text-2xl sm:text-4xl font-bold animate-pulse">
          {winLoss === "WIN" && "★ MISSION COMPLETE ★"}
          {winLoss === "LOSE" && "✕ MISSION FAILED ✕"}
          {winLoss === "DRAW" && "- DRAW -"}
        </div>
      </SciFiPanel>
    </div>
  );
}
