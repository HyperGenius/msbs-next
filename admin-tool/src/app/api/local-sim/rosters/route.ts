import { NextResponse } from "next/server";
import { errorResponse, isLocalSimEnabled, notFoundResponse } from "@/lib/localSim/guard";
import { RunConflictError, RunValidationError, startFetch } from "@/lib/localSim/runner";
import { listRosters, localSimDir, rosterExists } from "@/lib/localSim/store";
import type { LocalSimFetchRequest } from "@/types/localSim";

export const dynamic = "force-dynamic";

export async function GET() {
  if (!isLocalSimEnabled()) return notFoundResponse();
  try {
    return NextResponse.json({ root: localSimDir(), rosters: await listRosters(localSimDir()) });
  } catch (e) {
    return errorResponse(e instanceof Error ? e.message : "ロスターを読めません。", 500);
  }
}

/**
 * `fetch` でロスターを作る。進捗は `GET /api/local-sim/runs/current` で `run` と共通。
 * 実行中なら 409、同名のロスターがあり force でなければ 409、入力が不正なら 422。
 */
export async function POST(request: Request) {
  if (!isLocalSimEnabled()) return notFoundResponse();
  const body = (await request.json().catch(() => null)) as LocalSimFetchRequest | null;
  if (!body || typeof body !== "object") return errorResponse("リクエストが不正です。", 422);
  try {
    // CLI も同名を拒むが、本番DBから読み終えた後になるため先に確かめる。
    if (!body.force && typeof body.name === "string" && (await rosterExists(localSimDir(), body.name))) {
      return errorResponse(`ロスター ${body.name} は既にあります。上書きするときは force を指定してください。`, 409);
    }
    return NextResponse.json(startFetch(body), { status: 202 });
  } catch (e) {
    if (e instanceof RunConflictError) return errorResponse(e.message, 409);
    if (e instanceof RunValidationError) return errorResponse(e.message, 422);
    return errorResponse(e instanceof Error ? e.message : "ロスターの作成を開始できません。", 500);
  }
}
