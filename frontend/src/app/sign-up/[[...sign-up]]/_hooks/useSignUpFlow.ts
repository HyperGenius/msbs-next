"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useSignUp, useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { registerPilot } from "@/services/api";
import type { Background, BonusAllocation, StatKey } from "@/app/onboarding/_types";
import type { Faction } from "@/app/onboarding/_types";
import {
  BONUS_POINTS_TOTAL,
  INITIAL_BONUS,
  FACTION_UNIT_NAME,
  WizardPhase,
  ThemeVariant,
} from "../_constants";

/**
 * 入隊ウィザード全体の状態とイベントハンドラを管理するカスタムフック
 * Clerkの認証フローとパイロット登録APIをまとめて扱う
 */
export function useSignUpFlow() {
  const { isLoaded, signUp, setActive } = useSignUp();
  const { isSignedIn } = useAuth();
  const router = useRouter();

  /** Phase 3完了後にリダイレクトを抑止するフラグ（認証直後の誤リダイレクトを防ぐ） */
  const completedAuthRef = useRef(false);
  /** リロードでPhase 3に復帰した場合のフラグ（Phase 1/2のstateが空のためBACKを禁止する） */
  const resumedAtPhase3 = useRef(false);

  const [phase, setPhase] = useState<WizardPhase>(1);
  const [faction, setFaction] = useState<Faction | null>(null);

  // Phase 2: アカウント情報
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  // Phase 3: OTP認証コード
  const [otpCode, setOtpCode] = useState("");

  // Phase 4: パイロット情報
  const [pilotName, setPilotName] = useState("");
  const [selectedBackground, setSelectedBackground] = useState<Background | null>(null);
  const [bonusAllocation, setBonusAllocation] = useState<BonusAllocation>(INITIAL_BONUS);

  // Phase 5: 入隊完了状態
  const [enrollmentComplete, setEnrollmentComplete] = useState(false);
  const [enrollmentUnitName, setEnrollmentUnitName] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  /** 残りボーナスポイント数 */
  const remainingPoints =
    BONUS_POINTS_TOTAL - Object.values(bonusAllocation).reduce((a, b) => a + b, 0);

  /** 選択中の勢力に応じたUIテーマバリアント */
  const themeVariant: ThemeVariant = faction === "ZEON" ? "secondary" : "accent";

  /** サインイン済みかつClerk初期化完了の場合はオンボーディングにリダイレクト */
  useEffect(() => {
    if (isLoaded && isSignedIn && !completedAuthRef.current) {
      router.replace("/onboarding");
    }
  }, [isLoaded, isSignedIn, router]);

  /** メール認証待ち状態でリロードされた場合、Phase 3に自動復帰する */
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

  /** Phase 1: 勢力が選択されていることを確認してPhase 2へ進む */
  const handlePhase1Next = () => {
    setError(null);
    if (!faction) {
      setError("入隊先の勢力を選択してください");
      return;
    }
    setPhase(2);
  };

  /** Phase 2: Clerkでアカウントを作成しメール認証コードを送信してPhase 3へ進む */
  const handlePhase2Submit = async () => {
    setError(null);
    if (!email.trim()) {
      setError("メールアドレスを入力してください");
      return;
    }
    if (!username.trim()) {
      setError("ユーザー名を入力してください");
      return;
    }
    if (!/^[a-zA-Z0-9_-]{3,32}$/.test(username.trim())) {
      setError("ユーザー名は3〜32文字の半角英数字・アンダースコア・ハイフンで入力してください");
      return;
    }
    if (!password || password.length < 8) {
      setError("パスワードは8文字以上で入力してください");
      return;
    }
    if (!signUp) return;

    setIsSubmitting(true);
    try {
      await signUp.create({ emailAddress: email, username: username.trim(), password });
      await signUp.prepareEmailAddressVerification({ strategy: "email_code" });
      setPhase(3);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "アカウント作成に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  /** Phase 3: 入力されたOTPコードでメールアドレスを検証し、セッションを確立してPhase 4へ進む */
  const handlePhase3Verify = async () => {
    setError(null);
    if (!otpCode.trim()) {
      setError("認証コードを入力してください");
      return;
    }
    if (!signUp || !setActive) return;

    setIsSubmitting(true);
    try {
      const result = await signUp.attemptEmailAddressVerification({ code: otpCode });
      if (result.status === "complete") {
        completedAuthRef.current = true;
        if (result.createdSessionId) {
          await setActive({ session: result.createdSessionId });
        }
        setPhase(4);
      } else {
        setError("認証が完了しませんでした。もう一度お試しください。");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "認証コードの検証に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  /** Phase 4: ボーナスポイントのインクリメント/デクリメント処理 */
  const handleBonusChange = (stat: StatKey, delta: number) => {
    const current = bonusAllocation[stat];
    const next = current + delta;
    if (next < 0) return;
    if (delta > 0 && remainingPoints <= 0) return;
    setBonusAllocation((prev) => ({ ...prev, [stat]: next }));
  };

  /**
   * Phase 4→5: パイロット登録APIを呼び出し入隊手続きを完了させる
   * useCallbackでメモ化しているのはPhase 5の再試行ボタンから同じ関数を参照するため
   */
  const handlePhase4Submit = useCallback(async () => {
    setError(null);
    if (!pilotName.trim() || pilotName.trim().length < 2 || pilotName.trim().length > 15) {
      setError("パイロット名は2〜15文字で入力してください");
      return;
    }
    if (!selectedBackground) {
      setError("経歴を選択してください");
      return;
    }
    if (remainingPoints !== 0) {
      setError(`ボーナスポイントを全て割り振ってください（残り ${remainingPoints} pt）`);
      return;
    }
    if (!faction) return;

    setPhase(5);
    setIsSubmitting(true);
    try {
      await registerPilot(pilotName.trim(), faction, selectedBackground.id, {
        bonus_dex: bonusAllocation.DEX,
        bonus_int: bonusAllocation.INT,
        bonus_ref: bonusAllocation.REF,
        bonus_tou: bonusAllocation.TOU,
        bonus_luk: bonusAllocation.LUK,
      });
      setEnrollmentUnitName(FACTION_UNIT_NAME[faction]);
      setEnrollmentComplete(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "入隊手続きに失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  }, [pilotName, selectedBackground, remainingPoints, faction, bonusAllocation]);

  return {
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
  };
}
