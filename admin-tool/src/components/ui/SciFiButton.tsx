import { ReactNode, ButtonHTMLAttributes } from "react";

interface SciFiButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: "primary" | "secondary" | "accent" | "danger";
  size?: "sm" | "md" | "lg";
}

export default function SciFiButton({
  children,
  variant = "primary",
  size = "md",
  className = "",
  disabled = false,
  ...props
}: SciFiButtonProps) {
  const variantClasses = {
    primary: disabled 
      ? "bg-gray-700 text-gray-500 border-gray-600" 
      : "bg-[#00ff41] text-black border-[#00ff41] hover:sf-glow-green hover:bg-[#00cc33]",
    secondary: disabled 
      ? "bg-gray-700 text-gray-500 border-gray-600" 
      : "bg-[#ffb000] text-black border-[#ffb000] hover:sf-glow-amber hover:bg-[#cc8800]",
    accent: disabled 
      ? "bg-gray-700 text-gray-500 border-gray-600" 
      : "bg-[#00f0ff] text-black border-[#00f0ff] hover:sf-glow-cyan hover:bg-[#00b8cc]",
    danger: disabled 
      ? "bg-gray-700 text-gray-500 border-gray-600" 
      : "bg-red-700 text-white border-red-500 hover:bg-red-600 hover:shadow-red-500/50",
  };

  const sizeClasses = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-6 py-3 text-base",
    lg: "px-8 py-4 text-lg",
  };

  const baseClasses = `
    font-bold
    font-mono
    border-2
    transition-all
    duration-200
    ${variantClasses[variant]}
    ${sizeClasses[size]}
    ${disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer"}
    ${className}
  `.trim();

  return (
    <button
      className={baseClasses}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
}
