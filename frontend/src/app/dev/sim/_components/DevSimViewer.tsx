/* frontend/src/app/dev/sim/_components/DevSimViewer.tsx */
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useLocalSimGenerations } from "@/services/api";
import GenerationList from "./GenerationList";
import SimBattleList from "./SimBattleList";
import SimReplay from "./SimReplay";

/** 世代一覧・バトル一覧・再生画面。選択中の世代とバトルは URL の gen / battle に持つ。 */
export default function DevSimViewer() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { root, generations, isLoading, isError } = useLocalSimGenerations();

  const generationId = searchParams.get("gen") ?? generations?.[0]?.generation_id ?? null;
  const manifest = generations?.find((g) => g.generation_id === generationId) ?? null;
  const battleParam = Number(searchParams.get("battle"));
  const battleIndex = manifest?.battles.some((b) => b.index === battleParam) ? battleParam : null;

  const select = (nextGenerationId: string, nextBattleIndex: number | null = null) => {
    const params = new URLSearchParams({ gen: nextGenerationId });
    if (nextBattleIndex !== null) params.set("battle", String(nextBattleIndex));
    router.replace(`/dev/sim?${params}`, { scroll: false });
  };

  return (
    <div className="min-h-full bg-gray-900 text-green-400 p-4 md:p-8 font-mono">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold mb-1">LOCAL SIM VIEWER</h1>
        <p className="text-xs text-gray-500 mb-6 break-all">
          開発環境専用。読み込み元: {root ?? "..."}
        </p>

        {isError ? (
          <p className="text-red-400 text-sm" role="alert">
            世代の一覧を読み込めませんでした: {String(isError.message ?? isError)}
          </p>
        ) : isLoading || !generations ? (
          <p className="text-gray-400 text-sm">読み込み中...</p>
        ) : generations.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="grid gap-6 md:grid-cols-[20rem_minmax(0,1fr)]">
            <div className="flex flex-col gap-6">
              <GenerationList
                generations={generations}
                selectedId={manifest?.generation_id ?? null}
                onSelect={(id) => select(id)}
              />
              {manifest && (
                <SimBattleList
                  battles={manifest.battles}
                  selectedIndex={battleIndex}
                  onSelect={(index) => select(manifest.generation_id, index)}
                />
              )}
            </div>
            <div>
              {manifest && battleIndex !== null ? (
                // バトルを切り替えたら再生位置を 0 に戻すため、作り直す。
                <SimReplay
                  key={`${manifest.generation_id}/${battleIndex}`}
                  manifest={manifest}
                  index={battleIndex}
                  onClose={() => select(manifest.generation_id)}
                />
              ) : (
                <p className="text-gray-500 text-sm">バトルを選ぶと再生します。</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/** 保存した世代が無いときに、結果の作り方を案内する。 */
function EmptyState() {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4 text-sm text-gray-300">
      <p className="mb-3">保存したシミュレーション結果がありません。backend で次を実行してください。</p>
      <pre className="bg-gray-950 border border-gray-700 rounded p-3 text-xs text-green-300 overflow-x-auto">
        {[
          "cd backend",
          "python -m scripts.simulation.local_sim fetch --pilot <パイロットID> --npc 7 --name <ロスター名>",
          "python -m scripts.simulation.local_sim run --roster <ロスター名> --rounds 5",
        ].join("\n")}
      </pre>
      <p className="mt-3 text-xs text-gray-500">
        別の場所に保存した結果を読むときは、環境変数 LOCAL_SIM_DIR に local_sim ディレクトリを指定して
        npm run dev を起動し直してください。手順は docs/features/local-battle-simulator.md にあります。
      </p>
    </div>
  );
}
