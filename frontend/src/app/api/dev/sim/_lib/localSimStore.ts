/* frontend/src/app/api/dev/sim/_lib/localSimStore.ts */
import { promises as fs } from "node:fs";
import path from "node:path";
import { NextResponse } from "next/server";
import type { BattleLog, LocalSimBattle, LocalSimManifest } from "@/types/battle";

const GENERATIONS_DIR = "generations";
const MANIFEST_FILE = "manifest.json";
// generations.py の ROSTER_NAME_PATTERN と同じ。英数字で始めるため、`.tmp-` の書き込み中の世代と `..` を弾く。
const GENERATION_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_.-]*$/;
const BATTLE_FILE_PATTERN = /^battle_\d+\.json$/;
const BATTLE_INDEX_PATTERN = /^\d+$/;
// 表示に使わないデバッグ項目。1戦のログの約1/4を占めるため、返す前に除く。
const DEBUG_LOG_FIELDS = ["fuzzy_scores"] as const;
const NDJSON_CHUNK_LINES = 500;

/** 開発環境（`next dev`）のときだけ true を返す。 */
export function isDevSimEnabled(): boolean {
  return process.env.NODE_ENV === "development";
}

/** 開発環境以外で Route Handler が返す 404。 */
export function notFoundResponse(): NextResponse {
  return NextResponse.json({ detail: "Not Found" }, { status: 404 });
}

/**
 * ローカルシミュレーションの保存先を返す。
 * 既定は `next dev` を動かす frontend/ の親（リポジトリ直下）の battle_logs/local_sim。
 */
export function localSimDir(): string {
  const configured = process.env.LOCAL_SIM_DIR;
  return configured
    ? path.resolve(configured)
    : path.resolve(process.cwd(), "..", "battle_logs", "local_sim");
}

/** 世代ID がディレクトリ名1つ分として安全か確かめる。 */
export function isValidGenerationId(generationId: string): boolean {
  return GENERATION_ID_PATTERN.test(generationId);
}

/** URL の戦闘番号を数値にする。数字以外を含むときは null を返す。 */
export function parseBattleIndex(value: string): number | null {
  return BATTLE_INDEX_PATTERN.test(value) ? Number(value) : null;
}

/**
 * root 配下のファイルの実パスを返す。
 * 無いとき、またはシンボリックリンクを辿って root の外に出るときは null を返す。
 */
async function resolveInside(root: string, ...segments: string[]): Promise<string | null> {
  let realRoot: string;
  let realTarget: string;
  try {
    realRoot = await fs.realpath(root);
    realTarget = await fs.realpath(path.join(root, ...segments));
  } catch (error) {
    if (isNotFound(error)) return null;
    throw error;
  }
  const relative = path.relative(realRoot, realTarget);
  if (!relative || path.isAbsolute(relative) || relative.split(path.sep)[0] === "..") {
    return null;
  }
  return realTarget;
}

function isNotFound(error: unknown): boolean {
  const code = (error as NodeJS.ErrnoException).code;
  return code === "ENOENT" || code === "ENOTDIR";
}

/** 世代の `manifest.json` を読む。世代が無いときは null を返す。 */
export async function readManifest(
  root: string,
  generationId: string
): Promise<LocalSimManifest | null> {
  if (!isValidGenerationId(generationId)) return null;
  const file = await resolveInside(root, GENERATIONS_DIR, generationId, MANIFEST_FILE);
  if (!file) return null;
  const manifest = JSON.parse(await fs.readFile(file, "utf-8")) as LocalSimManifest;
  // CLI（find_generation）と同じく、ディレクトリ名を世代ID とする。
  return { ...manifest, generation_id: generationId };
}

/** 保存済みの世代を新しい順に返す。`manifest.json` が無いディレクトリは除く。 */
export async function listGenerations(root: string): Promise<LocalSimManifest[]> {
  let entries;
  try {
    entries = await fs.readdir(path.join(root, GENERATIONS_DIR), { withFileTypes: true });
  } catch (error) {
    if (isNotFound(error)) return [];
    throw error;
  }
  const manifests = await Promise.all(
    entries
      .filter((entry) => entry.isDirectory() && isValidGenerationId(entry.name))
      .map((entry) => readManifest(root, entry.name))
  );
  return manifests
    .filter((manifest): manifest is LocalSimManifest => manifest !== null)
    .sort(
      (a, b) =>
        Date.parse(b.created_at) - Date.parse(a.created_at) ||
        b.generation_id.localeCompare(a.generation_id)
    );
}

/**
 * 1戦分を読み、表示に使う項目とログに分けて返す。
 * ファイル名は `manifest.json` の一覧から引く。世代か戦闘が無いときは null を返す。
 */
export async function readBattle(
  root: string,
  generationId: string,
  index: number
): Promise<{ battle: LocalSimBattle; logs: BattleLog[] } | null> {
  const manifest = await readManifest(root, generationId);
  const summary = manifest?.battles.find((b) => b.index === index);
  if (!summary || !BATTLE_FILE_PATTERN.test(summary.file)) return null;
  const file = await resolveInside(root, GENERATIONS_DIR, generationId, summary.file);
  if (!file) return null;

  const { logs, ...rest } = JSON.parse(await fs.readFile(file, "utf-8")) as Omit<
    LocalSimBattle,
    "log_count"
  > & { logs: BattleLog[] };
  for (const log of logs) {
    for (const field of DEBUG_LOG_FIELDS) delete log[field];
  }
  return { battle: { ...rest, log_count: logs.length }, logs };
}

/** ログを本番の `/api/battles/{id}/logs` と同じ NDJSON で少しずつ送るストリームにする。 */
export function logsToNdjsonStream(logs: BattleLog[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let next = 0;
  return new ReadableStream({
    pull(controller) {
      if (next >= logs.length) {
        controller.close();
        return;
      }
      const end = Math.min(next + NDJSON_CHUNK_LINES, logs.length);
      let text = "";
      for (; next < end; next++) text += `${JSON.stringify(logs[next])}\n`;
      controller.enqueue(encoder.encode(text));
    },
  });
}
