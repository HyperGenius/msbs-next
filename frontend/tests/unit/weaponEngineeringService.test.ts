import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  upgradePlayerWeapon,
  getWeaponUpgradePreview,
  updatePlayerWeaponAimDistribution,
} from "@/services/weaponEngineering";

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
// upgradePlayerWeapon — 武器の custom_stats 改造
// ─────────────────────────────────────────────
describe("upgradePlayerWeapon", () => {
  it("成功時にWeaponUpgradeResponseを返す", async () => {
    const mockResponse = {
      message: "武器を改造しました！",
      player_weapon: { id: "pw-1", custom_stats: { power_bonus: 5 } },
      remaining_credits: 940,
      cost_paid: 60,
    };
    vi.mocked(fetch).mockResolvedValue(mockOk(mockResponse));

    const result = await upgradePlayerWeapon("pw-1", { target_stat: "power_bonus" });

    expect(result).toEqual(mockResponse);
  });

  it("POSTメソッドと正しいエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await upgradePlayerWeapon("pw-1", { target_stat: "accuracy_bonus" });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/player-weapons/pw-1/upgrade"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("Authorizationヘッダーにトークンを付与する", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await upgradePlayerWeapon("pw-1", { target_stat: "power_bonus" });

    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect((options as RequestInit).headers).toMatchObject({
      Authorization: "Bearer test-token",
    });
  });

  it("target_statとstepsをJSONボディとして送信する", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await upgradePlayerWeapon("pw-1", { target_stat: "power_bonus", steps: 3 });

    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body).toEqual({ target_stat: "power_bonus", steps: 3 });
  });

  it("APIがエラーを返したときdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("威力は既に上限に達しています"));

    await expect(
      upgradePlayerWeapon("pw-1", { target_stat: "power_bonus" })
    ).rejects.toThrow("威力は既に上限に達しています");
  });

  it("APIがdetailなしでエラーを返したときフォールバックメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve({}),
    } as unknown as Response);

    await expect(
      upgradePlayerWeapon("pw-1", { target_stat: "power_bonus" })
    ).rejects.toThrow("500");
  });
});

// ─────────────────────────────────────────────
// getWeaponUpgradePreview — 改造前のコスト・効果プレビュー
// ─────────────────────────────────────────────
describe("getWeaponUpgradePreview", () => {
  it("成功時にWeaponUpgradePreviewを返す", async () => {
    const mockPreview = {
      player_weapon_id: "pw-1",
      stat_type: "power_bonus",
      current_value: 0,
      new_value: 5,
      cost: 60,
      at_max_cap: false,
    };
    vi.mocked(fetch).mockResolvedValue(mockOk(mockPreview));

    const result = await getWeaponUpgradePreview("pw-1", "power_bonus");

    expect(result).toEqual(mockPreview);
  });

  it("URLにplayerWeaponIdとstatTypeを含めてGETリクエストする", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await getWeaponUpgradePreview("pw-abc", "accuracy_bonus");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/player-weapons/pw-abc/upgrade-preview/accuracy_bonus"),
      expect.any(Object)
    );
  });

  it("at_max_cap=trueのとき上限到達状態を正しく返す", async () => {
    vi.mocked(fetch).mockResolvedValue(
      mockOk({ at_max_cap: true, cost: 0, current_value: 100, new_value: 100 })
    );

    const result = await getWeaponUpgradePreview("pw-1", "power_bonus");

    expect(result.at_max_cap).toBe(true);
  });

  it("APIエラー時にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("武器インスタンスが見つかりません"));

    await expect(getWeaponUpgradePreview("pw-1", "power_bonus")).rejects.toThrow(
      "武器インスタンスが見つかりません"
    );
  });
});

// ─────────────────────────────────────────────
// updatePlayerWeaponAimDistribution — 狙う部位配分（ユーザー戦術設定）の更新 (Issue #505)
// ─────────────────────────────────────────────
describe("updatePlayerWeaponAimDistribution", () => {
  const distribution = {
    HEAD: 0.1,
    TORSO: 0.5,
    RIGHT_ARM: 0.1,
    LEFT_ARM: 0.1,
    RIGHT_LEG: 0.1,
    LEFT_LEG: 0.1,
  };

  it("成功時に更新後のPlayerWeaponを返す", async () => {
    const mockResponse = {
      id: "pw-1",
      custom_stats: { aim_distribution: distribution },
    };
    vi.mocked(fetch).mockResolvedValue(mockOk(mockResponse));

    const result = await updatePlayerWeaponAimDistribution("pw-1", {
      aim_distribution: distribution,
    });

    expect(result).toEqual(mockResponse);
  });

  it("PUTメソッドと正しいエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await updatePlayerWeaponAimDistribution("pw-1", { aim_distribution: distribution });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/player-weapons/pw-1/aim-distribution"),
      expect.objectContaining({ method: "PUT" })
    );
  });

  it("Authorizationヘッダーにトークンを付与する", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await updatePlayerWeaponAimDistribution("pw-1", { aim_distribution: distribution });

    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect((options as RequestInit).headers).toMatchObject({
      Authorization: "Bearer test-token",
    });
  });

  it("aim_distributionをJSONボディとして送信する", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await updatePlayerWeaponAimDistribution("pw-1", { aim_distribution: distribution });

    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body).toEqual({ aim_distribution: distribution });
  });

  it("APIがエラーを返したときdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("配分の合計は100%にしてください（現在の合計: 90.0%）"));

    await expect(
      updatePlayerWeaponAimDistribution("pw-1", { aim_distribution: distribution })
    ).rejects.toThrow("配分の合計は100%にしてください（現在の合計: 90.0%）");
  });

  it("APIがdetailなしでエラーを返したときフォールバックメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve({}),
    } as unknown as Response);

    await expect(
      updatePlayerWeaponAimDistribution("pw-1", { aim_distribution: distribution })
    ).rejects.toThrow("500");
  });
});
