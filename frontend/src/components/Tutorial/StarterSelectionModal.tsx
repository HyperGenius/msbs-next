"use client";

import { SciFiPanel, SciFiButton, SciFiHeading } from "@/components/ui";

interface StarterReceivedModalProps {
  factionName: string;
  unitName: string;
  onConfirm: () => void;
}

export default function StarterSelectionModal({
  factionName,
  unitName,
  onConfirm,
}: StarterReceivedModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm animate-fade-in">
      <div className="max-w-lg w-full mx-4">
        <SciFiPanel variant="accent" className="p-6 md:p-8">
          {/* ヘッダー */}
          <div className="mb-6 text-center">
            <SciFiHeading level={1} variant="accent" className="text-3xl md:text-4xl mb-3">
              機体配備完了
            </SciFiHeading>
            <p className="text-sm md:text-base text-[#00f0ff]/80">
              UNIT ASSIGNED
            </p>
          </div>

          {/* 配備情報 */}
          <div className="border border-[#00f0ff]/40 bg-[#00f0ff]/5 p-5 mb-6 text-center space-y-3">
            <div className="text-xs text-[#00f0ff]/60 uppercase tracking-widest">配属勢力</div>
            <div className="text-lg font-bold text-[#00f0ff]">{factionName}</div>
            <div className="h-px bg-[#00f0ff]/20" />
            <div className="text-xs text-[#00f0ff]/60 uppercase tracking-widest">支給機体</div>
            <div className="text-2xl font-bold text-[#00f0ff]">{unitName}</div>
            <p className="text-xs text-[#00f0ff]/50 leading-relaxed">
              勢力に応じた練習機が配備されました。<br />
              ショップで新しい機体を入手し、パイロットとして成長しましょう。
            </p>
          </div>

          {/* 確認ボタン */}
          <SciFiButton
            onClick={onConfirm}
            variant="accent"
            size="lg"
            className="w-full"
          >
            ▶ 了解 / ACKNOWLEDGED
          </SciFiButton>
        </SciFiPanel>
      </div>
    </div>
  );
}

