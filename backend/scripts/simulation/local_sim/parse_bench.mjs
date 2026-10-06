// NDJSON のバトルログのパース時間と、パースしたログが保持するヒープを測る。
//
//   node --expose-gc parse_bench.mjs <NDJSON ファイル> <回数>
//
// 結果は JSON で標準出力に書く。log_bench.py から呼ぶ。
import { readFileSync } from "node:fs";
import { performance } from "node:perf_hooks";

// frontend/src/services/battle.ts と同じ値。
const PROGRESSIVE_UPDATE_BATCH_SIZE = 500;
// fetch の reader.read() が返すチャンクの大きさの代わり。
const CHUNK_SIZE = 64 * 1024;

// fetchBattleLogsNdjson() の読み込み処理と同じ手順でパースする。
// onProgress はログの配列をコピーする分だけ再現する（描画の負荷は含めない）。
function parseNdjson(bytes) {
  const logs = [];
  let sinceLastProgress = 0;
  let progressCopies = 0;

  const pushLog = (line) => {
    logs.push(JSON.parse(line));
    sinceLastProgress++;
    if (sinceLastProgress >= PROGRESSIVE_UPDATE_BATCH_SIZE) {
      sinceLastProgress = 0;
      progressCopies += [...logs].length;
    }
  };

  const decoder = new TextDecoder();
  let buffer = "";
  for (let offset = 0; offset < bytes.length; offset += CHUNK_SIZE) {
    buffer += decoder.decode(bytes.subarray(offset, offset + CHUNK_SIZE), { stream: true });
    let newlineIndex = buffer.indexOf("\n");
    while (newlineIndex !== -1) {
      const line = buffer.slice(0, newlineIndex);
      buffer = buffer.slice(newlineIndex + 1);
      if (line.trim().length > 0) {
        pushLog(line);
      }
      newlineIndex = buffer.indexOf("\n");
    }
  }
  buffer += decoder.decode();
  if (buffer.trim().length > 0) {
    pushLog(buffer);
  }
  // コピーを使わないと、最適化でコピーごと消えうる。
  if (progressCopies < 0) {
    throw new Error("unreachable");
  }
  return logs;
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

if (typeof globalThis.gc !== "function") {
  console.error("node --expose-gc で実行してください。");
  process.exit(2);
}

const [path, runsArg] = process.argv.slice(2);
const runs = Number.parseInt(runsArg ?? "5", 10);
const bytes = readFileSync(path);

const parseMs = [];
for (let i = 0; i < runs; i++) {
  globalThis.gc();
  const start = performance.now();
  parseNdjson(bytes);
  parseMs.push(performance.now() - start);
}

globalThis.gc();
const before = process.memoryUsage().heapUsed;
const kept = parseNdjson(bytes);
globalThis.gc();
const heapBytes = process.memoryUsage().heapUsed - before;

console.log(
  JSON.stringify({
    node_version: process.version,
    lines: kept.length,
    parse_ms: parseMs,
    parse_ms_median: median(parseMs),
    heap_bytes: heapBytes,
  })
);
