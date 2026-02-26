"use client";

import { useState, useEffect, useCallback } from "react";
import { SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { usePilot } from "@/services/api";
import { SciFiButton, SciFiHeading } from "@/components/ui";

const navLinks = [
  { href: "/team", label: "Team", variant: "accent" as const },
  { href: "/history", label: "History", variant: "secondary" as const },
  { href: "/rankings", label: "Rankings", variant: "secondary" as const },
  { href: "/shop", label: "Shop", variant: "accent" as const },
  { href: "/garage", label: "Open Hangar", variant: "primary" as const },
];

export default function Header() {
  const { pilot } = usePilot();
  const [isOpen, setIsOpen] = useState(false);

  // Close mobile menu on Escape key
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") setIsOpen(false);
  }, []);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      return () => document.removeEventListener("keydown", handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);

  return (
    <header className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 pt-4 sm:pt-6 md:pt-8 mb-8 border-b-2 border-[#00ff41]/30 pb-4 sf-scanline font-mono">
      <div className="flex justify-between items-center">
        <div>
          <SciFiHeading level={1} className="text-2xl">
            MSBS-Next Simulator
          </SciFiHeading>
          <p className="text-sm text-[#00ff41]/60 font-mono ml-5">Phase 1: Prototype Environment</p>
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
            <UserButton 
              appearance={{
                elements: {
                  avatarBox: "w-10 h-10 border-2 border-[#00ff41]"
                }
              }}
            />
          </SignedIn>
        </div>

        {/* Mobile Menu Button */}
        <div className="flex items-center gap-3 md:hidden">
          <SignedOut>
            <Link href="/sign-in">
              <SciFiButton variant="accent" size="sm">Sign In</SciFiButton>
            </Link>
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
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="p-2 border-2 border-[#00ff41]/50 hover:border-[#00ff41] transition-colors"
            aria-label="Toggle navigation menu"
          >
            <svg className="w-6 h-6 text-[#00ff41]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Navigation Menu */}
      {isOpen && (
        <nav className="md:hidden mt-4 pt-4 border-t-2 border-[#00ff41]/20">
          <SignedIn>
            {pilot && (
              <Link
                href="/pilot"
                onClick={() => setIsOpen(false)}
                className="block mb-3 px-4 py-2 bg-[#0a0a0a] border-2 border-[#00ff41]/50 hover:border-[#00ff41] transition-all text-sm"
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
                    <span className="text-[#00ff41]/60">CR:</span>
                    <span className="text-[#00ff41] font-bold ml-1">{pilot.credits.toLocaleString()}</span>
                  </div>
                </div>
              </Link>
            )}
          </SignedIn>
          <div className="grid grid-cols-2 gap-2">
            {navLinks.map(({ href, label, variant }) => (
              <Link key={href} href={href} onClick={() => setIsOpen(false)}>
                <SciFiButton variant={variant} size="sm" className="w-full">{label}</SciFiButton>
              </Link>
            ))}
          </div>
        </nav>
      )}
    </header>
  );
}
