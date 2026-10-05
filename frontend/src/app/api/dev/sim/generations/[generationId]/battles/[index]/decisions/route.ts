import { NextResponse } from "next/server";
import {
  isDevSimEnabled,
  localSimDir,
  notFoundResponse,
  parseBattleIndex,
  readDecisionLogs,
} from "../../../../../_lib/localSimStore";

export const dynamic = "force-dynamic";

/** `?unit=<機体ID>` の AI の判断ログ（fuzzy_scores・strategy_mode）を返す。 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ generationId: string; index: string }> },
) {
  if (!isDevSimEnabled()) return notFoundResponse();
  const { generationId, index } = await params;
  const unitId = new URL(request.url).searchParams.get("unit");
  const battleIndex = parseBattleIndex(index);
  const logs =
    battleIndex === null || !unitId
      ? null
      : await readDecisionLogs(localSimDir(), generationId, battleIndex, unitId);
  if (!logs) return notFoundResponse();
  return NextResponse.json(logs);
}
