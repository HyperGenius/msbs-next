import { NextResponse } from "next/server";
import { isDevSimEnabled, localSimDir, notFoundResponse, readReport } from "../../../_lib/localSimStore";

export const dynamic = "force-dynamic";

/** 世代の集計値（CLI が保存した report.json）を返す。 */
export async function GET(_request: Request, { params }: { params: Promise<{ generationId: string }> }) {
  if (!isDevSimEnabled()) return notFoundResponse();
  const { generationId } = await params;
  const report = await readReport(localSimDir(), generationId);
  if (!report) return notFoundResponse();
  return NextResponse.json(report);
}
