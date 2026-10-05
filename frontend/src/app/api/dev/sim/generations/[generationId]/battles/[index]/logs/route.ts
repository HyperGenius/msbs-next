/* frontend/src/app/api/dev/sim/generations/[generationId]/battles/[index]/logs/route.ts */
import {
  isDevSimEnabled,
  localSimDir,
  logsToNdjsonStream,
  notFoundResponse,
  parseBattleIndex,
  readBattle,
} from "../../../../../_lib/localSimStore";

export const dynamic = "force-dynamic";

/** 1戦分のログを NDJSON で返す。fuzzy_scores などのデバッグ項目は除く。 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ generationId: string; index: string }> }
) {
  if (!isDevSimEnabled()) return notFoundResponse();
  const { generationId, index } = await params;
  const battleIndex = parseBattleIndex(index);
  const result = battleIndex === null ? null : await readBattle(localSimDir(), generationId, battleIndex);
  if (!result) return notFoundResponse();
  return new Response(logsToNdjsonStream(result.logs), {
    headers: { "Content-Type": "application/x-ndjson; charset=utf-8" },
  });
}
