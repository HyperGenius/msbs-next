import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  createTeam,
  inviteTeamMember,
  toggleTeamReady,
  leaveTeam,
  teamEntry,
} from "@/services/teams";

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

/** テスト用チームデータ */
const mockTeam = {
  id: "team-1",
  owner_user_id: "user-1",
  name: "第1MS小隊",
  status: "FORMING" as const,
  members: [{ user_id: "user-1", is_ready: false, joined_at: "2024-01-01T00:00:00Z" }],
  created_at: "2024-01-01T00:00:00Z",
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ─────────────────────────────────────────────
// createTeam — チーム作成
// ─────────────────────────────────────────────
describe("createTeam", () => {
  it("成功時にTeamを返す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk(mockTeam));

    const result = await createTeam("第1MS小隊");

    expect(result.name).toBe("第1MS小隊");
    expect(result.status).toBe("FORMING");
  });

  it("POSTメソッドとチーム作成エンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk(mockTeam));

    await createTeam("テストチーム");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/teams/create"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("チーム名をJSONボディとして送信する", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk(mockTeam));

    await createTeam("ア・バオア・クー攻略隊");

    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body.name).toBe("ア・バオア・クー攻略隊");
  });

  it("すでにチームに所属している場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("すでにチームに所属しています"));

    await expect(createTeam("新チーム")).rejects.toThrow("すでにチームに所属しています");
  });
});

// ─────────────────────────────────────────────
// inviteTeamMember — チームへのメンバー招待
// ─────────────────────────────────────────────
describe("inviteTeamMember", () => {
  it("成功時に更新後のTeamを返す", async () => {
    const updatedTeam = {
      ...mockTeam,
      members: [
        ...mockTeam.members,
        { user_id: "user-2", is_ready: false, joined_at: "2024-01-01T00:00:00Z" },
      ],
    };
    vi.mocked(fetch).mockResolvedValue(mockOk(updatedTeam));

    const result = await inviteTeamMember("team-1", "user-2");

    expect(result.members).toHaveLength(2);
  });

  it("POSTメソッドと招待エンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk(mockTeam));

    await inviteTeamMember("team-1", "user-2");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/teams/team-1/invite"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("招待対象のuser_idをJSONボディとして送信する", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk(mockTeam));

    await inviteTeamMember("team-1", "user-xyz");

    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body.user_id).toBe("user-xyz");
  });

  it("チームが満員の場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("チームが満員です"));

    await expect(inviteTeamMember("team-1", "user-2")).rejects.toThrow("チームが満員です");
  });
});

// ─────────────────────────────────────────────
// toggleTeamReady — Ready状態のトグル
// ─────────────────────────────────────────────
describe("toggleTeamReady", () => {
  it("成功時にReady状態が更新されたTeamを返す", async () => {
    const readyTeam = {
      ...mockTeam,
      members: [{ user_id: "user-1", is_ready: true, joined_at: "2024-01-01T00:00:00Z" }],
    };
    vi.mocked(fetch).mockResolvedValue(mockOk(readyTeam));

    const result = await toggleTeamReady("team-1");

    expect(result.members[0].is_ready).toBe(true);
  });

  it("POSTメソッドとreadyエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk(mockTeam));

    await toggleTeamReady("team-abc");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/teams/team-abc/ready"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("チームが見つからない場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("チームが見つかりません", 404));

    await expect(toggleTeamReady("team-1")).rejects.toThrow("チームが見つかりません");
  });
});

// ─────────────────────────────────────────────
// leaveTeam — チーム離脱
// ─────────────────────────────────────────────
describe("leaveTeam", () => {
  it("成功時に何も返さない（void）", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    const result = await leaveTeam("team-1");

    expect(result).toBeUndefined();
  });

  it("DELETEメソッドとleaveエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    await leaveTeam("team-1");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/teams/team-1/leave"),
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("チームに所属していない場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("このチームのメンバーではありません", 403));

    await expect(leaveTeam("team-1")).rejects.toThrow("このチームのメンバーではありません");
  });
});

// ─────────────────────────────────────────────
// teamEntry — チーム一括バトルエントリー
// ─────────────────────────────────────────────
describe("teamEntry", () => {
  it("成功時にTeamEntryResponseを返す", async () => {
    const mockResponse = {
      message: "チームエントリー完了",
      entry_ids: ["entry-1", "entry-2"],
      room_id: "room-1",
    };
    vi.mocked(fetch).mockResolvedValue(mockOk(mockResponse));

    const result = await teamEntry({ team_id: "team-1", mobile_suit_id: "ms-1" });

    expect(result.entry_ids).toHaveLength(2);
    expect(result.room_id).toBe("room-1");
  });

  it("POSTメソッドとエントリーエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({ entry_ids: [], room_id: "room-1" }));

    await teamEntry({ team_id: "team-1", mobile_suit_id: "ms-1" });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/teams/entry"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("team_idとmobile_suit_idをJSONボディとして送信する", async () => {
    vi.mocked(fetch).mockResolvedValue(mockOk({ entry_ids: [], room_id: "room-1" }));

    await teamEntry({ team_id: "team-abc", mobile_suit_id: "ms-xyz" });

    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body.team_id).toBe("team-abc");
    expect(body.mobile_suit_id).toBe("ms-xyz");
  });

  it("メンバーが全員Readyでない場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErr("全メンバーがReady状態ではありません"));

    await expect(
      teamEntry({ team_id: "team-1", mobile_suit_id: "ms-1" })
    ).rejects.toThrow("全メンバーがReady状態ではありません");
  });
});
