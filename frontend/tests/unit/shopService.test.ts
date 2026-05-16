import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  purchaseMobileSuit,
  purchaseWeapon,
  equipWeapon,
  deletePlayerWeapon,
} from "@/services/shop";

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
// purchaseMobileSuit — 機体購入
// ─────────────────────────────────────────────
describe("purchaseMobileSuit", () => {
  it("成功時にPurchaseResponseを返す", async () => {
    const mockResponse = {
      message: "購入完了",
      mobile_suit_id: "ms-new",
      remaining_credits: 5000,
    };
    vi.mocked(fetch).mockResolvedValue(mockOk(mockResponse));

    const result = await purchaseMobileSuit("item-1");

    expect(result).toEqual(mockResponse);
  });

  it("POSTメソッドと正しいアイテムIDのエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await purchaseMobileSuit("item-abc");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/shop/purchase/item-abc"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("クレジット不足の場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("クレジットが不足しています"));

    await expect(purchaseMobileSuit("item-1")).rejects.toThrow("クレジットが不足しています");
  });
});

// ─────────────────────────────────────────────
// purchaseWeapon — 武器購入
// ─────────────────────────────────────────────
describe("purchaseWeapon", () => {
  it("成功時にWeaponPurchaseResponseを返す", async () => {
    const mockResponse = {
      message: "武器購入完了",
      weapon_id: "weapon-1",
      player_weapon_id: "pw-1",
      remaining_credits: 3000,
    };
    vi.mocked(fetch).mockResolvedValue(mockOk(mockResponse));

    const result = await purchaseWeapon("weapon-1");

    expect(result.player_weapon_id).toBe("pw-1");
    expect(result.remaining_credits).toBe(3000);
  });

  it("POSTメソッドと武器購入エンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await purchaseWeapon("weapon-xyz");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/shop/purchase/weapon/weapon-xyz"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("クレジット不足の場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("クレジットが不足しています"));

    await expect(purchaseWeapon("weapon-1")).rejects.toThrow("クレジットが不足しています");
  });
});

// ─────────────────────────────────────────────
// equipWeapon — 武器装備
// ─────────────────────────────────────────────
describe("equipWeapon", () => {
  it("成功時に更新後のMobileSuitを返す", async () => {
    const mockMs = { id: "ms-1", weapons: [{ id: "pw-1", name: "ビームライフル" }] };
    vi.mocked(fetch).mockResolvedValue(mockOk(mockMs));

    const result = await equipWeapon("ms-1", { player_weapon_id: "pw-1" });

    expect(result).toEqual(mockMs);
  });

  it("PUTメソッドとequipエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await equipWeapon("ms-1", { player_weapon_id: "pw-1", slot_index: 0 });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/mobile_suits/ms-1/equip"),
      expect.objectContaining({ method: "PUT" })
    );
  });

  it("スロット番号を指定した場合にリクエストボディに含まれる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({}));

    await equipWeapon("ms-1", { player_weapon_id: "pw-1", slot_index: 2 });

    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body.slot_index).toBe(2);
  });

  it("APIエラー時にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("スロットが満杯です"));

    await expect(
      equipWeapon("ms-1", { player_weapon_id: "pw-1" })
    ).rejects.toThrow("スロットが満杯です");
  });
});

// ─────────────────────────────────────────────
// deletePlayerWeapon — 所有武器の売却・破棄
// ─────────────────────────────────────────────
describe("deletePlayerWeapon", () => {
  it("成功時に何も返さない（void）", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    const result = await deletePlayerWeapon("pw-1");

    expect(result).toBeUndefined();
  });

  it("DELETEメソッドと正しい武器IDのエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    await deletePlayerWeapon("pw-abc");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/player-weapons/pw-abc"),
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("武器が見つからない場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("武器インスタンスが見つかりません", 404));

    await expect(deletePlayerWeapon("pw-1")).rejects.toThrow(
      "武器インスタンスが見つかりません"
    );
  });
});
