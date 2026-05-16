import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { entryBattle, cancelEntry } from "@/services/entry";

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

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ─────────────────────────────────────────────
// entryBattle — バトルエントリー作成
// ─────────────────────────────────────────────
describe("entryBattle", () => {
  it("成功時にBattleEntryを返す", async () => {
    const mockEntry = {
      id: "entry-1",
      room_id: "room-1",
      mobile_suit_id: "ms-1",
      scheduled_at: "2024-01-01T00:00:00Z",
      created_at: "2024-01-01T00:00:00Z",
    };
    vi.mocked(fetch).mockResolvedValue(mockOk(mockEntry));

    const result = await entryBattle("ms-1");

    expect(result).toEqual(mockEntry);
  });

  it("POSTメソッドとentriesエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await entryBattle("ms-1");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/entries"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("mobile_suit_idをJSONボディとして送信する", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await entryBattle("ms-abc");

    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body.mobile_suit_id).toBe("ms-abc");
  });

  it("Authorizationヘッダーにトークンを付与する", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await entryBattle("ms-1");

    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect((options as RequestInit).headers).toMatchObject({
      Authorization: "Bearer test-token",
    });
  });

  it("すでにエントリー済みの場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("すでにエントリー済みです"));

    await expect(entryBattle("ms-1")).rejects.toThrow("すでにエントリー済みです");
  });
});

// ─────────────────────────────────────────────
// cancelEntry — エントリーキャンセル
// ─────────────────────────────────────────────
describe("cancelEntry", () => {
  it("成功時に何も返さない（void）", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    const result = await cancelEntry();

    expect(result).toBeUndefined();
  });

  it("DELETEメソッドとentriesエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    await cancelEntry();

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/entries"),
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("エントリーが存在しない場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("エントリーが見つかりません", 404));

    await expect(cancelEntry()).rejects.toThrow("エントリーが見つかりません");
  });
});
