import { SelectHTMLAttributes } from "react";

interface SciFiSelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  helpText?: string;
  variant?: "primary" | "secondary" | "accent";
  options: { value: string | number; label: string }[];
}

export default function SciFiSelect({
  label,
  helpText,
  variant = "primary",
  options,
  className = "",
  ...props
}: SciFiSelectProps) {
  const variantClasses = {
    primary: "border-[#00ff41]/50 focus:border-[#00ff41] focus:sf-border-glow-green text-[#00ff41]",
    secondary: "border-[#ffb000]/50 focus:border-[#ffb000] focus:sf-border-glow-amber text-[#ffb000]",
    accent: "border-[#00f0ff]/50 focus:border-[#00f0ff] focus:sf-border-glow-cyan text-[#00f0ff]",
  };

  const baseSelectClasses = `
    w-full
    px-4
    py-2
    bg-[#0a0a0a]
    border-2
    font-mono
    transition-all
    duration-200
    focus:outline-none
    disabled:opacity-50
    disabled:cursor-not-allowed
    ${variantClasses[variant]}
    ${className}
  `.trim();

  return (
    <div className="space-y-1">
      {label && (
        <label className="block text-sm font-bold font-mono text-[#00ff41]/80 uppercase tracking-wider">
          {label}
        </label>
      )}
      <select className={baseSelectClasses} {...props}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {helpText && (
        <p className="text-xs text-[#00ff41]/60 font-mono">{helpText}</p>
      )}
    </div>
  );
}
