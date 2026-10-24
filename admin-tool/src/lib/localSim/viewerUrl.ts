/* admin-tool/src/lib/localSim/viewerUrl.ts */
// クライアントでも使う。NEXT_PUBLIC_ の環境変数はビルド時に埋め込まれる。

const DEFAULT_DEV_SIM_URL = "http://localhost:3000";

/** `/dev/sim` の URL の基準。環境変数で変えられる。 */
export function devSimBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_DEV_SIM_URL || DEFAULT_DEV_SIM_URL).replace(/\/+$/, "");
}

/** 戦闘の再生 URL。 */
export function battleViewerUrl(generationId: string, battle: number, base = devSimBaseUrl()): string {
  const params = new URLSearchParams({ gen: generationId, battle: String(battle) });
  return `${base}/dev/sim?${params}`;
}

/** 2 世代の比較 URL。 */
export function compareViewerUrl(a: string, b: string, base = devSimBaseUrl()): string {
  const params = new URLSearchParams({ view: "compare", a, b });
  return `${base}/dev/sim?${params}`;
}
