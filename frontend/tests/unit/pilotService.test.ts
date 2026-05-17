import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { registerPilot, allocateStatusPoints, updatePilotName, resetAccount } from "@/services/pilot";

vi.mock("@/services/auth", async () => {
  const actual = await vi.importActual<typeof import("@/services/auth")>("@/services/auth");
  return { ...actual, getAuthToken: vi.fn().mockResolvedValue("test-token") };
});

/** 成功レスポンスを生成するヘルパー */
const mockOk = (data: unknown) =>
  ({ ok: true, json: () => Promise.resolve(data) } as unknown as Response);

/** APIエラーレスポンスを生成するヘルパー */
const mockErr = (detail: string, status = 400) =>
  ({
    ok: false,
    status,
    statusText: "Bad Request",
    json: () => Promise.resolve({ detail }),
  } as unknown as Response);

/** テスト用パイロットデータ */
const mockPilot = {
  id: "pilot-1",
  user_id: "user-1",
  name: "アムロ",
  faction: "FEDERATION",
  background: "military",
  level: 1,
  exp: 0,
  credits: 1000,
  skill_points: 0,
  skills: {},
  status_points: 0,
  sht: 5,
  mel: 5,
  intel: 5,
  ref: 5,
  tou: 5,
  luk: 5,
  awq: 5,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ─────────────────────────────────────────────
// registerPilot — 新規パイロット登録（オンボーディング）
// ─────────────────────────────────────────────
describe("registerPilot", () => {
  it("成功時にパイロット情報と機体IDを返す", async () => {
    const mockResponse = {
      pilot: mockPilot,
      mobile_suit_id: "ms-1",
      message: "登録完了",
    };
    vi.mocked(fetch).mockResolvedValue(mockOk(mockResponse));

    const result = await registerPilot("アムロ", "FEDERATION", "military", {
      bonus_sht: 1,
      bonus_mel: 1,
      bonus_int: 1,
      bonus_ref: 1,
      bonus_tou: 0,
      bonus_luk: 1,
    });

    expect(result.pilot.name).toBe("アムロ");
    expect(result.mobile_suit_id).toBe("ms-1");
  });

  it("POSTメソッドとregisterエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({ pilot: mockPilot, mobile_suit_id: "ms-1" }));

    await registerPilot("アムロ", "ZEON", "test", {
      bonus_sht: 1,
      bonus_mel: 0,
      bonus_int: 1,
      bonus_ref: 1,
      bonus_tou: 1,
      bonus_luk: 1,
    });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pilots/register"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("名前・勢力・経歴・ボーナスをJSONボディとして送信する", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({ pilot: mockPilot, mobile_suit_id: "ms-1" }));

    await registerPilot("テスト太郎", "FEDERATION", "civilian", {
      bonus_sht: 2,
      bonus_mel: 1,
      bonus_int: 1,
      bonus_ref: 0,
      bonus_tou: 1,
      bonus_luk: 0,
    });

    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body.name).toBe("テスト太郎");
    expect(body.faction).toBe("FEDERATION");
    expect(body.bonus_sht).toBe(2);
  });

  it("名前が重複している場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("そのパイロット名はすでに使用されています"));

    await expect(
      registerPilot("重複", "FEDERATION", "test", {
        bonus_sht: 1,
        bonus_mel: 0,
        bonus_int: 1,
        bonus_ref: 1,
        bonus_tou: 1,
        bonus_luk: 1,
      })
    ).rejects.toThrow("そのパイロット名はすでに使用されています");
  });
});

// ─────────────────────────────────────────────
// allocateStatusPoints — ステータスポイント割り振り
// ─────────────────────────────────────────────
describe("allocateStatusPoints", () => {
  it("成功時に更新後のパイロット情報を返す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({ ...mockPilot, sht: 8 }));

    const result = await allocateStatusPoints({ sht: 3 });

    expect(result.sht).toBe(8);
  });

  it("未指定のステータスは0として送信する", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk(mockPilot));

    await allocateStatusPoints({ sht: 2 });

    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    // 指定していないステータスは0で送信される（APIが部分更新非対応のため）
    expect(body.mel).toBe(0);
    expect(body.intel).toBe(0);
    expect(body.ref).toBe(0);
    expect(body.tou).toBe(0);
    expect(body.luk).toBe(0);
  });

  it("ポイント不足の場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("割り振り可能なポイントが不足しています"));

    await expect(allocateStatusPoints({ sht: 99 })).rejects.toThrow(
      "割り振り可能なポイントが不足しています"
    );
  });
});

// ─────────────────────────────────────────────
// updatePilotName — パイロット名変更
// ─────────────────────────────────────────────
describe("updatePilotName", () => {
  it("成功時に更新後のパイロット情報を返す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({ ...mockPilot, name: "シャア" }));

    const result = await updatePilotName("シャア");

    expect(result.name).toBe("シャア");
  });

  it("PUTメソッドとname更新エンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk(mockPilot));

    await updatePilotName("新しい名前");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pilots/me/name"),
      expect.objectContaining({ method: "PUT" })
    );
  });

  it("名前が重複している場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("その名前はすでに使用されています"));

    await expect(updatePilotName("重複名")).rejects.toThrow(
      "その名前はすでに使用されています"
    );
  });
});

// ─────────────────────────────────────────────
// resetAccount — アカウントリセット（デバッグ用）
// ─────────────────────────────────────────────
describe("resetAccount", () => {
  it("成功時に何も返さない（void）", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    const result = await resetAccount();

    expect(result).toBeUndefined();
  });

  it("DELETEメソッドとme削除エンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    await resetAccount();

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pilots/me"),
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("APIエラー時にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("パイロットが見つかりません", 404));

    await expect(resetAccount()).rejects.toThrow("パイロットが見つかりません");
  });
});
