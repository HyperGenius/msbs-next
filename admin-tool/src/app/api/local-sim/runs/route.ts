import { NextResponse } from "next/server";
import { errorResponse, isLocalSimEnabled, notFoundResponse } from "@/lib/localSim/guard";
import { RunConflictError, RunValidationError, startRun } from "@/lib/localSim/runner";
import type { LocalSimRunRequest } from "@/types/localSim";

export const dynamic = "force-dynamic";

/** 実行を開始する。実行中なら 409。 */
export async function POST(request: Request) {
  if (!isLocalSimEnabled()) return notFoundResponse();
  const body = (await request.json().catch(() => null)) as LocalSimRunRequest | null;
  if (!body || typeof body !== "object") return errorResponse("リクエストが不正です。", 422);
  try {
    return NextResponse.json(startRun(body), { status: 202 });
  } catch (e) {
    if (e instanceof RunConflictError) return errorResponse(e.message, 409);
    if (e instanceof RunValidationError) return errorResponse(e.message, 422);
    return errorResponse(e instanceof Error ? e.message : "実行を開始できません。", 500);
  }
}
