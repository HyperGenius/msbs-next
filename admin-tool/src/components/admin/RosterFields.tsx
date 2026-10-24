"use client";

import { useState } from "react";
import { formatChangeValue } from "@/lib/localSim/rosterEdit";

const baseCls = "w-full bg-[#0a0a0a] border text-[#00ff41] px-2 py-1 text-sm font-mono focus:outline-none";
const normalCls = "border-[#00ff41]/30 focus:border-[#00ff41]";
// 元のロスターから変えた値。琥珀色の枠と「元: …」で示す。
const changedCls = "border-[#ffb000] bg-[#ffb000]/10 focus:border-[#ffb000]";

function ChangedHint({ original }: { original: unknown }) {
  return <span className="ml-1 text-[10px] text-[#ffb000]">元: {formatChangeValue(original)}</span>;
}

interface FieldShellProps {
  label: string;
  changed: boolean;
  original: unknown;
  children: React.ReactNode;
}

function FieldShell({ label, changed, original, children }: FieldShellProps) {
  return (
    <div>
      <label className="block text-xs text-[#ffb000]/80 mb-0.5">
        {label}
        {changed && <ChangedHint original={original} />}
      </label>
      {children}
    </div>
  );
}

interface NumberFieldProps {
  label: string;
  value: number;
  /** 元のロスターの値。無い（追加した機体）ときは undefined で、変更の強調をしない */
  original?: number;
  step?: string;
  onChange: (value: number) => void;
}

/** 数値の入力欄。空や数値でない入力は NaN にして、保存前の検証で弾く */
export function NumberField({ label, value, original, step = "1", onChange }: NumberFieldProps) {
  const [draft, setDraft] = useState(String(value));
  const parsed = draft.trim() === "" ? NaN : Number(draft);
  // 入力途中の文字列（"0." など）は、値が同じ間は書き換えない。
  const shown = Object.is(parsed, value) ? draft : Number.isNaN(value) ? "" : String(value);
  const changed = original !== undefined && !Object.is(original, value);
  return (
    <FieldShell label={label} changed={changed} original={original}>
      <input
        type="number"
        step={step}
        value={shown}
        onChange={(e) => {
          setDraft(e.target.value);
          onChange(e.target.value.trim() === "" ? NaN : Number(e.target.value));
        }}
        className={`${baseCls} ${changed ? changedCls : normalCls} ${Number.isFinite(value) ? "" : "border-red-400"}`}
      />
    </FieldShell>
  );
}

interface TextFieldProps {
  label: string;
  value: string;
  original?: string;
  placeholder?: string;
  onChange: (value: string) => void;
}

export function TextField({ label, value, original, placeholder, onChange }: TextFieldProps) {
  const changed = original !== undefined && original !== value;
  return (
    <FieldShell label={label} changed={changed} original={original}>
      <input
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className={`${baseCls} ${changed ? changedCls : normalCls}`}
      />
    </FieldShell>
  );
}

interface SelectFieldProps {
  label: string;
  value: string;
  original?: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}

export function SelectField({ label, value, original, options, onChange }: SelectFieldProps) {
  const changed = original !== undefined && original !== value;
  return (
    <FieldShell label={label} changed={changed} original={original}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`${baseCls} ${changed ? changedCls : normalCls}`}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldShell>
  );
}
