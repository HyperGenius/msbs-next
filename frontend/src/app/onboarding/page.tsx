/* frontend/src/app/onboarding/page.tsx */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { SciFiPanel, SciFiButton, SciFiHeading, SciFiInput } from "@/components/ui";
import { registerPilot } from "@/services/api";
import backgroundsData from "@/data/backgrounds.json";

type Faction = "FEDERATION" | "ZEON";

interface Background {
  id: string;
  name: string;
  description: string;
  baseStats: { DEX: number; INT: number; REF: number; TOU: number };
}

const BACKGROUNDS: Background[] = backgroundsData as Background[];
const BONUS_POINTS_TOTAL = 5;

const STAT_DESCRIPTIONS: Record<string, string> = {
  DEX: "器用 (DEX): 命中率・距離減衰緩和・被ダメージカット",
  INT: "直感 (INT): クリティカル率・回避率",
  REF: "反応 (REF): イニシアチブ・機動性乗算",
  TOU: "耐久 (TOU): 攻撃ダメージ加算・被クリティカル率低下",
};

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3>(1);

  // Step 1
  const [pilotName, setPilotName] = useState("");
  const [selectedFaction, setSelectedFaction] = useState<Faction | null>(null);

  // Step 2
  const [selectedBackground, setSelectedBackground] = useState<Background | null>(null);

  // Step 3
  const [bonusAllocation, setBonusAllocation] = useState({ DEX: 0, INT: 0, REF: 0, TOU: 0 });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const remainingPoints =
    BONUS_POINTS_TOTAL - Object.values(bonusAllocation).reduce((a, b) => a + b, 0);

  const handleBonusChange = (stat: keyof typeof bonusAllocation, delta: number) => {
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
              <div className="flex justify-center gap-2 mt-3">
                {([1, 2, 3] as const).map((n) => (
                  <div
                    key={n}
                    className={`h-1 w-16 transition-all duration-300 ${
                      step >= n ? "bg-[#00ff41]" : "bg-[#00ff41]/20"
                    }`}
                  />
                ))}
              </div>
              <p className="text-[#00ff41]/40 text-xs mt-2">STEP {step} / 3</p>
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
                    <button
                      type="button"
                      onClick={() => setSelectedFaction("FEDERATION")}
                      className={`relative p-4 border-2 text-left transition-all duration-200 font-mono
                        ${selectedFaction === "FEDERATION"
                          ? "border-[#00f0ff] bg-[#00f0ff]/10 text-[#00f0ff]"
                          : "border-[#00ff41]/30 bg-[#0a0a0a] text-[#00ff41]/60 hover:border-[#00f0ff]/60 hover:text-[#00f0ff]/80"
                        }`}
                    >
                      {selectedFaction === "FEDERATION" && (
                        <span className="absolute top-2 right-2 text-[#00f0ff] text-xs">▶ SELECTED</span>
                      )}
                      <div className="text-lg font-bold mb-1">地球連邦軍</div>
                      <div className="text-xs opacity-80">Earth Federation Forces</div>
                      <div className="mt-2 text-xs opacity-60">練習機: RGM-79T GM Trainer</div>
                    </button>

                    <button
                      type="button"
                      onClick={() => setSelectedFaction("ZEON")}
                      className={`relative p-4 border-2 text-left transition-all duration-200 font-mono
                        ${selectedFaction === "ZEON"
                          ? "border-[#ff4400] bg-[#ff4400]/10 text-[#ff4400]"
                          : "border-[#00ff41]/30 bg-[#0a0a0a] text-[#00ff41]/60 hover:border-[#ff4400]/60 hover:text-[#ff4400]/80"
                        }`}
                    >
                      {selectedFaction === "ZEON" && (
                        <span className="absolute top-2 right-2 text-[#ff4400] text-xs">▶ SELECTED</span>
                      )}
                      <div className="text-lg font-bold mb-1">ジオン公国軍</div>
                      <div className="text-xs opacity-80">Principality of Zeon</div>
                      <div className="mt-2 text-xs opacity-60">練習機: MS-06T Zaku II Trainer</div>
                    </button>
                  </div>
                  <p className="text-xs text-[#00ff41]/40">
                    ※ 両練習機の性能は同一です。選択した勢力によってショップの品揃えが変わります。
                  </p>
                </div>

                {error && (
                  <div className="border border-[#ff4400]/50 bg-[#ff4400]/10 p-3 text-[#ff4400] text-sm">
                    {error}
                  </div>
                )}

                <SciFiButton
                  type="button"
                  variant="primary"
                  size="lg"
                  onClick={handleStep1Next}
                  disabled={!pilotName.trim() || !selectedFaction}
                  className="w-full"
                >
                  ▶ 次へ / NEXT
                </SciFiButton>
              </div>
            )}

            {/* ── STEP 2: 経歴選択 ── */}
            {step === 2 && (
              <div className="space-y-6">
                <p className="text-[#00ff41]/70 text-md text-center">あなたの経歴を教えてください</p>

                <div className="space-y-4">
                  {BACKGROUNDS.map((bg) => (
                    <button
                      key={bg.id}
                      type="button"
                      onClick={() => setSelectedBackground(bg)}
                      className={`w-full p-4 border-2 text-left transition-all duration-200 font-mono
                        ${selectedBackground?.id === bg.id
                          ? "border-[#00ff41] bg-[#00ff41]/10 text-[#00ff41]"
                          : "border-[#00ff41]/30 bg-[#0a0a0a] text-[#00ff41]/60 hover:border-[#00ff41]/60 hover:text-[#00ff41]/80"
                        }`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            {selectedBackground?.id === bg.id && (
                              <span className="text-[#00ff41] text-xs">▶</span>
                            )}
                            {/* 経歴名 */}
                            <span className="font-bold underline">{bg.name}</span>
                          </div>
                          {/* 経歴の説明 */}
                          <p className="text-sm opacity-70 leading-relaxed mb-3">{bg.description}</p>
                          {/* 各パラメータのボーナス値を表示する, 具体的すぎるため非表示 */}
                          {/* <div className="grid grid-cols-4 gap-2">
                            {(["DEX", "INT", "REF", "TOU"] as const).map((stat) => (
                              <div key={stat} className="text-center border border-current/30 p-1">
                                <div className="text-xs opacity-60">{stat}</div>
                                <div className="font-bold text-sm">{bg.baseStats[stat]}</div>
                              </div>
                            ))}
                          </div> */}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>

                {error && (
                  <div className="border border-[#ff4400]/50 bg-[#ff4400]/10 p-3 text-[#ff4400] text-sm">
                    {error}
                  </div>
                )}

                <div className="flex gap-3">
                  <SciFiButton
                    type="button"
                    variant="secondary"
                    size="lg"
                    onClick={() => { setStep(1); setError(null); }}
                    className="flex-1"
                  >
                    ◀ 戻る
                  </SciFiButton>
                  <SciFiButton
                    type="button"
                    variant="primary"
                    size="lg"
                    onClick={handleStep2Next}
                    disabled={!selectedBackground}
                    className="flex-1"
                  >
                    ▶ 次へ / NEXT
                  </SciFiButton>
                </div>
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
                  {(["DEX", "INT", "REF", "TOU"] as const).map((stat) => {
                    const base = selectedBackground.baseStats[stat];
                    const bonus = bonusAllocation[stat];
                    const total = base + bonus;
                    return (
                      <div key={stat} className="border border-[#00ff41]/20 bg-[#0a0a0a] p-3">
                        <div className="flex items-center justify-between mb-1">
                          {/* 項目と説明 */}
                          <div>
                            <span className="font-bold text-[#00ff41]">{stat}</span>
                            <span className="text-xs text-[#00ff41]/50 ml-2">
                              {STAT_DESCRIPTIONS[stat]}
                            </span>
                          </div>
                          {/* ボーナスポイント操作 */}
                          <div className="flex items-center gap-3">
                            <button
                              type="button"
                              onClick={() => handleBonusChange(stat, -1)}
                              disabled={bonus === 0}
                              className="w-7 h-7 border border-[#00ff41]/40 text-[#00ff41] disabled:opacity-30 hover:bg-[#00ff41]/10 transition-colors"
                            >
                              −
                            </button>
                            <div className="text-center min-w-[3rem]">
                              {/* パラメータ基本値 */}
                              {/* <span className="text-[#00ff41]/50 text-sm">{base}</span> */}
                              <span className="text-[#ffb000] text-sm"> +{bonus}</span>
                              {/* パラメータ合計値 */}
                              {/* <div className="text-lg font-bold text-[#00ff41]">{total}</div> */}
                            </div>
                            <button
                              type="button"
                              onClick={() => handleBonusChange(stat, 1)}
                              disabled={remainingPoints === 0}
                              className="w-7 h-7 border border-[#00ff41]/40 text-[#00ff41] disabled:opacity-30 hover:bg-[#00ff41]/10 transition-colors"
                            >
                              ＋
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                <p className="text-xs text-[#00ff41]/40 text-center">
                  ※ ステータスはレベルアップ時にも成長します。初期配分はいつでも確認できます。
                </p>

                {error && (
                  <div className="border border-[#ff4400]/50 bg-[#ff4400]/10 p-3 text-[#ff4400] text-sm">
                    {error}
                  </div>
                )}

                <div className="flex gap-3">
                  <SciFiButton
                    type="button"
                    variant="secondary"
                    size="lg"
                    onClick={() => { setStep(2); setError(null); }}
                    className="flex-1"
                  >
                    ◀ 戻る
                  </SciFiButton>
                  <SciFiButton
                    type="button"
                    variant="primary"
                    size="lg"
                    onClick={handleSubmit}
                    disabled={isSubmitting || remainingPoints !== 0}
                    className="flex-1"
                  >
                    {isSubmitting ? "登録中..." : "▶ 出撃準備完了 / DEPLOY"}
                  </SciFiButton>
                </div>
              </div>
            )}
          </div>
        </SciFiPanel>
      </div>
    </main>
  );
}

