import Link from "next/link";
import { SciFiPanel, SciFiHeading, SciFiButton } from "@/components/ui";

export default function HomePage() {
  return (
    <main className="max-w-2xl mx-auto px-4 py-12">
      <SciFiHeading level={1} className="mb-8">
        MSBS Admin Tool
      </SciFiHeading>
      <SciFiPanel className="p-6 space-y-4">
        <p className="text-sm text-[#00ff41]/70">
          ゲームバランス調整用のマスタデータ管理ツールです。
        </p>
        <div className="flex flex-col gap-3">
          <Link href="/mobile-suits">
            <SciFiButton className="w-full">機体マスタ管理</SciFiButton>
          </Link>
          <Link href="/weapons">
            <SciFiButton className="w-full" variant="secondary">
              武器マスタ管理
            </SciFiButton>
          </Link>
          <Link href="/npcs">
            <SciFiButton className="w-full" variant="secondary">
              NPCパイロット管理
            </SciFiButton>
          </Link>
        </div>
      </SciFiPanel>
    </main>
  );
}
