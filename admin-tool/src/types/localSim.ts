/* admin-tool/src/types/localSim.ts */
// ローカルバトルシミュレータの保存形式のうち、Admin Tool が表示に使う項目。
// backend/scripts/simulation/local_sim/generations.py・analysis.py の Pydantic モデルと項目を揃える。

export interface LocalSimBattleSummary {
  index: number;
  file: string;
  seed: number | null;
  win_loss: "WIN" | "LOSE";
  kills: number;
  elapsed_time: number;
  steps_used: number;
  timed_out: boolean;
}

export interface LocalSimManifest {
  generation_id: string;
  label: string;
  created_at: string;
  pinned: boolean;
  source?: "local" | "production";
  roster_name: string | null;
  player_name: string | null;
  seed: number | null;
  rounds: number;
  max_steps: number | null;
  theater_id: string | null;
  environment: string;
  summary: {
    battles: number;
    wins: number;
    losses: number;
    timeouts: number;
    total_kills: number;
  };
  battles: LocalSimBattleSummary[];
}

export interface LocalSimUnitStats {
  unit_id: string;
  name: string;
  pilot_name: string | null;
  is_player: boolean;
  battles: number;
  kills: number;
  deaths: number;
}

export interface LocalSimReport {
  generation_id: string;
  battles: number;
  wins: number;
  losses: number;
  timeouts: number;
  elapsed_time: { avg: number; min: number; max: number };
  player_kills: number;
  units: LocalSimUnitStats[];
  warnings: string[];
}

export interface LocalSimRosterInfo {
  name: string;
  entries: number;
  theater_id: string | null;
  fetched_at: string | null;
}

export interface LocalSimRunRequest {
  roster: string;
  rounds: number;
  seed?: number | null;
  steps?: number | null;
  label?: string | null;
  pin?: boolean;
}

export type LocalSimRunStatus = "running" | "succeeded" | "failed" | "cancelled";

export interface LocalSimRun {
  request: LocalSimRunRequest;
  status: LocalSimRunStatus;
  /** 完了した戦闘数 */
  completed: number;
  /** 直近の進捗行 */
  lines: string[];
  /** 終了コードが 0 以外のときの標準エラー */
  error: string | null;
  /** 成功したときの世代ID */
  generation_id: string | null;
  started_at: string;
  finished_at: string | null;
}

export interface LocalSimGenerationDetail {
  manifest: LocalSimManifest;
  report: LocalSimReport | null;
}
