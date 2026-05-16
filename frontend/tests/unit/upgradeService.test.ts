import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { upgradeMobileSuit, bulkUpgradeMobileSuit, getUpgradePreview } from "@/services/upgrades";

// getAuthToken をモックしてテスト用トークンを注入する
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
// upgradeMobileSuit — 単体ステータス強化
// ─────────────────────────────────────────────
describe("upgradeMobileSuit", () => {
  it("成功時にUpgradeResponseを返す", async () => {
    const mockResponse = {
      message: "HPを強化しました",
      mobile_suit: { id: "ms-1", max_hp: 1100 },
      remaining_credits: 900,
      cost_paid: 100,
    };
    vi.mocked(fetch).mockResolvedValue(mockOk(mockResponse));

    const result = await upgradeMobileSuit({ mobile_suit_id: "ms-1", target_stat: "hp" });

    expect(result).toEqual(mockResponse);
  });

  it("POSTメソッドと正しいエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await upgradeMobileSuit({ mobile_suit_id: "ms-1", target_stat: "armor" });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/engineering/upgrade"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("Authorizationヘッダーにトークンを付与する", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await upgradeMobileSuit({ mobile_suit_id: "ms-1", target_stat: "hp" });

    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect((options as RequestInit).headers).toMatchObject({
      Authorization: "Bearer test-token",
    });
  });

  it("APIがエラーを返したときdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("クレジットが不足しています"));

    await expect(
      upgradeMobileSuit({ mobile_suit_id: "ms-1", target_stat: "hp" })
    ).rejects.toThrow("クレジットが不足しています");
  });

  it("APIがdetailなしでエラーを返したときフォールバックメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve({}),
    } as unknown as Response);

    await expect(
      upgradeMobileSuit({ mobile_suit_id: "ms-1", target_stat: "hp" })
    ).rejects.toThrow("500");
  });
});

// ─────────────────────────────────────────────
// bulkUpgradeMobileSuit — 複数ステータス一括強化
// ─────────────────────────────────────────────
describe("bulkUpgradeMobileSuit", () => {
  it("成功時にBulkUpgradeResponseを返す", async () => {
    const mockResponse = {
      message: "一括強化完了",
      mobile_suit: { id: "ms-1" },
      remaining_credits: 500,
      total_cost_paid: 500,
    };
    vi.mocked(fetch).mockResolvedValue(mockOk(mockResponse));

    const result = await bulkUpgradeMobileSuit({
      mobile_suit_id: "ms-1",
      upgrades: { hp: 2, armor: 1 },
    });

    expect(result).toEqual(mockResponse);
  });

  it("POSTメソッドとbulk-upgradeエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await bulkUpgradeMobileSuit({ mobile_suit_id: "ms-1", upgrades: { hp: 1 } });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/engineering/bulk-upgrade"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("upgradesオブジェクトをJSONボディとして送信する", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));
    const upgrades = { hp: 3, mobility: 2 };

    await bulkUpgradeMobileSuit({ mobile_suit_id: "ms-1", upgrades });

    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body.upgrades).toEqual(upgrades);
  });

  it("APIエラー時にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("強化上限に達しています"));

    await expect(
      bulkUpgradeMobileSuit({ mobile_suit_id: "ms-1", upgrades: { hp: 1 } })
    ).rejects.toThrow("強化上限に達しています");
  });
});

// ─────────────────────────────────────────────
// getUpgradePreview — 強化前のコスト・効果プレビュー
// ─────────────────────────────────────────────
describe("getUpgradePreview", () => {
  it("成功時にUpgradePreviewを返す", async () => {
    const mockPreview = {
      mobile_suit_id: "ms-1",
      stat_type: "hp",
      current_value: 1000,
      new_value: 1100,
      cost: 150,
      at_max_cap: false,
    };
    vi.mocked(fetch).mockResolvedValue(mockOk(mockPreview));

    const result = await getUpgradePreview("ms-1", "hp");

    expect(result).toEqual(mockPreview);
  });

  it("URLにmobileSuitIdとstatTypeを含めてGETリクエストする", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await getUpgradePreview("ms-abc", "armor");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/engineering/preview/ms-abc/armor"),
      expect.any(Object)
    );
  });

  it("at_max_cap=trueのとき上限到達状態を正しく返す", async () => {
    vi.mocked(fetch).mockResolvedValue(
      mockOk({ at_max_cap: true, cost: 0, current_value: 9999, new_value: 9999 })
    );

    const result = await getUpgradePreview("ms-1", "hp");

    expect(result.at_max_cap).toBe(true);
  });

  it("APIエラー時にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("機体が見つかりません"));

    await expect(getUpgradePreview("ms-1", "hp")).rejects.toThrow("機体が見つかりません");
  });
});
