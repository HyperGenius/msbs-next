/* admin-tool/src/lib/localSim/runner.ts */
// `local_sim run` を子プロセスで実行し、状態をメモリに持つ。手元の 1 人だけが使う前提。
import { execFile, spawn, type ChildProcess } from "node:child_process";
import path from "node:path";
import type { LocalSimRun, LocalSimRunRequest } from "@/types/localSim";
import { buildRunArgs, isValidName, parseProgress, parseSavedGenerationId } from "./shared";

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

/** 実行を開始する。実行中なら RunConflictError、リクエストが不正なら RunValidationError。 */
export function startRun(request: LocalSimRunRequest): LocalSimRun {
  const args = buildRunArgs(request);
  if (typeof args === "string") throw new RunValidationError(args);
  if (globalState.__localSimJob?.run.status === "running") {
    throw new RunConflictError("実行中のシミュレーションがあります。");
  }

  // 引数は配列で渡し、シェルを通さない。
  const child = spawn("uv", ["run", "python", "-m", MODULE, ...args], {
    cwd: backendDir(),
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
    stdio: ["ignore", "pipe", "pipe"],
  });
  const run: LocalSimRun = {
    request,
    status: "running",
    completed: 0,
    lines: [],
    error: null,
    generation_id: null,
    started_at: new Date().toISOString(),
    finished_at: null,
  };
  const job: Job = { run, child, cancelRequested: false };
  globalState.__localSimJob = job;

  let stdoutRest = "";
  let stderr = "";
  const onLine = (line: string) => {
    if (!line.trim()) return;
    run.lines.push(line);
    if (run.lines.length > MAX_LINES) run.lines.shift();
    const progress = parseProgress(line);
    if (progress != null) run.completed = progress;
    run.generation_id = parseSavedGenerationId(line) ?? run.generation_id;
  };
  child.stdout?.setEncoding("utf-8");
  child.stdout?.on("data", (chunk: string) => {
    const lines = (stdoutRest + chunk).split(/\r?\n/);
    stdoutRest = lines.pop() ?? "";
    lines.forEach(onLine);
  });
  child.stderr?.setEncoding("utf-8");
  child.stderr?.on("data", (chunk: string) => {
    stderr = (stderr + chunk).slice(-MAX_STDERR_CHARS);
  });

  const finish = (status: LocalSimRun["status"], error: string | null) => {
    if (run.status !== "running") return;
    onLine(stdoutRest);
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
  return run;
}

/** 実行中のシミュレーションを SIGTERM で止める。CLI が書きかけの世代を消してから終了する。 */
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
