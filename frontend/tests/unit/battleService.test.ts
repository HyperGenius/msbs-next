import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { markBattleAsRead, fetchBattleLogsNdjson } from "@/services/battle";
import type { BattleLog } from "@/types/battle";

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

// ─────────────────────────────────────────────
// fetchBattleLogsNdjson — NDJSONレスポンスの逐次パース
// ─────────────────────────────────────────────

/** 文字列をチャンクに分割してReadableStreamのbodyを持つResponseを作る */
const mockNdjsonResponse = (text: string, chunkSize = 5): Response => {
  const encoder = new TextEncoder();
  const bytes = encoder.encode(text);
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (let i = 0; i < bytes.length; i += chunkSize) {
        controller.enqueue(bytes.slice(i, i + chunkSize));
      }
      controller.close();
    },
  });
  return { ok: true, body: stream } as unknown as Response;
};

describe("fetchBattleLogsNdjson", () => {
  it("改行区切りのNDJSONを1行ずつパースしてBattleLog配列を返す", async () => {
    const ndjson =
      '{"timestamp":0,"actor_id":"a","action_type":"MOVE","message":"m1","position_snapshot":{"x":0,"y":0,"z":0}}\n' +
      '{"timestamp":1,"actor_id":"b","action_type":"ATTACK","message":"m2","position_snapshot":{"x":1,"y":0,"z":0}}\n';
    vi.mocked(fetch).mockResolvedValue(mockNdjsonResponse(ndjson));

    const logs = await fetchBattleLogsNdjson("http://example.com/logs");

    expect(logs).toHaveLength(2);
    expect(logs[0].action_type).toBe("MOVE");
    expect(logs[1].action_type).toBe("ATTACK");
  });

  it("チャンク境界が行の途中で切れても正しくパースできる", async () => {
    const ndjson = '{"timestamp":0,"actor_id":"a","action_type":"MOVE","message":"long message here","position_snapshot":{"x":0,"y":0,"z":0}}\n';
    // チャンクサイズ1バイトずつに分割し、意図的にJSONの途中でチャンクを跨がせる
    vi.mocked(fetch).mockResolvedValue(mockNdjsonResponse(ndjson, 1));

    const logs = await fetchBattleLogsNdjson("http://example.com/logs");

    expect(logs).toHaveLength(1);
    expect(logs[0].message).toBe("long message here");
  });

  it("末尾に改行が無い最終行も取りこぼさずパースする", async () => {
    const ndjson = '{"timestamp":0,"actor_id":"a","action_type":"WAIT","message":"no trailing newline","position_snapshot":{"x":0,"y":0,"z":0}}';
    vi.mocked(fetch).mockResolvedValue(mockNdjsonResponse(ndjson));

    const logs = await fetchBattleLogsNdjson("http://example.com/logs");

    expect(logs).toHaveLength(1);
    expect(logs[0].message).toBe("no trailing newline");
  });

  it("末尾のマルチバイト文字が1バイトずつのチャンクに分割されても正しくデコードされる", async () => {
    // 末尾のメッセージを日本語（UTF-8で3バイト/文字）にし、1バイト単位のチャンクで
    // 配信させる（改行なし）。TextDecoderのstream:trueは未完成のマルチバイト列を
    // 呼び出しをまたいで正しく繰り越すため、この分割自体で文字化けは起きないが、
    // 末尾のdecoder.decode()終端処理を含めても結果が変わらないことを確認する。
    const ndjson = '{"timestamp":0,"actor_id":"a","action_type":"WAIT","message":"戦闘終了","position_snapshot":{"x":0,"y":0,"z":0}}';
    vi.mocked(fetch).mockResolvedValue(mockNdjsonResponse(ndjson, 1));

    const logs = await fetchBattleLogsNdjson("http://example.com/logs");

    expect(logs).toHaveLength(1);
    expect(logs[0].message).toBe("戦闘終了");
  });

  it("空のレスポンス（ログ無し）で空配列を返す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockNdjsonResponse(""));

    const logs = await fetchBattleLogsNdjson("http://example.com/logs");

    expect(logs).toEqual([]);
  });

  it("res.bodyが無い環境ではres.text()にフォールバックしてパースする", async () => {
    const ndjson =
      '{"timestamp":0,"actor_id":"a","action_type":"MOVE","message":"m1","position_snapshot":{"x":0,"y":0,"z":0}}\n';
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      body: null,
      text: () => Promise.resolve(ndjson),
    } as unknown as Response);

    const logs = await fetchBattleLogsNdjson("http://example.com/logs");

    expect(logs).toHaveLength(1);
    expect(logs[0].action_type).toBe("MOVE");
  });

  it("エラーレスポンス時はstatusを含む例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
    } as unknown as Response);

    await expect(fetchBattleLogsNdjson("http://example.com/logs")).rejects.toThrow("404");
  });

  // ─────────────────────────────────────────────
  // onProgress — 全件パース完了を待たない段階的な反映（Issue #494）
  // ─────────────────────────────────────────────

  it("onProgressに500行ごとにその時点までのログ配列を通知する", async () => {
    const lineCount = 1200;
    const ndjson = Array.from({ length: lineCount }, (_, i) =>
      `{"timestamp":${i},"actor_id":"a","action_type":"MOVE","message":"m${i}","position_snapshot":{"x":0,"y":0,"z":0}}`
    ).join("\n") + "\n";
    vi.mocked(fetch).mockResolvedValue(mockNdjsonResponse(ndjson, 4096));

    const onProgress = vi.fn();
    const logs = await fetchBattleLogsNdjson("http://example.com/logs", onProgress);

    expect(logs).toHaveLength(lineCount);
    // 500行ごとに通知されるため、1200行なら2回（500件目・1000件目）呼ばれる
    expect(onProgress).toHaveBeenCalledTimes(2);
    expect(onProgress.mock.calls[0][0]).toHaveLength(500);
    expect(onProgress.mock.calls[1][0]).toHaveLength(1000);
  });

  it("onProgressに渡す配列は呼び出しごとに独立したコピーである", async () => {
    const lineCount = 1000;
    const ndjson = Array.from({ length: lineCount }, (_, i) =>
      `{"timestamp":${i},"actor_id":"a","action_type":"MOVE","message":"m${i}","position_snapshot":{"x":0,"y":0,"z":0}}`
    ).join("\n") + "\n";
    vi.mocked(fetch).mockResolvedValue(mockNdjsonResponse(ndjson, 4096));

    const snapshots: BattleLog[][] = [];
    await fetchBattleLogsNdjson("http://example.com/logs", (partial) => {
      snapshots.push(partial);
    });

    // 後続のpushで先に通知済みの配列の中身・長さが書き換わっていないことを確認する
    expect(snapshots.map((s) => s.length)).toEqual([500, 1000]);
    expect(snapshots[0]).toHaveLength(500);
  });

  it("行数がバッチサイズ未満の場合はonProgressが呼ばれない（最終返り値には全件含まれる）", async () => {
    const ndjson =
      '{"timestamp":0,"actor_id":"a","action_type":"MOVE","message":"m1","position_snapshot":{"x":0,"y":0,"z":0}}\n';
    vi.mocked(fetch).mockResolvedValue(mockNdjsonResponse(ndjson));

    const onProgress = vi.fn();
    const logs = await fetchBattleLogsNdjson("http://example.com/logs", onProgress);

    expect(onProgress).not.toHaveBeenCalled();
    expect(logs).toHaveLength(1);
  });
});
