"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useSignUp, useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  SciFiPanel,
  SciFiHeading,
  SciFiInput,
  SciFiButton,
} from "@/components/ui";
import { registerPilot } from "@/services/api";
import backgroundsData from "@/data/backgrounds.json";
import { FactionCard } from "@/app/onboarding/_components/FactionCard";
import { BackgroundCard } from "@/app/onboarding/_components/BackgroundCard";
import { StatAllocationRow } from "@/app/onboarding/_components/StatAllocationRow";
import { ErrorBanner } from "@/app/onboarding/_components/ErrorBanner";
import type {
  Faction,
  Background,
  BonusAllocation,
  StatKey,
} from "@/app/onboarding/_types";

/* ── 定数 ─────────────────────────────────────────── */

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
const INITIAL_BONUS: BonusAllocation = {
  DEX: 0,
  INT: 0,
  REF: 0,
  TOU: 0,
  LUK: 0,
};

const FACTION_UNIT_NAME: Record<Faction, string> = {
  FEDERATION: "RGM-79T GM Trainer",
  ZEON: "MS-06T Zaku II Trainer",
};

/* ── 型 ───────────────────────────────────────────── */

type WizardPhase = 1 | 2 | 3 | 4 | 5;
type ThemeVariant = "secondary" | "accent";

/** テーマバリアントに対応する説明テキストの色クラスを返す */
function themeTextClass(v: ThemeVariant): string {
  return v === "accent" ? "text-[#00f0ff]/70" : "text-[#ffb000]/70";
}

/** テーマバリアントに対応するラベルテキストの色クラスを返す */
function themeLabelClass(v: ThemeVariant): string {
  return v === "accent" ? "text-[#00f0ff]/80" : "text-[#ffb000]/80";
}

/** テーマバリアントに対応するボーダー＋背景クラスを返す */
function themeBorderBgClass(v: ThemeVariant): string {
  return v === "accent"
    ? "border-[#00f0ff]/40 bg-[#00f0ff]/5"
    : "border-[#ffb000]/40 bg-[#ffb000]/5";
}

/* ── フェーズインジケーター ──────────────────────── */

const PHASE_LABELS = [
  "勢力選択",
  "連絡先入力",
  "認証確認",
  "パイロット申告",
  "入隊許可証",
];

function PhaseIndicator({
  currentPhase,
  variant,
}: {
  currentPhase: WizardPhase;
  variant: "primary" | "secondary" | "accent";
}) {
  const barColor: Record<string, string> = {
    primary: "bg-[#00ff41]",
    secondary: "bg-[#ffb000]",
    accent: "bg-[#00f0ff]",
  };
  const textColor: Record<string, string> = {
    primary: "text-[#00ff41]",
    secondary: "text-[#ffb000]",
    accent: "text-[#00f0ff]",
  };
  return (
    <div className="text-center">
      <div className="flex justify-center gap-1.5 mt-3">
        {[1, 2, 3, 4, 5].map((n) => (
          <div
            key={n}
            className={`h-1 w-12 transition-all duration-300 ${
              currentPhase >= n
                ? barColor[variant]
                : `${barColor[variant]} opacity-20`
            }`}
          />
        ))}
      </div>
      <p
        className={`${textColor[variant]} opacity-40 text-xs mt-2 font-mono`}
      >
        PHASE {currentPhase} / 5 — {PHASE_LABELS[currentPhase - 1]}
      </p>
    </div>
  );
}

/* ── メインウィザード ─────────────────────────────── */

export default function SignUpPage() {
  const { isLoaded, signUp, setActive } = useSignUp();
  const { isSignedIn } = useAuth();
  const router = useRouter();

  /** Phase 3 完了後にリダイレクトを抑止するフラグ */
  const completedAuthRef = useRef(false);

  const [phase, setPhase] = useState<WizardPhase>(1);
  const [faction, setFaction] = useState<Faction | null>(null);

  // Phase 2
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Phase 3
  const [otpCode, setOtpCode] = useState("");

  // Phase 4
  const [pilotName, setPilotName] = useState("");
  const [selectedBackground, setSelectedBackground] =
    useState<Background | null>(null);
  const [bonusAllocation, setBonusAllocation] =
    useState<BonusAllocation>(INITIAL_BONUS);

  // Phase 5
  const [enrollmentComplete, setEnrollmentComplete] = useState(false);
  const [enrollmentUnitName, setEnrollmentUnitName] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const remainingPoints =
    BONUS_POINTS_TOTAL -
    Object.values(bonusAllocation).reduce((a, b) => a + b, 0);

  /* テーマバリアント（勢力未選択時は accent） */
  const themeVariant: ThemeVariant =
    faction === "ZEON" ? "secondary" : "accent";

  /** リロードでPhase 3復帰した場合、Phase 1/2のステートが空のためBACKを禁止 */
  const resumedAtPhase3 = useRef(false);

  /* ── フォールバック ─────────────────────────────── */

  useEffect(() => {
    if (isLoaded && isSignedIn && !completedAuthRef.current) {
      router.replace("/onboarding");
    }
  }, [isLoaded, isSignedIn, router]);

  useEffect(() => {
    if (
      isLoaded &&
      signUp &&
      signUp.status === "missing_requirements" &&
      signUp.verifications?.emailAddress?.status === "unverified"
    ) {
      resumedAtPhase3.current = true;
      if (signUp.emailAddress) {
        setEmail(signUp.emailAddress);
      }
      setPhase(3);
    }
  }, [isLoaded, signUp]);

  /* ── Phase 1: 勢力選択 ─────────────────────────── */

  const handlePhase1Next = () => {
    setError(null);
    if (!faction) {
      setError("入隊先の勢力を選択してください");
      return;
    }
    setPhase(2);
  };

  /* ── Phase 2: メール・パスワード ────────────────── */

  const handlePhase2Submit = async () => {
    setError(null);
    if (!email.trim()) {
      setError("メールアドレスを入力してください");
      return;
    }
    if (!password || password.length < 8) {
      setError("パスワードは8文字以上で入力してください");
      return;
    }
    if (!signUp) return;

    setIsSubmitting(true);
    try {
      await signUp.create({ emailAddress: email, password });
      await signUp.prepareEmailAddressVerification({ strategy: "email_code" });
      setPhase(3);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "アカウント作成に失敗しました",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  /* ── Phase 3: OTP 検証 ─────────────────────────── */

  const handlePhase3Verify = async () => {
    setError(null);
    if (!otpCode.trim()) {
      setError("認証コードを入力してください");
      return;
    }
    if (!signUp || !setActive) return;

    setIsSubmitting(true);
    try {
      const result = await signUp.attemptEmailAddressVerification({
        code: otpCode,
      });
      if (result.status === "complete" && result.createdSessionId) {
        completedAuthRef.current = true;
        await setActive({ session: result.createdSessionId });
        setPhase(4);
      } else {
        setError("認証が完了しませんでした。もう一度お試しください。");
      }
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "認証コードの検証に失敗しました",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  /* ── Phase 4: パイロット情報 ────────────────────── */

  const handleBonusChange = (stat: StatKey, delta: number) => {
    const current = bonusAllocation[stat];
    const next = current + delta;
    if (next < 0) return;
    if (delta > 0 && remainingPoints <= 0) return;
    setBonusAllocation((prev) => ({ ...prev, [stat]: next }));
  };

  /* ── Phase 4 → 5: 入隊手続き送信 ───────────────── */

  const handlePhase4Submit = useCallback(async () => {
    setError(null);
    if (
      !pilotName.trim() ||
      pilotName.trim().length < 2 ||
      pilotName.trim().length > 15
    ) {
      setError("パイロット名は2〜15文字で入力してください");
      return;
    }
    if (!selectedBackground) {
      setError("経歴を選択してください");
      return;
    }
    if (remainingPoints !== 0) {
      setError(
        `ボーナスポイントを全て割り振ってください（残り ${remainingPoints} pt）`,
      );
      return;
    }
    if (!faction) return;

    setPhase(5);
    setIsSubmitting(true);
    try {
      await registerPilot(
        pilotName.trim(),
        faction,
        selectedBackground.id,
        {
          bonus_dex: bonusAllocation.DEX,
          bonus_int: bonusAllocation.INT,
          bonus_ref: bonusAllocation.REF,
          bonus_tou: bonusAllocation.TOU,
          bonus_luk: bonusAllocation.LUK,
        },
      );
      setEnrollmentUnitName(FACTION_UNIT_NAME[faction]);
      setEnrollmentComplete(true);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "入隊手続きに失敗しました",
      );
    } finally {
      setIsSubmitting(false);
    }
  }, [
    pilotName,
    selectedBackground,
    remainingPoints,
    faction,
    bonusAllocation,
  ]);

  /* ── ローディング画面 ──────────────────────────── */

  if (!isLoaded) {
    return (
      <main className="min-h-screen bg-[#050505] flex items-center justify-center font-mono">
        <p className="text-[#00ff41]/60 animate-pulse">LOADING SYSTEM...</p>
      </main>
    );
  }

  /* ── レンダー ──────────────────────────────────── */

  return (
    <main className="min-h-screen bg-[#050505] flex items-center justify-center px-4 py-12 font-mono">
      <div className="w-full max-w-2xl">
        <SciFiPanel
          variant={phase === 1 ? "accent" : themeVariant}
          chiseled
          className="p-6 sm:p-8"
        >
          <div className="space-y-8">
            {/* ─── ヘッダー ─── */}
            <div className="text-center">
              <SciFiHeading
                level={1}
                variant={phase === 1 ? "accent" : themeVariant}
                className="text-2xl sm:text-3xl mb-2 border-l-0 pl-0 text-center"
              >
                入隊手続き / ENLISTMENT
              </SciFiHeading>
              <PhaseIndicator
                currentPhase={phase}
                variant={phase === 1 ? "accent" : themeVariant}
              />
            </div>

            {/* ─── Phase 1: 勢力選択 ─── */}
            {phase === 1 && (
              <div className="space-y-6">
                <p className="text-[#00f0ff]/70 text-sm text-center">
                  入隊許可証提出先を選択してください
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <FactionCard
                    faction="FEDERATION"
                    label="地球連邦軍"
                    subLabel="Earth Federation Forces"
                    mobilesuit={FACTION_UNIT_NAME.FEDERATION}
                    isSelected={faction === "FEDERATION"}
                    onSelect={setFaction}
                  />
                  <FactionCard
                    faction="ZEON"
                    label="ジオン公国軍"
                    subLabel="Principality of Zeon"
                    mobilesuit={FACTION_UNIT_NAME.ZEON}
                    isSelected={faction === "ZEON"}
                    onSelect={setFaction}
                  />
                </div>

                <p className="text-xs text-[#00f0ff]/40">
                  ※
                  選択した勢力によってUIテーマカラーと初期配備機体が決まります。
                </p>

                <ErrorBanner message={error} />

                <div className="flex justify-end">
                  <SciFiButton
                    variant="accent"
                    size="lg"
                    onClick={handlePhase1Next}
                    disabled={!faction}
                  >
                    ▶ NEXT
                  </SciFiButton>
                </div>
              </div>
            )}

            {/* ─── Phase 2: メールアドレス・パスワード ─── */}
            {phase === 2 && (
              <div className="space-y-6">
                <p
                  className={`text-sm text-center ${themeTextClass(themeVariant)}`}
                >
                  連絡先と認証情報を入力してください
                </p>

                <SciFiInput
                  label="メールアドレス / EMAIL"
                  variant={themeVariant}
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="pilot@example.com"
                  disabled={isSubmitting}
                />

                <SciFiInput
                  label="パスワード / PASSWORD"
                  variant={themeVariant}
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  disabled={isSubmitting}
                  helpText="8文字以上で入力してください"
                />

                {/* Clerk Smart CAPTCHA マウントポイント（カスタムフロー用） */}
                <div id="clerk-captcha" />

                <ErrorBanner message={error} />

                <div className="flex gap-3">
                  <SciFiButton
                    variant="secondary"
                    size="lg"
                    onClick={() => {
                      setPhase(1);
                      setError(null);
                    }}
                    className="flex-1"
                  >
                    ◀ BACK
                  </SciFiButton>
                  <SciFiButton
                    variant={themeVariant}
                    size="lg"
                    onClick={handlePhase2Submit}
                    disabled={isSubmitting || !email.trim() || !password}
                    className="flex-1"
                  >
                    {isSubmitting ? "PROCESSING..." : "▶ SUBMIT"}
                  </SciFiButton>
                </div>
              </div>
            )}

            {/* ─── Phase 3: OTP 検証 ─── */}
            {phase === 3 && (
              <div className="space-y-6">
                <p
                  className={`text-sm text-center ${themeTextClass(themeVariant)}`}
                >
                  メールに送信された認証コードを入力してください
                </p>

                <SciFiInput
                  label="認証コード / VERIFICATION CODE"
                  variant={themeVariant}
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  placeholder="123456"
                  maxLength={6}
                  disabled={isSubmitting}
                />

                <ErrorBanner message={error} />

                <div className="flex gap-3">
                  {!resumedAtPhase3.current && (
                    <SciFiButton
                      variant="secondary"
                      size="lg"
                      onClick={() => {
                        setPhase(2);
                        setError(null);
                      }}
                      className="flex-1"
                    >
                      ◀ BACK
                    </SciFiButton>
                  )}
                  <SciFiButton
                    variant={themeVariant}
                    size="lg"
                    onClick={handlePhase3Verify}
                    disabled={isSubmitting || !otpCode.trim()}
                    className="flex-1"
                  >
                    {isSubmitting ? "VERIFYING..." : "▶ VERIFY"}
                  </SciFiButton>
                </div>
              </div>
            )}

            {/* ─── Phase 4: パイロット情報入力 ─── */}
            {phase === 4 && (
              <div className="space-y-6">
                <p
                  className={`text-sm text-center ${themeTextClass(themeVariant)}`}
                >
                  パイロット情報を入力してください
                </p>

                <SciFiInput
                  label="パイロット名 / CALLSIGN"
                  variant={themeVariant}
                  value={pilotName}
                  onChange={(e) => setPilotName(e.target.value)}
                  placeholder="例: Amuro Ray"
                  minLength={2}
                  maxLength={15}
                  helpText="2〜15文字で入力してください"
                />

                {/* 経歴選択 */}
                <div className="space-y-3">
                  <p
                    className={`text-sm font-bold uppercase tracking-wider font-mono ${themeLabelClass(themeVariant)}`}
                  >
                    経歴選択 / BACKGROUND
                  </p>
                  {BACKGROUNDS.map((bg) => (
                    <BackgroundCard
                      key={bg.id}
                      background={bg}
                      isSelected={selectedBackground?.id === bg.id}
                      onSelect={setSelectedBackground}
                    />
                  ))}
                </div>

                {/* ボーナスポイント割り振り */}
                <div className="space-y-3">
                  <p
                    className={`text-sm font-bold uppercase tracking-wider font-mono ${themeLabelClass(themeVariant)}`}
                  >
                    ボーナスポイント割り振り / BONUS ALLOCATION
                  </p>
                  <div className="flex justify-center">
                    <div
                      className={`border px-4 py-2 text-center flex items-center gap-2 ${themeBorderBgClass(themeVariant)}`}
                    >
                      <div className="text-xs opacity-60 pt-2">残り</div>
                      <div
                        className={`text-2xl font-bold ${
                          remainingPoints > 0
                            ? "text-[#ffb000]"
                            : themeLabelClass(themeVariant)
                        }`}
                      >
                        {remainingPoints} pt
                      </div>
                    </div>
                  </div>
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

                <ErrorBanner message={error} />

                <div className="flex gap-3">
                  <SciFiButton
                    variant="secondary"
                    size="lg"
                    onClick={() => {
                      setPhase(3);
                      setError(null);
                    }}
                    className="flex-1"
                  >
                    ◀ BACK
                  </SciFiButton>
                  <SciFiButton
                    variant={themeVariant}
                    size="lg"
                    onClick={handlePhase4Submit}
                    disabled={
                      !pilotName.trim() ||
                      !selectedBackground ||
                      remainingPoints !== 0
                    }
                    className="flex-1"
                  >
                    ▶ 入隊手続きを完了する
                  </SciFiButton>
                </div>
              </div>
            )}

            {/* ─── Phase 5: 入隊許可証 ─── */}
            {phase === 5 && (
              <div className="space-y-6 text-center">
                {!enrollmentComplete ? (
                  <div className="space-y-4 py-8">
                    <div className="text-4xl animate-pulse">⚙</div>
                    <p
                      className={`text-sm ${themeTextClass(themeVariant)}`}
                    >
                      入隊手続き処理中...
                    </p>
                    <p className="text-xs opacity-40">
                      PROCESSING ENLISTMENT REQUEST...
                    </p>
                    <ErrorBanner message={error} />
                    {error && (
                      <SciFiButton
                        variant={themeVariant}
                        size="md"
                        onClick={handlePhase4Submit}
                        disabled={isSubmitting}
                      >
                        再試行 / RETRY
                      </SciFiButton>
                    )}
                  </div>
                ) : (
                  <div className="space-y-6 py-4">
                    <div className="text-4xl mb-4 animate-bounce">🎖</div>
                    <SciFiHeading
                      level={2}
                      variant={themeVariant}
                      className="border-l-0 pl-0 text-center"
                    >
                      入隊許可
                    </SciFiHeading>
                    <p
                      className={`text-sm ${themeTextClass(themeVariant)}`}
                    >
                      ENLISTMENT APPROVED
                    </p>

                    {/* 入隊許可証（IDカード） */}
                    <div
                      className={`border-2 p-6 mx-auto max-w-sm space-y-3 transition-all duration-700 ${
                        faction === "FEDERATION"
                          ? "border-[#00f0ff] bg-[#00f0ff]/5"
                          : "border-[#ffb000] bg-[#ffb000]/5"
                      }`}
                    >
                      <div className="text-xs opacity-60 uppercase tracking-widest">
                        {faction === "FEDERATION"
                          ? "EARTH FEDERATION FORCES"
                          : "PRINCIPALITY OF ZEON"}
                      </div>
                      <div className="text-xl font-bold">{pilotName}</div>
                      <div className="border-t border-current/20 pt-2 mt-2">
                        <div className="text-xs opacity-60">
                          初期配備機体: {enrollmentUnitName}
                        </div>
                        <div className="text-xs opacity-60 mt-1">
                          STATUS: ACTIVE
                        </div>
                      </div>
                    </div>

                    <SciFiButton
                      variant={themeVariant}
                      size="lg"
                      onClick={() => router.push("/garage")}
                    >
                      ▶ ガレージへ進む / PROCEED TO GARAGE
                    </SciFiButton>
                  </div>
                )}
              </div>
            )}

            {/* ─── サインインリンク ─── */}
            {phase <= 2 && (
              <p className="text-center text-xs opacity-40">
                既にアカウントをお持ちですか？{" "}
                <Link
                  href="/sign-in"
                  className="underline hover:opacity-80"
                >
                  ログイン / SIGN IN
                </Link>
              </p>
            )}
          </div>
        </SciFiPanel>
      </div>
    </main>
  );
}
