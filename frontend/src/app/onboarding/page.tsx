/* frontend/src/app/onboarding/page.tsx */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { SciFiPanel, SciFiButton, SciFiHeading, SciFiInput } from "@/components/ui";
import { registerPilot } from "@/services/api";

type Faction = "FEDERATION" | "ZEON";

export default function OnboardingPage() {
  const router = useRouter();
  const [pilotName, setPilotName] = useState("");
  const [selectedFaction, setSelectedFaction] = useState<Faction | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!pilotName.trim() || pilotName.trim().length < 2 || pilotName.trim().length > 15) {
      setError("パイロット名は2〜15文字で入力してください");
      return;
    }

    if (!selectedFaction) {
      setError("勢力を選択してください");
      return;
    }

    setIsSubmitting(true);
    try {
      await registerPilot(pilotName.trim(), selectedFaction);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登録に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#050505] text-[#00ff41] flex items-center justify-center p-4 font-mono">
      <div className="w-full max-w-lg">
        <SciFiPanel variant="primary" chiseled>
          <div className="p-6 sm:p-8 space-y-8">
            <div className="text-center">
              <SciFiHeading level={1} variant="primary" className="text-2xl sm:text-3xl mb-2">
                PILOT REGISTRATION
              </SciFiHeading>
              <p className="text-[#00ff41]/60 text-sm">
                パイロット登録を完了してください
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* パイロット名入力 */}
              <div>
                <SciFiInput
                  label="パイロット名 / CALLSIGN"
                  variant="primary"
                  value={pilotName}
                  onChange={(e) => setPilotName(e.target.value)}
                  placeholder="例: Amuro Ray"
                  minLength={2}
                  maxLength={15}
                  disabled={isSubmitting}
                  helpText="2〜15文字で入力してください"
                />
              </div>

              {/* 勢力選択 */}
              <div className="space-y-3">
                <p className="text-sm font-bold font-mono text-[#00ff41]/80 uppercase tracking-wider">
                  勢力選択 / FACTION
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* 地球連邦軍 */}
                  <button
                    type="button"
                    onClick={() => setSelectedFaction("FEDERATION")}
                    disabled={isSubmitting}
                    className={`
                      relative p-4 border-2 text-left transition-all duration-200 font-mono
                      ${selectedFaction === "FEDERATION"
                        ? "border-[#00f0ff] bg-[#00f0ff]/10 text-[#00f0ff]"
                        : "border-[#00ff41]/30 bg-[#0a0a0a] text-[#00ff41]/60 hover:border-[#00f0ff]/60 hover:text-[#00f0ff]/80"
                      }
                      disabled:opacity-50 disabled:cursor-not-allowed
                    `}
                  >
                    {selectedFaction === "FEDERATION" && (
                      <span className="absolute top-2 right-2 text-[#00f0ff] text-xs">▶ SELECTED</span>
                    )}
                    <div className="text-lg font-bold mb-1">地球連邦軍</div>
                    <div className="text-xs opacity-80">Earth Federation Forces</div>
                    <div className="mt-2 text-xs opacity-60">
                      練習機: RGM-79T GM Trainer
                    </div>
                  </button>

                  {/* ジオン公国軍 */}
                  <button
                    type="button"
                    onClick={() => setSelectedFaction("ZEON")}
                    disabled={isSubmitting}
                    className={`
                      relative p-4 border-2 text-left transition-all duration-200 font-mono
                      ${selectedFaction === "ZEON"
                        ? "border-[#ff4400] bg-[#ff4400]/10 text-[#ff4400]"
                        : "border-[#00ff41]/30 bg-[#0a0a0a] text-[#00ff41]/60 hover:border-[#ff4400]/60 hover:text-[#ff4400]/80"
                      }
                      disabled:opacity-50 disabled:cursor-not-allowed
                    `}
                  >
                    {selectedFaction === "ZEON" && (
                      <span className="absolute top-2 right-2 text-[#ff4400] text-xs">▶ SELECTED</span>
                    )}
                    <div className="text-lg font-bold mb-1">ジオン公国軍</div>
                    <div className="text-xs opacity-80">Principality of Zeon</div>
                    <div className="mt-2 text-xs opacity-60">
                      練習機: MS-06T Zaku II Trainer
                    </div>
                  </button>
                </div>
                <p className="text-xs text-[#00ff41]/40">
                  ※ 両練習機の性能は完全に同一です。選択した勢力によってショップの品揃えが変わります。
                </p>
              </div>

              {/* エラーメッセージ */}
              {error && (
                <div className="border border-[#ff4400]/50 bg-[#ff4400]/10 p-3 text-[#ff4400] text-sm">
                  {error}
                </div>
              )}

              {/* 登録ボタン */}
              <SciFiButton
                type="submit"
                variant="primary"
                size="lg"
                disabled={isSubmitting || !pilotName.trim() || !selectedFaction}
                className="w-full"
              >
                {isSubmitting ? "登録中..." : "▶ 出撃準備完了 / DEPLOY"}
              </SciFiButton>
            </form>
          </div>
        </SciFiPanel>
      </div>
    </main>
  );
}
