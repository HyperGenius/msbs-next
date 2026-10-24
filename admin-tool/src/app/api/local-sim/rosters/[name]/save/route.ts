import { NextResponse } from "next/server";
import { errorResponse, isLocalSimEnabled, notFoundResponse } from "@/lib/localSim/guard";
import { RunValidationError, saveRoster } from "@/lib/localSim/runner";
import { localSimDir, rosterExists } from "@/lib/localSim/store";
import type { LocalSimRoster } from "@/types/localSim";

export const dynamic = "force-dynamic";

/**
 * 編集したロスターを `{name}` の名前の新しいロスターとして保存する。
 * body は `{ roster, force? }`。URL の名前は保存先で、元のロスターとは別の名前にして比べられるようにする。
 * 同名があり force でなければ 409、形式が不正なら 422。
 */
export async function POST(request: Request, { params }: { params: Promise<{ name: string }> }) {
  if (!isLocalSimEnabled()) return notFoundResponse();
  const { name } = await params;
  const body = (await request.json().catch(() => null)) as { roster?: LocalSimRoster; force?: boolean } | null;
  if (!body || typeof body.roster !== "object" || body.roster === null) {
    return errorResponse("リクエストが不正です。", 422);
  }
  const force = body.force === true;
  try {
    if (!force && (await rosterExists(localSimDir(), name))) {
      return errorResponse(`ロスター ${name} は既にあります。上書きするときは force を指定してください。`, 409);
    }
    await saveRoster(name, body.roster, force);
    return NextResponse.json({ name });
  } catch (e) {
    if (e instanceof RunValidationError) return errorResponse(e.message, 422);
    return errorResponse(e instanceof Error ? e.message : "ロスターを保存できません。", 500);
  }
}
