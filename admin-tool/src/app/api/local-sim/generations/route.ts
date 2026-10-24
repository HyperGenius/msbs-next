import { NextResponse } from "next/server";
import { errorResponse, isLocalSimEnabled, notFoundResponse } from "@/lib/localSim/guard";
import { listGenerations, localSimDir } from "@/lib/localSim/store";

export const dynamic = "force-dynamic";

export async function GET() {
  if (!isLocalSimEnabled()) return notFoundResponse();
  try {
    return NextResponse.json({
      root: localSimDir(),
      generations: await listGenerations(localSimDir()),
    });
  } catch (e) {
    return errorResponse(e instanceof Error ? e.message : "世代を読めません。", 500);
  }
}
