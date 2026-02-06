"use client";

import { SignInButton, SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { usePilot } from "@/services/api";

export default function Header() {
  const { pilot } = usePilot();

  return (
    <header className="mb-8 border-b border-green-700 pb-4">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">MSBS-Next Simulator</h1>
          <p className="text-sm opacity-70">Phase 1: Prototype Environment</p>
        </div>
        <div className="flex items-center gap-4">
          <SignedIn>
            {pilot && (
              <div className="px-4 py-2 bg-gray-800 rounded border border-green-700">
                <div className="flex gap-4 text-sm">
                  <div>
                    <span className="text-gray-400">Lv.</span>
                    <span className="text-yellow-400 font-bold ml-1">{pilot.level}</span>
                  </div>
                  <div className="border-l border-gray-600 pl-4">
                    <span className="text-gray-400">Credits:</span>
                    <span className="text-green-400 font-bold ml-1">{pilot.credits.toLocaleString()}</span>
                  </div>
                </div>
              </div>
            )}
          </SignedIn>
          <Link
            href="/history"
            className="px-6 py-3 bg-yellow-900 hover:bg-yellow-800 rounded font-bold transition-colors shadow-lg hover:shadow-yellow-500/50"
          >
            History
          </Link>
          <Link
            href="/shop"
            className="px-6 py-3 bg-blue-900 hover:bg-blue-800 rounded font-bold transition-colors shadow-lg hover:shadow-blue-500/50"
          >
            Shop
          </Link>
          <Link
            href="/garage/engineering"
            className="px-6 py-3 bg-purple-900 hover:bg-purple-800 rounded font-bold transition-colors shadow-lg hover:shadow-purple-500/50"
          >
            Engineering
          </Link>
          <Link
            href="/garage"
            className="px-6 py-3 bg-green-900 hover:bg-green-800 rounded font-bold transition-colors shadow-lg hover:shadow-green-500/50"
          >
            Open Hangar
          </Link>
          <SignedOut>
            <SignInButton mode="modal">
              <button className="px-6 py-3 bg-blue-900 hover:bg-blue-800 rounded font-bold transition-colors shadow-lg hover:shadow-blue-500/50">
                Sign In
              </button>
            </SignInButton>
          </SignedOut>
          <SignedIn>
            <UserButton 
              appearance={{
                elements: {
                  avatarBox: "w-10 h-10"
                }
              }}
            />
          </SignedIn>
        </div>
      </div>
    </header>
  );
}
