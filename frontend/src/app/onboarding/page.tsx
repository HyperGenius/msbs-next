/* frontend/src/app/onboarding/page.tsx */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { SciFiPanel, SciFiHeading, SciFiInput } from "@/components/ui";
import { registerPilot } from "@/services/api";
import backgroundsData from "@/data/backgrounds.json";

import type { Faction, Background, BonusAllocation, StatKey } from "./_types";
import { StepIndicator } from "./_components/StepIndicator";
import { ErrorBanner } from "./_components/ErrorBanner";
import { NavButtons } from "./_components/NavButtons";
import { FactionCard } from "./_components/FactionCard";
import { BackgroundCard } from "./_components/BackgroundCard";
import { StatAllocationRow } from "./_components/StatAllocationRow";

const BACKGROUNDS: Background[] = backgroundsData as Background[];
const BONUS_POINTS_TOTAL = 5;
const STAT_KEYS: StatKey[] = ["DEX", "INT", "REF", "TOU", "LUK"];

const STAT_DESCRIPTIONS: Record<StatKey, string> = {
  DEX: "器用 (DEX): 手先の器用さ",
  INT: "直感 (INT): 状況判断力",
  REF: "反応 (REF): 反射神経",
  TOU: "耐久 (TOU): 体力・頑丈さ",
  LUK: "幸運 (LUK): 運の良さ",
};

const INITIAL_BONUS: BonusAllocation = { DEX: 0, INT: 0, REF: 0, TOU: 0, LUK: 0 };

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3>(1);

  // Step 1
  const [pilotName, setPilotName] = useState("");
  const [selectedFaction, setSelectedFaction] = useState<Faction | null>(null);

  // Step 2
  const [selectedBackground, setSelectedBackground] = useState<Background | null>(null);

  // Step 3
  const [bonusAllocation, setBonusAllocation] = useState<BonusAllocation>(INITIAL_BONUS);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const remainingPoints =
    BONUS_POINTS_TOTAL - Object.values(bonusAllocation).reduce((a, b) => a + b, 0);

  const handleBonusChange = (stat: StatKey, delta: number) => {
    const current = bonusAllocation[stat];
    const next = current + delta;
    if (next < 0) return;
    if (delta > 0 && remainingPoints <= 0) return;
    setBonusAllocation((prev) => ({ ...prev, [stat]: next }));
  };

  const handleStep1Next = () => {
    setError(null);
    if (!pilotName.trim() || pilotName.trim().length < 2 || pilotName.trim().length > 15) {
      setError("パイロット名は2〜15文字で入力してください");
      return;
    }
    if (!selectedFaction) {
      setError("勢力を選択してください");
      return;
    }
    setStep(2);
  };

  const handleStep2Next = () => {
    setError(null);
    if (!selectedBackground) {
      setError("経歴を選択してください");
      return;
    }
    setStep(3);
  };

  const handleSubmit = async () => {
    setError(null);
    if (remainingPoints !== 0) {
      setError(`ボーナスポイントを全て割り振ってください（残り ${remainingPoints} pt）`);
      return;
    }
    if (!selectedFaction || !selectedBackground) return;

    setIsSubmitting(true);
    try {
      await registerPilot(pilotName.trim(), selectedFaction, selectedBackground.id, {
        bonus_dex: bonusAllocation.DEX,
        bonus_int: bonusAllocation.INT,
        bonus_ref: bonusAllocation.REF,
        bonus_tou: bonusAllocation.TOU,
        bonus_luk: bonusAllocation.LUK,
      });
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登録に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#050505] text-[#00ff41] flex items-center justify-center p-4 font-mono">
      <div className="w-full max-w-2xl">
        <SciFiPanel variant="primary" chiseled>
          <div className="p-6 sm:p-8 space-y-8">
            {/* ヘッダー */}
            <div className="text-center">
              <SciFiHeading level={1} variant="primary" className="text-2xl sm:text-3xl mb-2">
                PILOT REGISTRATION
              </SciFiHeading>
              <StepIndicator currentStep={step} />
            </div>

            {/* ── STEP 1: 勢力 & コールサイン ── */}
            {step === 1 && (
              <div className="space-y-6">
                <p className="text-[#00ff41]/70 text-sm text-center">勢力選択 &amp; コールサイン入力</p>

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

                <div className="space-y-3">
                  <p className="text-sm font-bold text-[#00ff41]/80 uppercase tracking-wider">
                    勢力選択 / FACTION
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <FactionCard
                      faction="FEDERATION"
                      label="地球連邦軍"
                      subLabel="Earth Federation Forces"
                      mobilesuit="RGM-79T GM Trainer"
                      isSelected={selectedFaction === "FEDERATION"}
                      onSelect={setSelectedFaction}
                    />
                    <FactionCard
                      faction="ZEON"
                      label="ジオン公国軍"
                      subLabel="Principality of Zeon"
                      mobilesuit="MS-06T Zaku II Trainer"
                      isSelected={selectedFaction === "ZEON"}
                      onSelect={setSelectedFaction}
                    />
                  </div>
                  <p className="text-xs text-[#00ff41]/40">
                    ※ 両練習機の性能は同一です。選択した勢力によってショップの品揃えが変わります。
                  </p>
                </div>

                <ErrorBanner message={error} />

                <NavButtons
                  onNext={handleStep1Next}
                  nextDisabled={!pilotName.trim() || !selectedFaction}
                />
              </div>
            )}

            {/* ── STEP 2: 経歴選択 ── */}
            {step === 2 && (
              <div className="space-y-6">
                <p className="text-[#00ff41]/70 text-md text-center">あなたの経歴を教えてください</p>

                <div className="space-y-4">
                  {BACKGROUNDS.map((bg) => (
                    <BackgroundCard
                      key={bg.id}
                      background={bg}
                      isSelected={selectedBackground?.id === bg.id}
                      onSelect={setSelectedBackground}
                    />
                  ))}
                </div>

                <ErrorBanner message={error} />

                <NavButtons
                  onBack={() => { setStep(1); setError(null); }}
                  onNext={handleStep2Next}
                  nextDisabled={!selectedBackground}
                />
              </div>
            )}

            {/* ── STEP 3: ボーナスポイント割り振り ── */}
            {step === 3 && selectedBackground && (
              <div className="space-y-6">
                <p className="text-[#00ff41]/70 text-sm text-center">ボーナスポイント割り振り</p>
                <div className="flex justify-center">
                  <div className="border border-[#00ff41]/40 bg-[#00ff41]/5 px-4 py-2 text-center flex items-center gap-2">
                    <div className="text-xs text-[#00ff41]/60 pt-2">残り</div>
                    <div className={`text-2xl font-bold ${remainingPoints > 0 ? "text-[#ffb000]" : "text-[#00ff41]"}`}>
                      {remainingPoints} pt
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  {STAT_KEYS.map((stat) => (
                    <StatAllocationRow
                      key={stat}
                      stat={stat}
                      description={STAT_DESCRIPTIONS[stat]}
                      bonus={bonusAllocation[stat]}
                      canDecrement={bonusAllocation[stat] > 0}
                      canIncrement={remainingPoints > 0}
                      onDecrement={() => handleBonusChange(stat, -1)}
                      onIncrement={() => handleBonusChange(stat, 1)}
                    />
                  ))}
                </div>

                <p className="text-xs text-[#00ff41]/40 text-center">
                  ※ ステータスはレベルアップ時にも成長します。初期配分はいつでも確認できます。
                </p>

                <ErrorBanner message={error} />

                <NavButtons
                  onBack={() => { setStep(2); setError(null); }}
                  onSubmit={handleSubmit}
                  submitDisabled={isSubmitting || remainingPoints !== 0}
                  submitLabel={isSubmitting ? "SUBMITTING..." : "SUBMIT!"}
                />
              </div>
            )}
          </div>
        </SciFiPanel>
      </div>
    </main>
  );
}

