/* admin-tool/src/lib/localSim/runner.ts */
// `local_sim run` / `fetch` を子プロセスで実行し、状態をメモリに持つ。手元の 1 人だけが使う前提。
import { execFile, spawn, type ChildProcess } from "node:child_process";
import path from "node:path";
import type {
  LocalSimBattleRun,
  LocalSimFetchRequest,
  LocalSimFetchRun,
  LocalSimRun,
  LocalSimRunRequest,
} from "@/types/localSim";
import {
  buildFetchArgs,
  buildRunArgs,
  isValidName,
  parseProgress,
  parseSavedGenerationId,
  parseSavedRosterName,
} from "./shared";

const MODULE = "scripts.simulation.local_sim";
const MAX_LINES = 50;
const MAX_STDERR_CHARS = 4000;

interface Job {
  run: LocalSimRun;
  child: ChildProcess;
  cancelRequested: boolean;
}

// dev サーバーのモジュール再読み込みで状態が消えないよう globalThis に置く。
const globalState = globalThis as unknown as { __localSimJob?: Job };

function backendDir(): string {
  return path.resolve(process.cwd(), "..", "backend");
}

/** 現在（または直近）の実行。無ければ null。 */
export function currentRun(): LocalSimRun | null {
  return globalState.__localSimJob?.run ?? null;
}

export class RunConflictError extends Error {}
export class RunValidationError extends Error {}

function assertIdle(): void {
  if (globalState.__localSimJob?.run.status === "running") {
    throw new RunConflictError("実行中のシミュレーションかロスター作成があります。");
  }
}

/** CLI を子プロセスで起動し、出力 1 行ごとに onLine を呼ぶ。終了したら run の状態を書き換える。 */
function launch(run: LocalSimRun, args: string[], onLine: (line: string) => void): void {
  // 引数は配列で渡し、シェルを通さない。
  const child = spawn("uv", ["run", "python", "-m", MODULE, ...args], {
    cwd: backendDir(),
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
    stdio: ["ignore", "pipe", "pipe"],
  });
  const job: Job = { run, child, cancelRequested: false };
  globalState.__localSimJob = job;

  let stdoutRest = "";
  let stderr = "";
  const handleLine = (line: string) => {
    if (!line.trim()) return;
    run.lines.push(line);
    if (run.lines.length > MAX_LINES) run.lines.shift();
    onLine(line);
  };
  child.stdout?.setEncoding("utf-8");
  child.stdout?.on("data", (chunk: string) => {
    const lines = (stdoutRest + chunk).split(/\r?\n/);
    stdoutRest = lines.pop() ?? "";
    lines.forEach(handleLine);
  });
  child.stderr?.setEncoding("utf-8");
  child.stderr?.on("data", (chunk: string) => {
    stderr = (stderr + chunk).slice(-MAX_STDERR_CHARS);
  });

  const finish = (status: LocalSimRun["status"], error: string | null) => {
    if (run.status !== "running") return;
    handleLine(stdoutRest);
    run.status = status;
    run.error = error;
    run.finished_at = new Date().toISOString();
  };
  child.on("error", (err) => finish("failed", `uv を起動できません: ${err.message}`));
  child.on("close", (code) => {
    if (job.cancelRequested) finish("cancelled", null);
    else if (code === 0) finish("succeeded", null);
    else finish("failed", stderr.trim() || `終了コード ${code}`);
  });
}

/** `run` を開始する。実行中なら RunConflictError、リクエストが不正なら RunValidationError。 */
export function startRun(request: LocalSimRunRequest): LocalSimBattleRun {
  const args = buildRunArgs(request);
  if (typeof args === "string") throw new RunValidationError(args);
  assertIdle();
  const run: LocalSimBattleRun = {
    kind: "run",
    request,
    status: "running",
    completed: 0,
    lines: [],
    error: null,
    generation_id: null,
    started_at: new Date().toISOString(),
    finished_at: null,
  };
  launch(run, args, (line) => {
    const progress = parseProgress(line);
    if (progress != null) run.completed = progress;
    run.generation_id = parseSavedGenerationId(line) ?? run.generation_id;
  });
  return run;
}

/**
 * `fetch`（ロスター作成）を開始する。本番DBへは CLI が Read Only の接続で読むだけ。
 * 実行中なら RunConflictError、リクエストが不正なら RunValidationError。
 */
export function startFetch(request: LocalSimFetchRequest): LocalSimFetchRun {
  const args = buildFetchArgs(request);
  if (typeof args === "string") throw new RunValidationError(args);
  assertIdle();
  const run: LocalSimFetchRun = {
    kind: "fetch",
    request,
    status: "running",
    lines: [],
    error: null,
    roster_name: null,
    started_at: new Date().toISOString(),
    finished_at: null,
  };
  launch(run, args, (line) => {
    run.roster_name = parseSavedRosterName(line) ?? run.roster_name;
  });
  return run;
}

/** 実行中のジョブを SIGTERM で止める。run は書きかけの世代を消してから終了する。fetch は DB を読むだけなので、そのまま終わる。 */
export function cancelRun(): boolean {
  const job = globalState.__localSimJob;
  if (!job || job.run.status !== "running") return false;
  job.cancelRequested = true;
  job.child.kill("SIGTERM");
  return true;
}

/** 世代のピン留めを CLI の pin / unpin で切り替える。 */
export function setPinned(generationId: string, pinned: boolean): Promise<void> {
  if (!isValidName(generationId)) return Promise.reject(new RunValidationError("世代IDが不正です。"));
  return new Promise((resolve, reject) => {
    execFile(
      "uv",
      ["run", "python", "-m", MODULE, pinned ? "pin" : "unpin", generationId],
      { cwd: backendDir() },
      (error, _stdout, stderr) => {
        if (error) reject(new Error(stderr.trim() || error.message));
        else resolve();
      }
    );
  });
}
