/* frontend/src/components/Header.tsx */
"use client";

import { useCallback } from "react";
import { SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { usePilot, resetAccount } from "@/services/api";
import { SciFiButton, SciFiHeading } from "@/components/ui";
import { ONBOARDING_COMPLETED_KEY } from "@/constants";

const navLinks = [
  { href: "/team", label: "Team", variant: "accent" as const },
  { href: "/history", label: "History", variant: "secondary" as const },
  { href: "/rankings", label: "Rankings", variant: "secondary" as const },
  { href: "/shop", label: "Shop", variant: "accent" as const },
  { href: "/garage", label: "Hangar", variant: "primary" as const },
];

/*
 * ヘッダーコンポーネント
 * - サイトタイトルとサブタイトルを表示
*/
export default function Header() {
  const { pilot } = usePilot();
  const isDev = process.env.NODE_ENV === "development";

  const handleResetAccount = useCallback(async () => {
    if (!confirm("【デバッグ】アカウントを初期状態にリセットします。パイロット、機体、戦績が全て削除されます。よろしいですか？")) {
      return;
    }
    try {
      await resetAccount();
      localStorage.removeItem(ONBOARDING_COMPLETED_KEY);
      window.location.reload();
    } catch (e) {
      alert(`リセットに失敗しました: ${e instanceof Error ? e.message : String(e)}`);
    }
  }, []);

  return (
    <header className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 pt-4 sm:pt-6 md:pt-8 mb-8 border-b-2 border-[#00ff41]/30 pb-4 sf-scanline font-mono">
      <div className="flex justify-between items-center">
        <div>
          <Link href="/">
            <SciFiHeading level={1} className="text-2xl">
              MSBS-Next Simulator
            </SciFiHeading>
          </Link>
          {/* サブタイトル: デスクトップのみ表示 */}
          <p className="hidden md:block text-sm text-[#00ff41]/60 font-mono ml-5">
            Phase 1: Prototype Environment
          </p>
          {/* デバッグボタン */}
          {isDev && (
            <button
              onClick={handleResetAccount}
              className="mb-1 px-2 py-0.5 text-xs bg-red-900/50 text-red-400 border border-red-500/50 hover:bg-red-900 transition-colors"
            >
              [SYS_RESET]
            </button>
          )}
        </div>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-3">
          <SignedIn>
            {pilot && (
              <Link
                href="/pilot"
                className="px-4 py-2 bg-[#0a0a0a] border-2 border-[#00ff41]/50 hover:border-[#00ff41] hover:sf-border-glow-green transition-all font-mono text-sm"
              >
                <div className="flex gap-4">
                  <div>
                    <span className="text-[#00ff41]/60">LV.</span>
                    <span className="text-[#ffb000] font-bold ml-1">{pilot.level}</span>
                  </div>
                  <div className="border-l-2 border-[#00ff41]/30 pl-4">
                    <span className="text-[#00ff41]/60">SP:</span>
                    <span className="text-[#00f0ff] font-bold ml-1">{pilot.skill_points}</span>
                  </div>
                  <div className="border-l-2 border-[#00ff41]/30 pl-4">
                    <span className="text-[#00ff41]/60">CREDITS:</span>
                    <span className="text-[#00ff41] font-bold ml-1">{pilot.credits.toLocaleString()}</span>
                  </div>
                </div>
              </Link>
            )}
          </SignedIn>
          {navLinks.map(({ href, label, variant }) => (
            <Link key={href} href={href}>
              <SciFiButton variant={variant} size="sm">{label}</SciFiButton>
            </Link>
          ))}
          <SignedOut>
            <Link href="/sign-in">
              <SciFiButton variant="accent" size="sm">Sign In</SciFiButton>
            </Link>
          </SignedOut>
          <SignedIn>
            <div suppressHydrationWarning>
              <UserButton
                appearance={{
                  elements: {
                    avatarBox: "w-10 h-10 border-2 border-[#00ff41]"
                  }
                }}
              />
            </div>
          </SignedIn>
        </div>

        {/* Mobile: Profile/Sign In only (navigation is in BottomNav) */}
        <div className="flex items-center gap-3 md:hidden">
          <SignedOut>
            <Link href="/sign-in">
              <SciFiButton variant="accent" size="sm">Sign In</SciFiButton>
            </Link>
          </SignedOut>
          <SignedIn>
            <div suppressHydrationWarning>
              <UserButton
                appearance={{
                  elements: {
                    avatarBox: "w-10 h-10 border-2 border-[#00ff41]"
                  }
                }}
              />
            </div>
          </SignedIn>
        </div>
      </div>
    </header>
  );
}
