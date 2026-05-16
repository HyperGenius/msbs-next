import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { unlockSkill } from "@/services/skills";

vi.mock("@/services/auth", async () => {
  const actual = await vi.importActual<typeof import("@/services/auth")>("@/services/auth");
  return { ...actual, getAuthToken: vi.fn().mockResolvedValue("test-token") };
});

/** テスト用パイロットデータ（スキル習得後） */
const mockPilotWithSkill = {
  id: "pilot-1",
  user_id: "user-1",
  name: "アムロ",
  faction: "FEDERATION",
  background: "military",
  level: 5,
  exp: 1000,
  credits: 3000,
  skill_points: 0,
  skills: { "quick_trigger": 1 },
  status_points: 0,
  dex: 7,
  intel: 5,
  ref: 8,
  tou: 5,
  luk: 5,
  awq: 5,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-02T00:00:00Z",
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ─────────────────────────────────────────────
// unlockSkill — スキルの習得またはレベルアップ
// ─────────────────────────────────────────────
describe("unlockSkill", () => {
  it("成功時にSkillUnlockResponseを返す", async () => {
    const mockResponse = {
      pilot: mockPilotWithSkill,
      message: "スキル「クイックトリガー」を習得しました",
    };
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    } as unknown as Response);

    const result = await unlockSkill("quick_trigger");

    expect(result.pilot.skills["quick_trigger"]).toBe(1);
    expect(result.message).toContain("クイックトリガー");
  });

  it("POSTメソッドとスキル習得エンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ pilot: mockPilotWithSkill, message: "習得" }),
    } as unknown as Response);

    await unlockSkill("quick_trigger");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pilots/skills/unlock"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("skill_idをJSONボディとして送信する", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ pilot: mockPilotWithSkill, message: "習得" }),
    } as unknown as Response);

    await unlockSkill("evasion_master");

    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body.skill_id).toBe("evasion_master");
  });

  it("Authorizationヘッダーにトークンを付与する", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ pilot: mockPilotWithSkill, message: "習得" }),
    } as unknown as Response);

    await unlockSkill("quick_trigger");

    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect((options as RequestInit).headers).toMatchObject({
      Authorization: "Bearer test-token",
    });
  });

  it("スキルポイントが不足している場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: () => Promise.resolve({ detail: "スキルポイントが不足しています" }),
    } as unknown as Response);

    await expect(unlockSkill("quick_trigger")).rejects.toThrow("スキルポイントが不足しています");
  });

  it("最大レベルに達したスキルを強化しようとした場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: () => Promise.resolve({ detail: "スキルはすでに最大レベルです" }),
    } as unknown as Response);

    await expect(unlockSkill("quick_trigger")).rejects.toThrow("スキルはすでに最大レベルです");
  });

  it("APIがdetailなしでエラーを返したときフォールバックメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve({}),
    } as unknown as Response);

    await expect(unlockSkill("quick_trigger")).rejects.toThrow("500");
  });
});
