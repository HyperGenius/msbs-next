/* admin-tool/src/lib/localSim/store.ts */
// battle_logs/local_sim の読み込み。frontend の localSimStore.ts と同じ規則でパスを検証する。
import { promises as fs } from "node:fs";
import path from "node:path";
import type { LocalSimManifest, LocalSimReport, LocalSimRoster, LocalSimRosterInfo } from "@/types/localSim";
import { isValidName } from "./shared";

const GENERATIONS_DIR = "generations";
const ROSTERS_DIR = "rosters";
const MANIFEST_FILE = "manifest.json";
const REPORT_FILE = "report.json";

/** 保存先。既定は admin-tool/ の親（リポジトリ直下）の battle_logs/local_sim。 */
export function localSimDir(): string {
  const configured = process.env.LOCAL_SIM_DIR;
  return configured
    ? path.resolve(configured)
    : path.resolve(process.cwd(), "..", "battle_logs", "local_sim");
}

function isNotFound(error: unknown): boolean {
  const code = (error as NodeJS.ErrnoException).code;
  return code === "ENOENT" || code === "ENOTDIR";
}

/** root 配下のファイルの実パスを返す。無いとき、または root の外に出るときは null。 */
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
  if (!relative || path.isAbsolute(relative) || relative.split(path.sep)[0] === "..") return null;
  return realTarget;
}

export async function readManifest(root: string, generationId: string): Promise<LocalSimManifest | null> {
  if (!isValidName(generationId)) return null;
  const file = await resolveInside(root, GENERATIONS_DIR, generationId, MANIFEST_FILE);
  if (!file) return null;
  const manifest = JSON.parse(await fs.readFile(file, "utf-8")) as LocalSimManifest;
  return { ...manifest, generation_id: generationId };
}

export async function readReport(root: string, generationId: string): Promise<LocalSimReport | null> {
  if (!isValidName(generationId)) return null;
  const file = await resolveInside(root, GENERATIONS_DIR, generationId, REPORT_FILE);
  if (!file) return null;
  return JSON.parse(await fs.readFile(file, "utf-8")) as LocalSimReport;
}

/** 世代を新しい順に返す。一覧では戦闘ごとの内訳を省く。 */
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
      .filter((entry) => entry.isDirectory() && isValidName(entry.name))
      .map((entry) => readManifest(root, entry.name))
  );
  return manifests
    .filter((m): m is LocalSimManifest => m !== null)
    .map((m) => ({ ...m, battles: [] }))
    .sort(
      (a, b) =>
        Date.parse(b.created_at) - Date.parse(a.created_at) ||
        b.generation_id.localeCompare(a.generation_id)
    );
}

/** ロスターを名前順に返す。読めないファイルは除く。 */
export async function listRosters(root: string): Promise<LocalSimRosterInfo[]> {
  const dir = path.join(root, ROSTERS_DIR);
  let files: string[];
  try {
    files = await fs.readdir(dir);
  } catch (error) {
    if (isNotFound(error)) return [];
    throw error;
  }
  const rosters: LocalSimRosterInfo[] = [];
  for (const file of files.filter((f) => f.endsWith(".json")).sort()) {
    const name = file.slice(0, -".json".length);
    if (!isValidName(name)) continue;
    try {
      const data = JSON.parse(await fs.readFile(path.join(dir, file), "utf-8"));
      rosters.push({
        name,
        entries: Array.isArray(data.entries) ? data.entries.length : 0,
        theater_id: data.conditions?.theater_id ?? null,
        fetched_at: data.fetched_at ?? null,
      });
    } catch {
      // 壊れたロスターは一覧に出さない。
    }
  }
  return rosters;
}

/** 同名のロスターがあるか。 */
export async function rosterExists(root: string, name: string): Promise<boolean> {
  if (!isValidName(name)) return false;
  return (await resolveInside(root, ROSTERS_DIR, `${name}.json`)) !== null;
}

/** ロスターの中身を返す。無いときは null。 */
export async function readRoster(root: string, name: string): Promise<LocalSimRoster | null> {
  if (!isValidName(name)) return null;
  const file = await resolveInside(root, ROSTERS_DIR, `${name}.json`);
  if (!file) return null;
  return JSON.parse(await fs.readFile(file, "utf-8")) as LocalSimRoster;
}
