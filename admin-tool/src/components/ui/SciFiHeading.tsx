import { ReactNode } from "react";

interface SciFiHeadingProps {
  children: ReactNode;
  level?: 1 | 2 | 3 | 4;
  className?: string;
  variant?: "primary" | "secondary" | "accent";
}

export default function SciFiHeading({
  children,
  level = 1,
  className = "",
  variant = "primary",
}: SciFiHeadingProps) {
  const variantClasses = {
    primary: "text-[#00ff41] border-[#00ff41]",
    secondary: "text-[#ffb000] border-[#ffb000]",
    accent: "text-[#00f0ff] border-[#00f0ff]",
  };

  const sizeClasses = {
    1: "text-3xl md:text-4xl",
    2: "text-2xl md:text-3xl",
    3: "text-xl md:text-2xl",
    4: "text-lg md:text-xl",
  };

  const baseClasses = `
    font-bold
    font-mono
    uppercase
    tracking-wider
    border-l-4
    pl-4
    ${variantClasses[variant]}
    ${sizeClasses[level]}
    ${className}
  `.trim();

  switch (level) {
    case 1:
      return <h1 className={baseClasses}>{children}</h1>;
    case 2:
      return <h2 className={baseClasses}>{children}</h2>;
    case 3:
      return <h3 className={baseClasses}>{children}</h3>;
    case 4:
      return <h4 className={baseClasses}>{children}</h4>;
    default:
      return <h1 className={baseClasses}>{children}</h1>;
  }
}
