/* frontend/src/app/api/dev/sim/generations/route.ts */
import { NextResponse } from "next/server";
import type { LocalSimGenerationList } from "@/types/battle";
import { isDevSimEnabled, listGenerations, localSimDir, notFoundResponse } from "../_lib/localSimStore";

export const dynamic = "force-dynamic";

/** 保存済みの世代を新しい順に返す。 */
export async function GET() {
  if (!isDevSimEnabled()) return notFoundResponse();
  const root = localSimDir();
  const body: LocalSimGenerationList = { root, generations: await listGenerations(root) };
  return NextResponse.json(body);
}
