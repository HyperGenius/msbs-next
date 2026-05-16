"use client";

import Link from "next/link";
import {
  SciFiPanel,
  SciFiHeading,
  SciFiInput,
  SciFiButton,
} from "@/components/ui";
import { FactionCard } from "@/app/onboarding/_components/FactionCard";
import { BackgroundCard } from "@/app/onboarding/_components/BackgroundCard";
import { StatAllocationRow } from "@/app/onboarding/_components/StatAllocationRow";
import { ErrorBanner } from "@/app/onboarding/_components/ErrorBanner";
import { PhaseIndicator } from "./_components/PhaseIndicator";
import { useSignUpFlow } from "./_hooks/useSignUpFlow";
import {
  BACKGROUNDS,
  STAT_KEYS,
  STAT_DESCRIPTIONS,
  themeTextClass,
  themeLabelClass,
  themeBorderBgClass,
} from "./_constants";

export default function SignUpPage() {
  const {
    isLoaded,
    router,
    phase,
    setPhase,
    faction,
    setFaction,
    email,
    setEmail,
    username,
    setUsername,
    password,
    setPassword,
    otpCode,
    setOtpCode,
    pilotName,
    setPilotName,
    selectedBackground,
    setSelectedBackground,
    bonusAllocation,
    remainingPoints,
    enrollmentComplete,
    enrollmentUnitName,
    error,
    setError,
    isSubmitting,
    themeVariant,
    resumedAtPhase3,
    handlePhase1Next,
    handlePhase2Submit,
    handlePhase3Verify,
    handleBonusChange,
    handlePhase4Submit,
  } = useSignUpFlow();

  if (!isLoaded) {
    return (
      <main className="min-h-screen bg-[#050505] flex items-center justify-center font-mono">
        <p className="text-[#00ff41]/60 animate-pulse">LOADING SYSTEM...</p>
      </main>
    );
  }

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
                    mobilesuit="RGM-79T GM Trainer"
                    isSelected={faction === "FEDERATION"}
                    onSelect={setFaction}
                  />
                  <FactionCard
                    faction="ZEON"
                    label="ジオン公国軍"
                    subLabel="Principality of Zeon"
                    mobilesuit="MS-06T Zaku II Trainer"
                    isSelected={faction === "ZEON"}
                    onSelect={setFaction}
                  />
                </div>

                <p className="text-xs text-[#00f0ff]/40">
                  ※ 選択した勢力によってUIテーマカラーと初期配備機体が決まります。
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
                <p className={`text-sm text-center ${themeTextClass(themeVariant)}`}>
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
                  label="ユーザー名 / USERNAME"
                  variant={themeVariant}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="amuro_ray"
                  disabled={isSubmitting}
                  helpText="3〜32文字の半角英数字・アンダースコア・ハイフン"
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

                <div id="clerk-captcha" />

                <ErrorBanner message={error} />

                <div className="flex gap-3">
                  <SciFiButton
                    variant="secondary"
                    size="lg"
                    onClick={() => { setPhase(1); setError(null); }}
                    className="flex-1"
                  >
                    ◀ BACK
                  </SciFiButton>
                  <SciFiButton
                    variant={themeVariant}
                    size="lg"
                    onClick={handlePhase2Submit}
                    disabled={isSubmitting || !email.trim() || !username.trim() || !password}
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
                <p className={`text-sm text-center ${themeTextClass(themeVariant)}`}>
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
                      onClick={() => { setPhase(2); setError(null); }}
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
                <p className={`text-sm text-center ${themeTextClass(themeVariant)}`}>
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

                <div className="space-y-3">
                  <p className={`text-sm font-bold uppercase tracking-wider font-mono ${themeLabelClass(themeVariant)}`}>
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

                <div className="space-y-3">
                  <p className={`text-sm font-bold uppercase tracking-wider font-mono ${themeLabelClass(themeVariant)}`}>
                    ボーナスポイント割り振り / BONUS ALLOCATION
                  </p>
                  <div className="flex justify-center">
                    <div className={`border px-4 py-2 text-center flex items-center gap-2 ${themeBorderBgClass(themeVariant)}`}>
                      <div className="text-xs opacity-60 pt-2">残り</div>
                      <div className={`text-2xl font-bold ${remainingPoints > 0 ? "text-[#ffb000]" : themeLabelClass(themeVariant)}`}>
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
                    onClick={() => { setPhase(3); setError(null); }}
                    className="flex-1"
                  >
                    ◀ BACK
                  </SciFiButton>
                  <SciFiButton
                    variant={themeVariant}
                    size="lg"
                    onClick={handlePhase4Submit}
                    disabled={!pilotName.trim() || !selectedBackground || remainingPoints !== 0}
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
                    <p className={`text-sm ${themeTextClass(themeVariant)}`}>
                      入隊手続き処理中...
                    </p>
                    <p className="text-xs opacity-40">PROCESSING ENLISTMENT REQUEST...</p>
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
                    <p className={`text-sm ${themeTextClass(themeVariant)}`}>
                      ENLISTMENT APPROVED
                    </p>

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
                        <div className="text-xs opacity-60 mt-1">STATUS: ACTIVE</div>
                      </div>
                    </div>

                    <SciFiButton
                      variant={themeVariant}
                      size="lg"
                      onClick={() => router.push("/")}
                    >
                      ▶ ダッシュボードへ / GO TO DASHBOARD
                    </SciFiButton>
                  </div>
                )}
              </div>
            )}

            {/* ─── サインインリンク ─── */}
            {phase <= 2 && (
              <p className="text-center text-xs opacity-40">
                既にアカウントをお持ちですか？{" "}
                <Link href="/sign-in" className="underline hover:opacity-80">
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
