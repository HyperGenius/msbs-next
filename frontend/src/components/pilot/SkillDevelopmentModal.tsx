"use client";

import { Pilot, SkillDefinition } from "@/types/battle";
import { KeyedMutator } from "swr";
import SciFiModal from "@/components/ui/SciFiModal";
import SkillDevelopmentPanel from "./SkillDevelopmentPanel";

interface SkillDevelopmentModalProps {
  pilot: Pilot;
  skills: SkillDefinition[];
  mutatePilot: KeyedMutator<Pilot>;
  onClose: () => void;
}

/**
 * スキル開発パネルをモーダルとして表示するラッパー。
 * モバイルではボトムシート、sm 以上では中央寄せで表示される。
 */
export default function SkillDevelopmentModal({ pilot, skills, mutatePilot, onClose }: SkillDevelopmentModalProps) {
  return (
    <SciFiModal isOpen onClose={onClose} variant="accent" maxWidthClass="max-w-3xl">
      <div className="relative">
        {/* 閉じるボタン */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 z-10 text-gray-400 hover:text-[#00f0ff] transition-colors font-mono text-sm"
          aria-label="閉じる"
        >
          ✕ CLOSE
        </button>

        <SkillDevelopmentPanel pilot={pilot} skills={skills} mutatePilot={mutatePilot} />
      </div>
    </SciFiModal>
  );
}
