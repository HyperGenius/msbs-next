"use client";

import { useEffect } from "react";
import SciFiPanel from "./SciFiPanel";

interface SciFiModalProps {
  /** モーダルを開閉するフラグ */
  isOpen: boolean;
  /** オーバーレイまたは閉じるボタンをクリックしたときのコールバック */
  onClose: () => void;
  /** SciFiPanel のカラーバリアント */
  variant?: "primary" | "secondary" | "accent";
  /** モーダル幅の上限（Tailwind クラス, デフォルト: max-w-3xl） */
  maxWidthClass?: string;
  children: React.ReactNode;
}

/**
 * SF テーマの汎用モーダルシェル。
 * - モバイル: 画面下部からスライドアップするボトムシート
 * - sm以上: 画面中央に表示
 * - 内部コンテンツは max-h-[85dvh] + overflow-y-auto で独立スクロール
 * - Esc キーおよびオーバーレイクリックで閉じる
 */
export default function SciFiModal({
  isOpen,
  onClose,
  variant = "primary",
  maxWidthClass = "max-w-3xl",
  children,
}: SciFiModalProps) {
  /** Esc キーで閉じる */
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isOpen, onClose]);

  /** モーダルが開いている間はボディのスクロールを無効化する */
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className={`w-full ${maxWidthClass} mx-0 sm:mx-4 max-h-[85dvh] overflow-y-auto
          animate-in slide-in-from-bottom-4 sm:slide-in-from-bottom-0 duration-300`}
        onClick={(e) => e.stopPropagation()}
      >
        <SciFiPanel variant={variant} className="p-0">
          {children}
        </SciFiPanel>
      </div>
    </div>
  );
}
