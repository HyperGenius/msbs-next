/* admin-tool/src/lib/localSim/guard.ts */
import { NextResponse } from "next/server";

/** 開発環境（`next dev`）のときだけ true。frontend の `/dev/sim` と同じ。 */
export function isLocalSimEnabled(): boolean {
  return process.env.NODE_ENV === "development";
}

export function notFoundResponse(): NextResponse {
  return NextResponse.json({ detail: "Not Found" }, { status: 404 });
}

export function errorResponse(detail: string, status: number): NextResponse {
  return NextResponse.json({ detail }, { status });
}
