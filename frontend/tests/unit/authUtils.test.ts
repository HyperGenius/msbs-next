import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { authKey, fetcher, getAuthToken } from "@/services/auth";

// ─────────────────────────────────────────────
// authKey — SWRキー生成ヘルパー
// ─────────────────────────────────────────────
describe("authKey", () => {
  it("isLoaded=true かつ isSignedIn=true のときURLを返す", () => {
    expect(authKey("/api/test", true, true)).toBe("/api/test");
  });

  it("isLoaded=false のときnullを返す（Clerk初期化待ち）", () => {
    expect(authKey("/api/test", false, true)).toBeNull();
  });

  it("isSignedIn=false のときnullを返す（未ログイン）", () => {
    expect(authKey("/api/test", true, false)).toBeNull();
  });

  it("isSignedIn=null のときnullを返す", () => {
    expect(authKey("/api/test", true, null)).toBeNull();
  });

  it("isSignedIn=undefined のときnullを返す", () => {
    expect(authKey("/api/test", true, undefined)).toBeNull();
  });

  it("isLoaded=false かつ isSignedIn=false のときnullを返す", () => {
    expect(authKey("/api/test", false, false)).toBeNull();
  });
});

// ─────────────────────────────────────────────
// getAuthToken — クライアントサイドのトークン取得
// ─────────────────────────────────────────────
describe("getAuthToken", () => {
  it("Node環境（windowが未定義）ではnullを返す", async () => {
    // テスト実行環境はNodeのためwindow.Clerkは存在せずnullになる
    const result = await getAuthToken();
    expect(result).toBeNull();
  });

  it("window.Clerkが存在しない場合はnullを返す", async () => {
    // グローバルにwindowを定義するが、Clerkプロパティは持たせない
    vi.stubGlobal("window", {});
    const result = await getAuthToken();
    expect(result).toBeNull();
    vi.unstubAllGlobals();
  });

  it("window.Clerk.sessionが存在する場合はトークンを返す", async () => {
    vi.stubGlobal("window", {
      Clerk: {
        session: {
          getToken: vi.fn().mockResolvedValue("mock-token-xyz"),
        },
      },
    });
    const result = await getAuthToken();
    expect(result).toBe("mock-token-xyz");
    vi.unstubAllGlobals();
  });
});

// ─────────────────────────────────────────────
// fetcher — 認証不要エンドポイント向けSWRフェッチャー
// ─────────────────────────────────────────────
describe("fetcher", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("正常レスポンスのときJSONを返す", async () => {
    const mockData = [{ id: "1", name: "テスト" }];
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    } as unknown as Response);

    const result = await fetcher("http://127.0.0.1:8000/api/missions");
    expect(result).toEqual(mockData);
  });

  it("レスポンスがok=falseのとき、ステータスコード付きエラーを投げる", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
    } as unknown as Response);

    await expect(fetcher("http://127.0.0.1:8000/api/missions"))
      .rejects.toThrow("404");
  });

  it("エラーオブジェクトにstatusプロパティが付与される", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    } as unknown as Response);

    try {
      await fetcher("http://127.0.0.1:8000/api/test");
    } catch (err) {
      expect((err as { status: number }).status).toBe(500);
    }
  });
});
