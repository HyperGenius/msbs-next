import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  sendFriendRequest,
  acceptFriendRequest,
  rejectFriendRequest,
  removeFriend,
} from "@/services/friends";

vi.mock("@/services/auth", async () => {
  const actual = await vi.importActual<typeof import("@/services/auth")>("@/services/auth");
  return { ...actual, getAuthToken: vi.fn().mockResolvedValue("test-token") };
});

/** 成功レスポンスを生成するヘルパー */
const mockOk = (data: unknown = {}) =>
  ({ ok: true, json: () => Promise.resolve(data) } as unknown as Response);

/** APIエラーレスポンスを生成するヘルパー */
const mockErr = (detail: string, status = 400) =>
  ({
    ok: false,
    status,
    statusText: "Bad Request",
    json: () => Promise.resolve({ detail }),
  } as unknown as Response);

/** テスト用フレンドデータ */
const mockFriend = {
  id: "friend-1",
  user_id: "user-1",
  friend_user_id: "user-2",
  status: "PENDING" as const,
  pilot_name: "シャア",
  created_at: "2024-01-01T00:00:00Z",
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ─────────────────────────────────────────────
// sendFriendRequest — フレンドリクエスト送信
// ─────────────────────────────────────────────
describe("sendFriendRequest", () => {
  it("成功時にFriendレコード（PENDING状態）を返す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk(mockFriend));

    const result = await sendFriendRequest("user-2");

    expect(result.status).toBe("PENDING");
    expect(result.friend_user_id).toBe("user-2");
  });

  it("POSTメソッドとフレンドリクエストエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk(mockFriend));

    await sendFriendRequest("user-2");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/friends/request"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("friend_user_idをJSONボディとして送信する", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk(mockFriend));

    await sendFriendRequest("target-user-id");

    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body.friend_user_id).toBe("target-user-id");
  });

  it("すでにフレンド申請済みの場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("すでにフレンド申請済みです"));

    await expect(sendFriendRequest("user-2")).rejects.toThrow("すでにフレンド申請済みです");
  });
});

// ─────────────────────────────────────────────
// acceptFriendRequest — フレンドリクエスト承認
// ─────────────────────────────────────────────
describe("acceptFriendRequest", () => {
  it("成功時にFriendレコード（ACCEPTED状態）を返す", async () => {
    const acceptedFriend = { ...mockFriend, status: "ACCEPTED" as const };
    vi.mocked(fetch).mockResolvedValue(mockOk(acceptedFriend));

    const result = await acceptFriendRequest("user-2");

    expect(result.status).toBe("ACCEPTED");
  });

  it("POSTメソッドと承認エンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk(mockFriend));

    await acceptFriendRequest("user-2");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/friends/accept"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("対象のリクエストが存在しない場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("フレンドリクエストが見つかりません", 404));

    await expect(acceptFriendRequest("user-2")).rejects.toThrow(
      "フレンドリクエストが見つかりません"
    );
  });
});

// ─────────────────────────────────────────────
// rejectFriendRequest — フレンドリクエスト拒否
// ─────────────────────────────────────────────
describe("rejectFriendRequest", () => {
  it("成功時に何も返さない（void）", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    const result = await rejectFriendRequest("user-2");

    expect(result).toBeUndefined();
  });

  it("POSTメソッドと拒否エンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    await rejectFriendRequest("user-2");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/friends/reject"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("APIエラー時にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("フレンドリクエストが見つかりません", 404));

    await expect(rejectFriendRequest("user-2")).rejects.toThrow(
      "フレンドリクエストが見つかりません"
    );
  });
});

// ─────────────────────────────────────────────
// removeFriend — フレンド解除
// ─────────────────────────────────────────────
describe("removeFriend", () => {
  it("成功時に何も返さない（void）", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    const result = await removeFriend("user-2");

    expect(result).toBeUndefined();
  });

  it("DELETEメソッドと正しいユーザーIDのエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    await removeFriend("user-xyz");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/friends/user-xyz"),
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("フレンド関係が存在しない場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("フレンド関係が見つかりません", 404));

    await expect(removeFriend("user-2")).rejects.toThrow("フレンド関係が見つかりません");
  });
});
