import { ReactNode, KeyboardEvent } from "react";

interface SciFiCardProps {
  children: ReactNode;
  className?: string;
  variant?: "primary" | "secondary" | "accent";
  interactive?: boolean;
  onClick?: () => void;
}

export default function SciFiCard({
  children,
  className = "",
  variant = "primary",
  interactive = false,
  onClick,
}: SciFiCardProps) {
  const variantClasses = {
    primary: "border-[#00ff41]/50 hover:border-[#00ff41] hover:sf-border-glow-green",
    secondary: "border-[#ffb000]/50 hover:border-[#ffb000] hover:sf-border-glow-amber",
    accent: "border-[#00f0ff]/50 hover:border-[#00f0ff] hover:sf-border-glow-cyan",
  };

  const baseClasses = `
    relative
    p-6
    bg-[#0a0a0a]/60
    backdrop-blur-sm
    border-2
    sf-scanline
    transition-all
    duration-200
    ${variantClasses[variant]}
    ${interactive ? "cursor-pointer transform hover:scale-[1.02]" : ""}
    ${className}
  `.trim();

  // interactive + onClick の場合のみキーボード操作(Enter/Space)を有効にする。
  // e.target !== e.currentTarget の場合はカード内のネストしたボタン/Select等から
  // バブリングしてきたキー操作なので無視する（ネスト要素側の本来の挙動と二重発火させないため）
  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick?.();
    }
  };

  const interactiveProps =
    interactive && onClick
      ? { role: "button" as const, tabIndex: 0, onKeyDown: handleKeyDown }
      : {};

  return (
    <div className={baseClasses} onClick={onClick} {...interactiveProps}>
      {children}
    </div>
  );
}
