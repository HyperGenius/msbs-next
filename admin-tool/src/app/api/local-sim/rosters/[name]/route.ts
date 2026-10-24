import { NextResponse } from "next/server";
import { errorResponse, isLocalSimEnabled, notFoundResponse } from "@/lib/localSim/guard";
import { localSimDir, readRoster } from "@/lib/localSim/store";

export const dynamic = "force-dynamic";

/** ロスターの中身を返す。編集画面が読む。 */
export async function GET(_request: Request, { params }: { params: Promise<{ name: string }> }) {
  if (!isLocalSimEnabled()) return notFoundResponse();
  const { name } = await params;
  try {
    const roster = await readRoster(localSimDir(), name);
    if (!roster) return notFoundResponse();
    return NextResponse.json({ roster });
  } catch (e) {
    return errorResponse(e instanceof Error ? e.message : "ロスターを読めません。", 500);
  }
}
