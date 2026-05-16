import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { updateMobileSuit } from "@/services/mobileSuit";

vi.mock("@/services/auth", async () => {
  const actual = await vi.importActual<typeof import("@/services/auth")>("@/services/auth");
  return { ...actual, getAuthToken: vi.fn().mockResolvedValue("test-token") };
});

/** テスト用機体データ */
const mockMobileSuit = {
  id: "ms-1",
  name: "RX-78-2 ガンダム",
  max_hp: 1200,
  current_hp: 1200,
  armor: 80,
  mobility: 70,
  position: { x: 0, y: 0, z: 0 },
  weapons: [],
  side: "PLAYER" as const,
  tactics: { priority: "CLOSEST" as const, range: "BALANCED" as const },
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ─────────────────────────────────────────────
// updateMobileSuit — 機体データの更新
// ─────────────────────────────────────────────
describe("updateMobileSuit", () => {
  it("成功時に更新後のMobileSuitを返す", async () => {
    const updated = { ...mockMobileSuit, name: "ガンダム改" };
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(updated),
    } as unknown as Response);

    const result = await updateMobileSuit("ms-1", { name: "ガンダム改" });

    expect(result.name).toBe("ガンダム改");
  });

  it("PUTメソッドと正しいIDのエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockMobileSuit),
    } as unknown as Response);

    await updateMobileSuit("ms-abc", { armor: 90 });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/mobile_suits/ms-abc"),
      expect.objectContaining({ method: "PUT" })
    );
  });

  it("更新データをJSONボディとして送信する", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockMobileSuit),
    } as unknown as Response);

    await updateMobileSuit("ms-1", { armor: 95, mobility: 75 });

    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body.armor).toBe(95);
    expect(body.mobility).toBe(75);
  });

  it("Authorizationヘッダーにトークンを付与する", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockMobileSuit),
    } as unknown as Response);

    await updateMobileSuit("ms-1", { name: "テスト" });

    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect((options as RequestInit).headers).toMatchObject({
      Authorization: "Bearer test-token",
    });
  });

  it("APIエラー時に機体IDを含むエラーメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
    } as unknown as Response);

    await expect(updateMobileSuit("ms-missing", { name: "更新" })).rejects.toThrow("ms-missing");
  });

  it("戦術設定のみ更新した場合でも成功する", async () => {
    const updatedMs = {
      ...mockMobileSuit,
      tactics: { priority: "WEAKEST" as const, range: "RANGED" as const },
    };
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(updatedMs),
    } as unknown as Response);

    const result = await updateMobileSuit("ms-1", {
      tactics: { priority: "WEAKEST", range: "RANGED" },
    });

    expect(result.tactics.priority).toBe("WEAKEST");
  });
});
