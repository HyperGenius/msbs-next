"use client";

import { SignInButton, SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
import Link from "next/link";

export default function Header() {
  return (
    <header className="mb-8 border-b border-green-700 pb-4">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">MSBS-Next Simulator</h1>
          <p className="text-sm opacity-70">Phase 1: Prototype Environment</p>
        </div>
        <div className="flex items-center gap-4">
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
