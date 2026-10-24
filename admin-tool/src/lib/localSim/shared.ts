/* admin-tool/src/lib/localSim/shared.ts */
import type { LocalSimFetchRequest, LocalSimRunRequest, LocalSimUnitSpec } from "@/types/localSim";

// backend の ROSTER_NAME_PATTERN と同じ。英数字で始めるため `..` と `.tmp-` の書き込み中の世代、`-` で始まる引数を弾く。
const NAME_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_.-]*$/;
const MAX_ROUNDS = 1000;
const PROGRESS_PATTERN = /^\s*\[(\d+)\/(\d+)\]/;
const SAVED_PATTERN = /^保存しました: (.+)$/;
const ROSTER_SAVED_PATTERN = /^\d+ 機を保存しました: (.+)$/;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
// pilots.id（UUID）か user_id（Clerk の user_xxx、NPC の npc-{uuid}）。`-` で始まる引数を弾く。
const PILOT_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_-]*$/;
const MAX_FETCH_UNITS = 100;

/** ロスター名・ラベル・世代ID がファイル名1つ分として安全か確かめる。 */
export function isValidName(value: string): boolean {
  return NAME_PATTERN.test(value);
}

function isPositiveInt(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 1;
}

/**
 * 実行リクエストを検証して `local_sim run` の引数にする。
 * 不正なときは理由の文字列を返す。
 */
export function buildRunArgs(request: LocalSimRunRequest): string[] | string {
  if (typeof request.roster !== "string" || !isValidName(request.roster)) {
    return "ロスター名は英数字で始め、英数字と _ . - だけを使ってください。";
  }
  if (!isPositiveInt(request.rounds) || request.rounds > MAX_ROUNDS) {
    return `戦闘数は 1〜${MAX_ROUNDS} の整数で指定してください。`;
  }
  const args = ["run", "--roster", request.roster, "--rounds", String(request.rounds)];
  if (request.seed != null) {
    if (typeof request.seed !== "number" || !Number.isInteger(request.seed) || request.seed < 0) {
      return "シードは 0 以上の整数で指定してください。";
    }
    args.push("--seed", String(request.seed));
  }
  if (request.steps != null) {
    if (!isPositiveInt(request.steps)) return "最大ステップ数は 1 以上の整数で指定してください。";
    args.push("--steps", String(request.steps));
  }
  if (request.label) {
    if (typeof request.label !== "string" || !isValidName(request.label)) {
      return "ラベルは英数字で始め、英数字と _ . - だけを使ってください。";
    }
    args.push("--label", request.label);
  }
  if (request.pin) args.push("--pin");
  return args;
}

function isNonNegativeInt(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

/** `ID[:TEAM]` を作る。CLI の parse_unit_spec() と同じく、ID とチームは空にできない。 */
function unitSpecArgs(
  option: "--ms" | "--pilot",
  specs: LocalSimUnitSpec[] | undefined,
  isValidId: (id: string) => boolean,
  label: string
): string[] | string {
  if (specs == null) return [];
  if (!Array.isArray(specs)) return "参加機体の指定が不正です。";
  const args: string[] = [];
  for (const spec of specs) {
    if (!spec || typeof spec.id !== "string" || !isValidId(spec.id)) {
      return `${label}が不正です: ${String(spec?.id ?? "")}`;
    }
    if (spec.team != null && spec.team !== "") {
      if (typeof spec.team !== "string" || !isValidName(spec.team)) {
        return "チーム名は英数字で始め、英数字と _ . - だけを使ってください。";
      }
      args.push(option, `${spec.id}:${spec.team}`);
    } else {
      args.push(option, spec.id);
    }
  }
  return args;
}

/**
 * ロスター作成のリクエストを検証して `local_sim fetch` の引数にする。
 * 不正なときは理由の文字列を返す。参加機体の数（2機以上）は CLI が確かめる。
 */
export function buildFetchArgs(request: LocalSimFetchRequest): string[] | string {
  const args = ["fetch"];
  const ms = unitSpecArgs("--ms", request.mobile_suits, (id) => UUID_PATTERN.test(id), "機体ID");
  if (typeof ms === "string") return ms;
  const pilots = unitSpecArgs("--pilot", request.pilots, (id) => PILOT_ID_PATTERN.test(id), "パイロットID");
  if (typeof pilots === "string") return pilots;
  args.push(...ms, ...pilots);
  for (const [option, value, label] of [
    ["--npc", request.npc, "NPC 数"],
    ["--ace", request.ace, "エース数"],
  ] as const) {
    if (value == null || value === 0) continue;
    if (!isNonNegativeInt(value) || value > MAX_FETCH_UNITS) {
      return `${label}は 0〜${MAX_FETCH_UNITS} の整数で指定してください。`;
    }
    args.push(option, String(value));
  }
  const aceIds = request.ace_ids ?? [];
  if (!Array.isArray(aceIds) || aceIds.length > MAX_FETCH_UNITS) return "エースIDの指定が不正です。";
  for (const id of aceIds) {
    if (typeof id !== "string" || !isValidName(id)) return `エースID ${String(id)} が不正です。`;
    args.push("--ace-id", id);
  }
  const hasMission = request.mission != null || !!request.mission_builder;
  if (request.mission != null && request.mission_builder) {
    return "作戦マスターのIDとリポジトリの定義は同時に指定できません。";
  }
  if (request.mission != null) {
    if (!isPositiveInt(request.mission)) return "作戦IDは正の整数で指定してください。";
    args.push("--mission", String(request.mission));
  }
  if (request.mission_builder) {
    if (typeof request.mission_builder !== "string" || !isValidName(request.mission_builder)) {
      return "作戦の定義名が不正です。";
    }
    args.push("--mission-builder", request.mission_builder);
  }
  if (hasMission) {
    // CLI も拒むが、本番DBへ接続する前にここで止める。
    if (request.npc || request.ace || aceIds.length) return "作戦では NPC・エースを指定できません。";
    if ([...(request.mobile_suits ?? []), ...(request.pilots ?? [])].some((u) => u.team)) {
      return "作戦ではチームを指定できません（プレイヤー機は全員同じチームで出ます）。";
    }
  }
  if (request.theater) {
    if (typeof request.theater !== "string" || !isValidName(request.theater)) return "戦域IDが不正です。";
    args.push("--theater", request.theater);
  }
  if (request.minovsky != null) {
    const value = request.minovsky;
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 1) {
      return "ミノフスキー濃度は 0〜1 で指定してください。";
    }
    args.push("--minovsky", String(value));
  }
  if (request.name) {
    if (typeof request.name !== "string" || !isValidName(request.name)) {
      return "ロスター名は英数字で始め、英数字と _ . - だけを使ってください。";
    }
    args.push("--name", request.name);
  }
  if (request.force) args.push("--force");
  return args;
}

/** CLI の出力 1 行から、完了した戦闘数を取り出す（`  [3/20] seed=…`）。 */
export function parseProgress(line: string): number | null {
  const match = PROGRESS_PATTERN.exec(line);
  return match ? Number(match[1]) : null;
}

/** CLI の `保存しました: <世代のパス>` から世代ID（ディレクトリ名）を取り出す。 */
export function parseSavedGenerationId(line: string): string | null {
  const match = SAVED_PATTERN.exec(line.trim());
  if (!match) return null;
  const name = match[1].split(/[\\/]/).filter(Boolean).pop() ?? "";
  return isValidName(name) ? name : null;
}

/** fetch の `N 機を保存しました: <ロスターのパス>` からロスター名を取り出す。 */
export function parseSavedRosterName(line: string): string | null {
  const match = ROSTER_SAVED_PATTERN.exec(line.trim());
  if (!match) return null;
  const file = match[1].split(/[\\/]/).filter(Boolean).pop() ?? "";
  if (!file.endsWith(".json")) return null;
  const name = file.slice(0, -".json".length);
  return isValidName(name) ? name : null;
}
