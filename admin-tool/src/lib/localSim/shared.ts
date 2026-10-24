/* admin-tool/src/lib/localSim/shared.ts */
import type { LocalSimRunRequest } from "@/types/localSim";

// backend の ROSTER_NAME_PATTERN と同じ。英数字で始めるため `..` と `.tmp-` の書き込み中の世代、`-` で始まる引数を弾く。
const NAME_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_.-]*$/;
const MAX_ROUNDS = 1000;
const PROGRESS_PATTERN = /^\s*\[(\d+)\/(\d+)\]/;
const SAVED_PATTERN = /^保存しました: (.+)$/;

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
