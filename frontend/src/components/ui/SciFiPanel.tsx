import { ReactNode } from "react";

interface SciFiPanelProps {
  children: ReactNode;
  className?: string;
  variant?: "primary" | "secondary" | "accent";
  scanline?: boolean;
  chiseled?: boolean;
}

export default function SciFiPanel({
  children,
  className = "",
  variant = "primary",
  scanline = true,
  chiseled = true,
}: SciFiPanelProps) {
  const variantClasses = {
    primary: "border-[#00ff41] sf-border-glow-green",
    secondary: "border-[#ffb000] sf-border-glow-amber",
    accent: "border-[#00f0ff] sf-border-glow-cyan",
  };

  const baseClasses = `
    relative
    bg-[#0a0a0a]/80
    backdrop-blur-sm
    border-2
    ${variantClasses[variant]}
    ${scanline ? "sf-scanline" : ""}
    ${chiseled ? "sf-chiseled" : "rounded-lg"}
    ${className}
  `.trim();

  return (
    <div className={baseClasses}>
      {children}
    </div>
  );
}
