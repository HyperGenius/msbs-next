/* frontend/src/app/api/dev/sim/generations/[generationId]/battles/[index]/route.ts */
import { NextResponse } from "next/server";
import {
  isDevSimEnabled,
  localSimDir,
  notFoundResponse,
  parseBattleIndex,
  readBattle,
} from "../../../../_lib/localSimStore";

export const dynamic = "force-dynamic";

/** 1戦分のログ以外の項目を返す。ログは `logs` で取得する。 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ generationId: string; index: string }> }
) {
  if (!isDevSimEnabled()) return notFoundResponse();
  const { generationId, index } = await params;
  const battleIndex = parseBattleIndex(index);
  const result = battleIndex === null ? null : await readBattle(localSimDir(), generationId, battleIndex);
  if (!result) return notFoundResponse();
  return NextResponse.json(result.battle);
}
