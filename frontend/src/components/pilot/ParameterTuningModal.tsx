"use client";

import { Pilot } from "@/types/battle";
import { KeyedMutator } from "swr";
import SciFiModal from "@/components/ui/SciFiModal";
import ParameterTuningPanel from "./ParameterTuningPanel";

interface ParameterTuningModalProps {
  pilot: Pilot;
  mutatePilot: KeyedMutator<Pilot>;
  onClose: () => void;
}

/**
 * パラメータチューニングパネルをモーダルとして表示するラッパー。
 * モバイルではボトムシート、sm 以上では中央寄せで表示される。
 */
export default function ParameterTuningModal({ pilot, mutatePilot, onClose }: ParameterTuningModalProps) {
  return (
    <SciFiModal isOpen onClose={onClose} variant="secondary" maxWidthClass="max-w-3xl">
      <div className="relative">
        {/* 閉じるボタン */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 z-10 text-gray-400 hover:text-[#ffb000] transition-colors font-mono text-sm"
          aria-label="閉じる"
        >
          ✕ CLOSE
        </button>

        <ParameterTuningPanel pilot={pilot} mutatePilot={mutatePilot} />
      </div>
    </SciFiModal>
  );
}
