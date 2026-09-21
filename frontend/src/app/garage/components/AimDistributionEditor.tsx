/* frontend/src/app/garage/components/AimDistributionEditor.tsx */
"use client";

import { useMemo, useState } from "react";
import { PlayerWeapon } from "@/types/battle";
import { updatePlayerWeaponAimDistribution } from "@/services/api";
import { SciFiButton, SciFiHeading } from "@/components/ui";

interface AimDistributionEditorProps {
  playerWeapon: PlayerWeapon;
  /** 更新成功時に呼ばれる（更新後の PlayerWeapon を渡す） */
  onUpdated: (updated: PlayerWeapon) => void;
}

/** 部位の並び順・日本語ラベル定義 */
const PART_LABELS: { key: string; label: string }[] = [
  { key: "HEAD", label: "頭部" },
  { key: "TORSO", label: "胴体" },
  { key: "RIGHT_ARM", label: "右腕" },
  { key: "LEFT_ARM", label: "左腕" },
  { key: "RIGHT_LEG", label: "右脚" },
  { key: "LEFT_LEG", label: "左脚" },
];

// バックエンド(DEFAULT_AIM_DISTRIBUTION)と同じ初期値。他の配分値(割合 0.0〜1.0)と
// 単位を揃えておく（%はUI表示専用でDEFAULT_DISTRIBUTION_PERCENTに分離している）
const DEFAULT_DISTRIBUTION_RATIO: Record<string, number> = {
  TORSO: 0.5,
  RIGHT_ARM: 0.1,
  LEFT_ARM: 0.1,
  RIGHT_LEG: 0.1,
  LEFT_LEG: 0.1,
  HEAD: 0.1,
};

// 「初期値に戻す」ボタン用のUI表示値(%)。DEFAULT_DISTRIBUTION_RATIOの100倍と常に一致させること
const DEFAULT_DISTRIBUTION_PERCENT: Record<string, number> = {
  TORSO: 50,
  RIGHT_ARM: 10,
  LEFT_ARM: 10,
  RIGHT_LEG: 10,
  LEFT_LEG: 10,
  HEAD: 10,
};

/** 現在の武器インスタンスに設定されている配分(%)を取得する（優先順: custom_stats上書き → base_snapshotの初期値 → デフォルト） */
function resolveCurrentDistribution(playerWeapon: PlayerWeapon): Record<string, number> {
  const override = playerWeapon.custom_stats?.aim_distribution;
  const base = (playerWeapon.base_snapshot as { aim_distribution?: Record<string, number> })
    .aim_distribution;
  const source = override ?? base ?? DEFAULT_DISTRIBUTION_RATIO;

  const result: Record<string, number> = {};
  for (const { key } of PART_LABELS) {
    // 割合(0.0〜1.0)を%表示用の整数に変換
    result[key] = Math.round((source[key] ?? 0) * 100);
  }
  return result;
}

export default function AimDistributionEditor({
  playerWeapon,
  onUpdated,
}: AimDistributionEditorProps) {
  const [values, setValues] = useState<Record<string, number>>(() =>
    resolveCurrentDistribution(playerWeapon)
  );
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const total = useMemo(
    () => PART_LABELS.reduce((sum, { key }) => sum + (values[key] ?? 0), 0),
    [values]
  );
  const isValidTotal = total === 100;

  const handleChange = (key: string, value: number) => {
    setValues((prev) => ({ ...prev, [key]: Math.max(0, Math.min(100, value)) }));
    setMessage(null);
  };

  const handleReset = () => {
    setValues({ ...DEFAULT_DISTRIBUTION_PERCENT });
    setMessage(null);
  };

  const handleApply = async () => {
    if (!isValidTotal) return;

    setIsSaving(true);
    setMessage(null);

    try {
      // %表示(整数)を割合(0.0〜1.0)へ変換して送信
      const aim_distribution: Record<string, number> = {};
      for (const { key } of PART_LABELS) {
        aim_distribution[key] = (values[key] ?? 0) / 100;
      }

      const updated = await updatePlayerWeaponAimDistribution(playerWeapon.id, {
        aim_distribution,
      });

      setMessage("✓ 狙う部位配分を更新しました");
      onUpdated(updated);
    } catch (error) {
      setMessage(
        `✗ エラー: ${error instanceof Error ? error.message : "更新に失敗しました"}`
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="pt-4 border-t border-[#00ff41]/20">
      <div className="flex items-center justify-between mb-1">
        <SciFiHeading level={4} className="text-base">
          狙う部位配分
        </SciFiHeading>
        <span
          className={`text-xs font-mono ${
            isValidTotal ? "text-[#00ff41]/70" : "text-red-400"
          }`}
        >
          合計: {total}%
        </span>
      </div>
      <p className="text-xs text-[#00ff41]/50 mb-3">
        この武器が命中時に狙う部位の割合を設定します（合計100%）。相対角度・距離による補正と組み合わせて実際の命中部位が決まります
      </p>

      <div className="space-y-2">
        {PART_LABELS.map(({ key, label }) => (
          <div key={key} className="flex items-center gap-2">
            <span className="w-10 text-xs font-mono text-[#00ff41]/80 shrink-0">
              {label}
            </span>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={values[key] ?? 0}
              onChange={(e) => handleChange(key, Number(e.target.value))}
              className="flex-1 accent-[#00ff41]"
              aria-label={`${label}の配分`}
            />
            <span className="w-12 text-right text-xs font-mono text-[#00ff41]">
              {values[key] ?? 0}%
            </span>
          </div>
        ))}
      </div>

      {message && (
        <div
          className={`mt-3 p-2 rounded border text-xs ${
            message.startsWith("✓")
              ? "bg-[#00ff41]/10 border-[#00ff41]/50 text-[#00ff41]"
              : "bg-red-900/30 border-red-600/50 text-red-300"
          }`}
        >
          {message}
        </div>
      )}

      <div className="flex items-center gap-2 mt-3">
        <SciFiButton
          size="sm"
          variant="accent"
          onClick={handleApply}
          disabled={!isValidTotal || isSaving}
        >
          {isSaving ? "更新中..." : "配分を適用"}
        </SciFiButton>
        <button
          onClick={handleReset}
          disabled={isSaving}
          className="text-xs text-[#00ff41]/50 hover:text-[#00ff41] underline disabled:opacity-30"
        >
          初期値に戻す
        </button>
      </div>
    </div>
  );
}
