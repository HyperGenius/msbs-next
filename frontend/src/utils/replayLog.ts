/* frontend/src/utils/replayLog.ts */
import { BattleLog, REPLAY_LOG_VERSION, ReplayLogHeader } from "@/types/battle";

/** ビューアが読めない `replay_version` の配信用ログを受け取ったときのエラー。 */
export class UnsupportedReplayVersionError extends Error {
  readonly version: unknown;

  constructor(version: unknown) {
    super(`未対応の配信用ログのバージョンです: ${String(version)}`);
    this.name = "UnsupportedReplayVersionError";
    this.version = version;
  }
}

/** 配信用ログの先頭行かどうかを返す。旧形式の行は `replay_version` を持たない。 */
export function isReplayLogHeader(entry: unknown): entry is ReplayLogHeader {
  return typeof entry === "object" && entry !== null && "replay_version" in entry;
}

/**
 * ログの先頭行を調べ、取り除くべきヘッダー行なら true を返す。
 * 旧形式の行なら false を返す。
 *
 * 新しいバージョンの読み方はこのビューアが知らない。そのまま描画すると表示が崩れるため、エラーにする。
 *
 * @throws UnsupportedReplayVersionError ヘッダーのバージョンが `REPLAY_LOG_VERSION` と違うとき
 */
export function consumeReplayLogHeader(firstEntry: unknown): boolean {
  if (!isReplayLogHeader(firstEntry)) return false;
  if (firstEntry.replay_version !== REPLAY_LOG_VERSION) {
    throw new UnsupportedReplayVersionError(firstEntry.replay_version);
  }
  return true;
}

/**
 * 配信用ログと旧形式のどちらかを、ビューアに渡すログにする。
 * 配信用ログならヘッダー行を除く。行の中身は変えない。
 *
 * 省いた項目（`undefined`）と旧形式の `null` は、ビューアの部品がどちらも「値が無い」と読む。
 */
export function toViewerLogs(entries: readonly unknown[]): BattleLog[] {
  const rows = entries.length > 0 && consumeReplayLogHeader(entries[0]) ? entries.slice(1) : entries;
  return rows as BattleLog[];
}
