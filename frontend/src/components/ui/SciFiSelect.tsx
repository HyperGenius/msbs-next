"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

export interface SciFiSelectOption {
  value: string | number;
  label: string;
  description?: string;
}

interface SciFiSelectProps {
  label?: string;
  helpText?: string;
  variant?: "primary" | "secondary" | "accent";
  options: SciFiSelectOption[];
  value: string | number;
  onChange?: (value: string) => void;
  disabled?: boolean;
  /** トリガーボタンに付与する。幅や余白の上書きに使う */
  className?: string;
}

const VARIANT_CLASSES = {
  primary: {
    text: "text-[#00ff41]",
    trigger: "border-[#00ff41]/50 focus-visible:border-[#00ff41] focus-visible:sf-border-glow-green",
    popup: "border-[#00ff41]",
    active: "bg-[#00ff41]/15",
    selected: "text-[#00ff41]",
    rgb: "0,255,65",
  },
  secondary: {
    text: "text-[#ffb000]",
    trigger: "border-[#ffb000]/50 focus-visible:border-[#ffb000] focus-visible:sf-border-glow-amber",
    popup: "border-[#ffb000]",
    active: "bg-[#ffb000]/15",
    selected: "text-[#ffb000]",
    rgb: "255,176,0",
  },
  accent: {
    text: "text-[#00f0ff]",
    trigger: "border-[#00f0ff]/50 focus-visible:border-[#00f0ff] focus-visible:sf-border-glow-cyan",
    popup: "border-[#00f0ff]",
    active: "bg-[#00f0ff]/15",
    selected: "text-[#00f0ff]",
    rgb: "0,240,255",
  },
};

// リストの最大高さ（max-h-64）と同じ値。これだけ下に空きが無ければ上向きに開く
const POPUP_MAX_HEIGHT_PX = 256;

export default function SciFiSelect({
  label,
  helpText,
  variant = "primary",
  options,
  value,
  onChange,
  disabled = false,
  className = "",
}: SciFiSelectProps) {
  const baseId = useId();
  const labelId = `${baseId}-label`;
  const listId = `${baseId}-list`;
  const optionId = (index: number) => `${baseId}-opt-${index}`;

  const rootRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const [open, setOpen] = useState(false);
  const [openUpward, setOpenUpward] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  const styles = VARIANT_CLASSES[variant];
  const selectedIndex = options.findIndex((o) => String(o.value) === String(value));
  const selected = selectedIndex >= 0 ? options[selectedIndex] : undefined;

  const openList = () => {
    if (disabled) return;
    const rect = rootRef.current?.getBoundingClientRect();
    if (rect) {
      const spaceBelow = window.innerHeight - rect.bottom;
      setOpenUpward(spaceBelow < POPUP_MAX_HEIGHT_PX && rect.top > spaceBelow);
    }
    setActiveIndex(Math.max(selectedIndex, 0));
    setOpen(true);
  };

  const commit = (index: number) => {
    const option = options[index];
    if (option) onChange?.(String(option.value));
    setOpen(false);
  };

  useEffect(() => {
    if (!open) return;
    const handlePointerDown = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    listRef.current?.children[activeIndex]?.scrollIntoView({ block: "nearest" });
  }, [open, activeIndex]);

  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (disabled) return;
    const last = options.length - 1;
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        if (!open) openList();
        else setActiveIndex((i) => Math.min(i + 1, last));
        break;
      case "ArrowUp":
        e.preventDefault();
        if (!open) openList();
        else setActiveIndex((i) => Math.max(i - 1, 0));
        break;
      case "Home":
        if (open) {
          e.preventDefault();
          setActiveIndex(0);
        }
        break;
      case "End":
        if (open) {
          e.preventDefault();
          setActiveIndex(last);
        }
        break;
      case "Enter":
      case " ":
        e.preventDefault();
        if (open) commit(activeIndex);
        else openList();
        break;
      case "Escape":
        if (open) {
          e.preventDefault();
          setOpen(false);
        }
        break;
      case "Tab":
        setOpen(false);
        break;
    }
  };

  return (
    <div className="space-y-1">
      {label && (
        <label
          id={labelId}
          className="block text-sm font-bold font-mono text-[#00ff41]/80 uppercase tracking-wider"
        >
          {label}
        </label>
      )}
      <div ref={rootRef} className="relative">
        <button
          type="button"
          role="combobox"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-controls={listId}
          aria-labelledby={label ? labelId : undefined}
          aria-activedescendant={open ? optionId(activeIndex) : undefined}
          disabled={disabled}
          onClick={() => (open ? setOpen(false) : openList())}
          onKeyDown={handleKeyDown}
          className={`
            flex w-full min-h-11 items-center justify-between gap-2
            px-4 py-2 bg-[#0a0a0a] border-2 font-mono text-left
            transition-all duration-200 focus:outline-none
            disabled:opacity-50 disabled:cursor-not-allowed
            ${styles.text} ${styles.trigger} ${className}
          `.trim()}
        >
          <span className="truncate">{selected?.label ?? ""}</span>
          <svg
            aria-hidden="true"
            viewBox="0 0 12 8"
            className={`h-2 w-3 shrink-0 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
            fill="currentColor"
          >
            <path d="M0 0h12L6 8z" />
          </svg>
        </button>

        {open && (
          <ul
            ref={listRef}
            id={listId}
            role="listbox"
            aria-labelledby={label ? labelId : undefined}
            style={{ boxShadow: `0 0 12px rgba(${styles.rgb},0.25)` }}
            className={`
              absolute left-0 z-50 max-h-64 min-w-full w-max max-w-[min(32rem,calc(100vw-2rem))]
              overflow-y-auto bg-[#0a0a0a] border-2 font-mono
              ${styles.popup}
              ${openUpward ? "bottom-full mb-1" : "top-full mt-1"}
            `.trim()}
          >
            {options.map((option, index) => {
              const isSelected = index === selectedIndex;
              return (
                <li
                  key={option.value}
                  id={optionId(index)}
                  role="option"
                  aria-selected={isSelected}
                  onPointerEnter={() => setActiveIndex(index)}
                  // ボタンのフォーカスを保つため、押下時の blur を防ぐ
                  onPointerDown={(e) => e.preventDefault()}
                  onClick={() => commit(index)}
                  className={`
                    min-h-11 cursor-pointer px-4 py-2 border-b border-white/5 last:border-b-0
                    ${index === activeIndex ? styles.active : ""}
                    ${isSelected ? `${styles.selected} font-bold` : "text-gray-300"}
                  `.trim()}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-3 shrink-0 text-xs" aria-hidden="true">
                      {isSelected ? "▶" : ""}
                    </span>
                    <span>{option.label}</span>
                  </div>
                  {option.description && (
                    <p className="mt-0.5 pl-5 text-xs font-normal leading-relaxed text-gray-400">
                      {option.description}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
      {helpText && (
        <p className="text-xs text-[#00ff41]/60 font-mono">{helpText}</p>
      )}
    </div>
  );
}
