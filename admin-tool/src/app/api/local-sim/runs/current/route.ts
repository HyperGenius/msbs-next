import { NextResponse } from "next/server";
import { errorResponse, isLocalSimEnabled, notFoundResponse } from "@/lib/localSim/guard";
import { cancelRun, currentRun } from "@/lib/localSim/runner";

export const dynamic = "force-dynamic";

/** 現在（または直近）の実行の進捗。まだ実行していなければ null。 */
export async function GET() {
  if (!isLocalSimEnabled()) return notFoundResponse();
  return NextResponse.json({ run: currentRun() });
}

/** 実行中のシミュレーションを中止する。 */
export async function DELETE() {
  if (!isLocalSimEnabled()) return notFoundResponse();
  if (!cancelRun()) return errorResponse("実行中のシミュレーションがありません。", 409);
  return NextResponse.json({ run: currentRun() });
}
