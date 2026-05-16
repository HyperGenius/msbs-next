import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { markBattleAsRead } from "@/services/battle";

vi.mock("@/services/auth", async () => {
  const actual = await vi.importActual<typeof import("@/services/auth")>("@/services/auth");
  return { ...actual, getAuthToken: vi.fn().mockResolvedValue("test-token") };
});

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ─────────────────────────────────────────────
// markBattleAsRead — バトル結果を既読にする
// ─────────────────────────────────────────────
describe("markBattleAsRead", () => {
  it("成功時に何も返さない（void）", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    const result = await markBattleAsRead("battle-1");

    expect(result).toBeUndefined();
  });

  it("POSTメソッドとreadエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    await markBattleAsRead("battle-abc");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/battles/battle-abc/read"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("Authorizationヘッダーにトークンを付与する", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    await markBattleAsRead("battle-1");

    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect((options as RequestInit).headers).toMatchObject({
      Authorization: "Bearer test-token",
    });
  });

  it("バトルが見つからない場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: () => Promise.resolve({ detail: "バトル結果が見つかりません" }),
    } as unknown as Response);

    await expect(markBattleAsRead("battle-1")).rejects.toThrow("バトル結果が見つかりません");
  });

  it("APIがdetailなしでエラーを返したときフォールバックメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve({}),
    } as unknown as Response);

    await expect(markBattleAsRead("battle-1")).rejects.toThrow("500");
  });
});
