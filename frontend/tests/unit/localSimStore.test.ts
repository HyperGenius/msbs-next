import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  isDevSimEnabled,
  isValidGenerationId,
  listGenerations,
  localSimDir,
  logsToNdjsonStream,
  parseBattleIndex,
  readBattle,
  readManifest,
} from "@/app/api/dev/sim/_lib/localSimStore";
import type { BattleLog } from "@/types/battle";

let root: string;

/** 世代を1つ書く。battles には manifest に載せる戦闘を渡す */
async function writeGeneration(
  id: string,
  createdAt: string,
  battles: { index: number; file: string }[] = []
) {
  const dir = path.join(root, "generations", id);
  await fs.mkdir(dir, { recursive: true });
  const manifest = {
    generation_id: id,
    label: id.split("_")[1] ?? id,
    created_at: createdAt,
    pinned: false,
    battles: battles.map((b) => ({ ...b, seed: 1, win_loss: "WIN" })),
  };
  await fs.writeFile(path.join(dir, "manifest.json"), JSON.stringify(manifest));
  return dir;
}

const log = (timestamp: number): BattleLog => ({
  timestamp,
  actor_id: "a",
  action_type: "MOVE",
  message: `t=${timestamp}`,
  position_snapshot: { x: 0, y: 0, z: 0 },
  fuzzy_scores: { attack: 0.5 },
});

beforeEach(async () => {
  root = await fs.mkdtemp(path.join(os.tmpdir(), "local-sim-"));
});

afterEach(async () => {
  vi.unstubAllEnvs();
  await fs.rm(root, { recursive: true, force: true });
});

describe("isDevSimEnabled", () => {
  it("NODE_ENV が development のときだけ true を返す", () => {
    vi.stubEnv("NODE_ENV", "development");
    expect(isDevSimEnabled()).toBe(true);
    vi.stubEnv("NODE_ENV", "production");
    expect(isDevSimEnabled()).toBe(false);
  });
});

describe("localSimDir", () => {
  it("既定は作業ディレクトリの親の battle_logs/local_sim", () => {
    vi.stubEnv("LOCAL_SIM_DIR", "");
    expect(localSimDir()).toBe(path.resolve(process.cwd(), "..", "battle_logs", "local_sim"));
  });

  it("LOCAL_SIM_DIR があればそれを使う", () => {
    vi.stubEnv("LOCAL_SIM_DIR", "/data/local_sim");
    expect(localSimDir()).toBe(path.resolve("/data/local_sim"));
  });
});

describe("isValidGenerationId / parseBattleIndex", () => {
  it.each(["20261005-213000_before", "20261005-213000_a.b-2"])("%s は使える", (id) => {
    expect(isValidGenerationId(id)).toBe(true);
  });

  it.each(["..", ".tmp-20261005-213000_x", "a/b", "a\\b", "", "_x"])("%s は使えない", (id) => {
    expect(isValidGenerationId(id)).toBe(false);
  });

  it("数字だけを戦闘番号にする", () => {
    expect(parseBattleIndex("12")).toBe(12);
    expect(parseBattleIndex("1.5")).toBeNull();
    expect(parseBattleIndex("../1")).toBeNull();
  });
});

describe("listGenerations", () => {
  it("保存先が無ければ空を返す", async () => {
    expect(await listGenerations(path.join(root, "missing"))).toEqual([]);
  });

  it("新しい順に返し、一時ディレクトリと manifest の無い世代は除く", async () => {
    await writeGeneration("20261001-000000_old", "2026-10-01T00:00:00+09:00");
    await writeGeneration("20261003-000000_new", "2026-10-03T00:00:00+09:00");
    await writeGeneration(".tmp-20261004-000000_tmp", "2026-10-04T00:00:00+09:00");
    await fs.mkdir(path.join(root, "generations", "20261005-000000_empty"));

    const ids = (await listGenerations(root)).map((g) => g.generation_id);
    expect(ids).toEqual(["20261003-000000_new", "20261001-000000_old"]);
  });

  it("世代ID はディレクトリ名にする", async () => {
    const dir = await writeGeneration("20261001-000000_x", "2026-10-01T00:00:00Z");
    await fs.rename(dir, path.join(root, "generations", "20261001-000000_renamed"));
    const [manifest] = await listGenerations(root);
    expect(manifest.generation_id).toBe("20261001-000000_renamed");
  });
});

describe("readManifest", () => {
  it("不正な世代ID では読まない", async () => {
    expect(await readManifest(root, "..")).toBeNull();
  });

  it("local_sim の外を指すシンボリックリンクは読まない", async () => {
    const outside = await fs.mkdtemp(path.join(os.tmpdir(), "outside-"));
    try {
      await fs.writeFile(path.join(outside, "manifest.json"), "{}");
      await fs.mkdir(path.join(root, "generations"), { recursive: true });
      await fs.symlink(outside, path.join(root, "generations", "linked"));
      expect(await readManifest(root, "linked")).toBeNull();
    } finally {
      await fs.rm(outside, { recursive: true, force: true });
    }
  });
});

describe("readBattle", () => {
  it("ログを分け、fuzzy_scores を除いて返す", async () => {
    const dir = await writeGeneration("20261001-000000_x", "2026-10-01T00:00:00Z", [
      { index: 1, file: "battle_001.json" },
    ]);
    const record = { schema_version: 1, index: 1, win_loss: "WIN", logs: [log(0), log(0.1)] };
    await fs.writeFile(path.join(dir, "battle_001.json"), JSON.stringify(record));

    const result = await readBattle(root, "20261001-000000_x", 1);
    expect(result?.battle).toMatchObject({ index: 1, win_loss: "WIN", log_count: 2 });
    expect(result?.battle).not.toHaveProperty("logs");
    expect(result?.logs.map((l) => l.timestamp)).toEqual([0, 0.1]);
    expect(result?.logs[0]).not.toHaveProperty("fuzzy_scores");
  });

  it("manifest に無い戦闘と、不正なファイル名は読まない", async () => {
    const dir = await writeGeneration("20261001-000000_x", "2026-10-01T00:00:00Z", [
      { index: 2, file: "../../secret.json" },
    ]);
    await fs.writeFile(path.join(dir, "battle_001.json"), JSON.stringify({ logs: [] }));

    expect(await readBattle(root, "20261001-000000_x", 1)).toBeNull();
    expect(await readBattle(root, "20261001-000000_x", 2)).toBeNull();
  });

  it("世代が無ければ null を返す", async () => {
    expect(await readBattle(root, "20261001-000000_missing", 1)).toBeNull();
  });
});

describe("logsToNdjsonStream", () => {
  it("1行1件の NDJSON にする", async () => {
    const logs = Array.from({ length: 1201 }, (_, i) => log(i));
    const text = await new Response(logsToNdjsonStream(logs)).text();
    const lines = text.trimEnd().split("\n");
    expect(lines).toHaveLength(1201);
    expect(JSON.parse(lines[1200]).timestamp).toBe(1200);
    expect(text.endsWith("\n")).toBe(true);
  });

  it("ログが無ければ空にする", async () => {
    expect(await new Response(logsToNdjsonStream([])).text()).toBe("");
  });
});
