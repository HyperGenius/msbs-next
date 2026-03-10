/* frontend/src/components/BottomNav.tsx */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useCallback, useEffect } from "react";

const mainNavItems = [
  { href: "/", label: "Home", icon: "🏠" },
  { href: "/garage", label: "Garage", icon: "🔧" },
  { href: "/shop", label: "Shop", icon: "🛒" },
  { href: "/history", label: "History", icon: "📜" },
];

const menuItems = [
  { href: "/team", label: "Team", icon: "👥" },
  { href: "/rankings", label: "Rankings", icon: "🏆" },
  { href: "/pilot", label: "Pilot", icon: "🧑‍✈️" },
];

/*
 * スマホ向けのボトムナビゲーションコンポーネント
 * - 主要なページへのクイックアクセスと、その他のページへのメニューを提供
 * - デスクトップでは表示されず、Headerのナビゲーションが使用される
 * - アクセシビリティを考慮し、キーボード操作やスクリーンリーダーに対応
*/
export default function BottomNav() {
  const pathname = usePathname();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") setIsMenuOpen(false);
  }, []);

  useEffect(() => {
    if (isMenuOpen) {
      document.addEventListener("keydown", handleKeyDown);
      return () => document.removeEventListener("keydown", handleKeyDown);
    }
  }, [isMenuOpen, handleKeyDown]);

  return (
    <>
      {/* Overlay to close menu on tap outside */}
      {isMenuOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          onClick={() => setIsMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Menu popup */}
      {isMenuOpen && (
        <div
          role="menu"
          aria-labelledby="bottom-nav-menu-button"
          className="fixed bottom-16 right-2 z-50 md:hidden bg-[#0a0a0a] border-2 border-[#00ff41]/50 p-1 min-w-[180px] sf-scanline"
        >          {menuItems.map(({ href, label, icon }) => (
            <Link
              key={href}
              href={href}
              role="menuitem"
              onClick={() => setIsMenuOpen(false)}
              className="flex items-center gap-3 py-2.5 px-4 text-sm font-mono text-[#00ff41]/70 hover:text-[#00ff41] hover:bg-[#00ff41]/10 transition-colors no-min-size"
            >
              <span className="text-base leading-none">{icon}</span>
              <span>{label}</span>
            </Link>
          ))}
        </div>
      )}

      {/* Bottom navigation bar */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-50 md:hidden bg-[#050505] border-t-2 border-[#00ff41]/30 font-mono"
        aria-label="Bottom navigation"
      >
        <div className="flex h-16">
          {mainNavItems.map(({ href, label, icon }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex flex-col items-center justify-center flex-1 gap-0.5 text-[10px] no-min-size transition-colors ${
                  isActive
                    ? "text-[#00ff41] border-t-2 border-[#00ff41]"
                    : "text-[#00ff41]/40 hover:text-[#00ff41]/70"
                }`}
              >
                <span className="text-lg leading-none">{icon}</span>
                <span>{label}</span>
              </Link>
            );
          })}

          {/* Menu toggle */}
          <button
            id="bottom-nav-menu-button"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className={`flex flex-col items-center justify-center flex-1 gap-0.5 text-[10px] no-min-size transition-colors ${
              isMenuOpen
                ? "text-[#00ff41] border-t-2 border-[#00ff41]"
                : "text-[#00ff41]/40 hover:text-[#00ff41]/70"
            }`}
            aria-label="メニューを開く"
            aria-expanded={isMenuOpen}
          >
            <span className="text-xl leading-none">≡</span>
            <span>Menu</span>
          </button>
        </div>
      </nav>
    </>
  );
}
