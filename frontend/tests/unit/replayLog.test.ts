/* frontend/tests/unit/replayLog.test.ts */
import { describe, it, expect } from "vitest";
import { REPLAY_LOG_VERSION } from "@/types/battle";
import {
  consumeReplayLogHeader,
  isReplayLogHeader,
  toViewerLogs,
  UnsupportedReplayVersionError,
} from "@/utils/replayLog";

const MOVE_ROW = {
  timestamp: 0.1,
  actor_id: "a",
  action_type: "MOVE",
  position_snapshot: { x: 0, y: 0, z: 0 },
};

describe("isReplayLogHeader", () => {
  it("replay_version を持つ行だけをヘッダーとみなす", () => {
    expect(isReplayLogHeader({ replay_version: 1 })).toBe(true);
    expect(isReplayLogHeader(MOVE_ROW)).toBe(false);
    expect(isReplayLogHeader(null)).toBe(false);
    expect(isReplayLogHeader("replay_version")).toBe(false);
  });
});

describe("consumeReplayLogHeader", () => {
  it("対応しているバージョンのヘッダーなら true を返す", () => {
    expect(consumeReplayLogHeader({ replay_version: REPLAY_LOG_VERSION })).toBe(true);
  });

  it("旧形式の行なら false を返す", () => {
    expect(consumeReplayLogHeader({ ...MOVE_ROW, message: "m" })).toBe(false);
  });

  it("未対応のバージョンならバージョンを持つエラーを投げる", () => {
    const read = () => consumeReplayLogHeader({ replay_version: REPLAY_LOG_VERSION + 1 });
    expect(read).toThrow(UnsupportedReplayVersionError);
    try {
      read();
    } catch (error) {
      expect((error as UnsupportedReplayVersionError).version).toBe(REPLAY_LOG_VERSION + 1);
    }
  });
});

describe("toViewerLogs", () => {
  it("配信用ログはヘッダー行を除き、行の中身を変えない", () => {
    const logs = toViewerLogs([{ replay_version: REPLAY_LOG_VERSION }, MOVE_ROW]);
    expect(logs).toEqual([MOVE_ROW]);
    expect(logs[0]).toBe(MOVE_ROW);
  });

  it("旧形式はそのまま返す", () => {
    const row = { ...MOVE_ROW, message: "m", heading: null };
    expect(toViewerLogs([row])).toEqual([row]);
  });

  it("空のログは空のまま返す", () => {
    expect(toViewerLogs([])).toEqual([]);
  });

  it("未対応のバージョンはエラーにする", () => {
    expect(() => toViewerLogs([{ replay_version: 99 }, MOVE_ROW])).toThrow(UnsupportedReplayVersionError);
  });
});
