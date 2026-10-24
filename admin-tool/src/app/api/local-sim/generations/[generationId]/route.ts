import { NextResponse } from "next/server";
import { errorResponse, isLocalSimEnabled, notFoundResponse } from "@/lib/localSim/guard";
import { RunValidationError, setPinned } from "@/lib/localSim/runner";
import { localSimDir, readManifest, readReport } from "@/lib/localSim/store";

export const dynamic = "force-dynamic";

type Context = { params: Promise<{ generationId: string }> };

/** 世代の manifest と report。 */
export async function GET(_request: Request, { params }: Context) {
  if (!isLocalSimEnabled()) return notFoundResponse();
  const { generationId } = await params;
  try {
    const manifest = await readManifest(localSimDir(), generationId);
    if (!manifest) return errorResponse("世代が見つかりません。", 404);
    const report = await readReport(localSimDir(), generationId);
    return NextResponse.json({ manifest, report });
  } catch (e) {
    return errorResponse(e instanceof Error ? e.message : "世代を読めません。", 500);
  }
}

/** ピン留めの切り替え。body は { pinned: boolean }。 */
export async function PATCH(request: Request, { params }: Context) {
  if (!isLocalSimEnabled()) return notFoundResponse();
  const { generationId } = await params;
  const body = (await request.json().catch(() => null)) as { pinned?: unknown } | null;
  if (typeof body?.pinned !== "boolean") return errorResponse("pinned を指定してください。", 422);
  try {
    if (!(await readManifest(localSimDir(), generationId))) {
      return errorResponse("世代が見つかりません。", 404);
    }
    await setPinned(generationId, body.pinned);
    return NextResponse.json({ generation_id: generationId, pinned: body.pinned });
  } catch (e) {
    const status = e instanceof RunValidationError ? 422 : 500;
    return errorResponse(e instanceof Error ? e.message : "ピン留めを変更できません。", status);
  }
}
