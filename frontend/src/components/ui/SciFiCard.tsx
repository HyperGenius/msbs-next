import { ReactNode } from "react";

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

  return (
    <div className={baseClasses} onClick={onClick}>
      {children}
    </div>
  );
}
