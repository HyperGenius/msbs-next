import { NextResponse } from "next/server";
import { errorResponse, isLocalSimEnabled, notFoundResponse } from "@/lib/localSim/guard";
import { listRosters, localSimDir } from "@/lib/localSim/store";

export const dynamic = "force-dynamic";

export async function GET() {
  if (!isLocalSimEnabled()) return notFoundResponse();
  try {
    return NextResponse.json({ root: localSimDir(), rosters: await listRosters(localSimDir()) });
  } catch (e) {
    return errorResponse(e instanceof Error ? e.message : "ロスターを読めません。", 500);
  }
}
