"use client";

import { SignInButton, SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { usePilot } from "@/services/api";
import { SciFiButton, SciFiHeading } from "@/components/ui";

export default function Header() {
  const { pilot } = usePilot();

  return (
    <header className="mb-8 border-b-2 border-[#00ff41]/30 pb-4 sf-scanline">
      <div className="flex justify-between items-center">
        <div>
          <SciFiHeading level={1} className="text-2xl">
            MSBS-Next Simulator
          </SciFiHeading>
          <p className="text-sm text-[#00ff41]/60 font-mono ml-5">Phase 1: Prototype Environment</p>
        </div>
        <div className="flex items-center gap-3">
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
          <Link href="/team">
            <SciFiButton variant="accent" size="sm">Team</SciFiButton>
          </Link>
          <Link href="/history">
            <SciFiButton variant="secondary" size="sm">History</SciFiButton>
          </Link>
          <Link href="/rankings">
            <SciFiButton variant="secondary" size="sm">Rankings</SciFiButton>
          </Link>
          <Link href="/shop">
            <SciFiButton variant="accent" size="sm">Shop</SciFiButton>
          </Link>
          <Link href="/garage/engineering">
            <SciFiButton variant="accent" size="sm">Engineering</SciFiButton>
          </Link>
          <Link href="/garage">
            <SciFiButton variant="primary" size="sm">Open Hangar</SciFiButton>
          </Link>
          <SignedOut>
            <SignInButton mode="modal">
              <SciFiButton variant="accent" size="sm">Sign In</SciFiButton>
            </SignInButton>
          </SignedOut>
          <SignedIn>
            <UserButton 
              appearance={{
                elements: {
                  avatarBox: "w-10 h-10 border-2 border-[#00ff41]"
                }
              }}
            />
          </SignedIn>
        </div>
      </div>
    </header>
  );
}
