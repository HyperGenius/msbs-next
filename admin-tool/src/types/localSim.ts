/* admin-tool/src/types/localSim.ts */
// ローカルバトルシミュレータの保存形式のうち、Admin Tool が表示に使う項目。
// backend/scripts/simulation/local_sim/generations.py・analysis.py の Pydantic モデルと項目を揃える。

export interface LocalSimBattleSummary {
  index: number;
  file: string;
  seed: number | null;
  win_loss: "WIN" | "LOSE" | "DRAW";
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
  /** 作戦の名前。作戦の無い世代と古い世代では null か無い */
  mission_name?: string | null;
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
    /** 作戦の引き分け。古い世代には無い */
    draws?: number;
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

/** 作戦の結果（世代の全戦闘の合計） */
export interface LocalSimObjectiveStats {
  mission_name: string | null;
  battles: number;
  success: number;
  failure: number;
  draw: number;
  /** 成功に必要な数。0 は達成度を数えない目標 */
  required: number;
  /** 護衛する友軍の数 */
  total: number;
  /** 達成した数（離脱した友軍の数）の合計 */
  progress: number;
  /** 撃破された友軍の数の合計 */
  lost: number;
}

export interface LocalSimReport {
  generation_id: string;
  battles: number;
  wins: number;
  losses: number;
  timeouts: number;
  elapsed_time: { avg: number; min: number; max: number };
  player_kills: number;
  /** 作戦の引き分け。schema_version 1 の report には無い */
  draws?: number;
  /** 作戦の結果。作戦の無い世代と schema_version 1 の report では null か無い */
  objective?: LocalSimObjectiveStats | null;
  units: LocalSimUnitStats[];
  warnings: string[];
}

export interface LocalSimRosterInfo {
  name: string;
  entries: number;
  theater_id: string | null;
  fetched_at: string | null;
}

/** ロスターの編集対象。backend の `Roster`（roster.py）のうち、編集画面が読み書きする項目 */
export interface LocalSimRoster {
  schema_version: number;
  name: string;
  fetched_at: string;
  conditions: {
    theater_id: string | null;
    environment: string;
    environment_profile: Record<string, unknown> | null;
    environment_name?: string | null;
    minovsky_density: number;
    battlefield: { obstacle_density?: string; [key: string]: unknown };
    [key: string]: unknown;
  };
  entries: LocalSimRosterEntry[];
  mission: { source: string; builder: string | null; master: LocalSimMissionMaster } | null;
  [key: string]: unknown;
}

export interface LocalSimRosterEntry {
  source: { kind: string; mobile_suit_id: string; pilot_name?: string | null; [key: string]: unknown };
  is_npc: boolean;
  snapshot: Record<string, unknown>;
}

/** 作戦マスター（`Mission` の model_dump()）のうち、編集する項目 */
export interface LocalSimMissionMaster {
  name?: string;
  allies_config: LocalSimMissionUnit[] | null;
  enemy_config: { enemies: LocalSimMissionUnit[]; [key: string]: unknown };
  objective: { type: string; params: Record<string, unknown> } | null;
  [key: string]: unknown;
}

/** 作戦の友軍・敵機1機（`MissionUnitConfig`） */
export interface LocalSimMissionUnit {
  name: string;
  max_hp: number;
  armor: number;
  mobility: number;
  terrain_adaptability?: Record<string, string>;
  weapon: {
    id: string;
    name: string;
    power: number;
    range: number;
    accuracy: number;
    weapon_type: string;
    is_melee: boolean;
    fire_arc_deg: number;
    [key: string]: unknown;
  };
  role: string | null;
  squad_id: string | null;
  [key: string]: unknown;
}

export interface LocalSimRunRequest {
  roster: string;
  rounds: number;
  seed?: number | null;
  steps?: number | null;
  label?: string | null;
  pin?: boolean;
}

/** `fetch` の `--ms` / `--pilot` 1 つ分（`ID[:TEAM]`） */
export interface LocalSimUnitSpec {
  id: string;
  /** 同じチーム名の機体と味方になる。省略すると個人戦 */
  team?: string | null;
}

export interface LocalSimFetchRequest {
  /** `--ms`（機体ID） */
  mobile_suits?: LocalSimUnitSpec[];
  /** `--pilot`（pilots.id か user_id。出撃機体を使う） */
  pilots?: LocalSimUnitSpec[];
  npc?: number;
  ace?: number;
  theater?: string | null;
  minovsky?: number | null;
  /** 省略すると CLI が日時から作る */
  name?: string | null;
  /** 同名のロスターを上書きする */
  force?: boolean;
}

export type LocalSimRunStatus = "running" | "succeeded" | "failed" | "cancelled";

interface LocalSimJobBase {
  status: LocalSimRunStatus;
  /** 直近の出力行 */
  lines: string[];
  /** 終了コードが 0 以外のときの標準エラー */
  error: string | null;
  started_at: string;
  finished_at: string | null;
}

/** `local_sim run` の実行 */
export interface LocalSimBattleRun extends LocalSimJobBase {
  kind: "run";
  request: LocalSimRunRequest;
  /** 完了した戦闘数 */
  completed: number;
  /** 成功したときの世代ID */
  generation_id: string | null;
}

/** `local_sim fetch` の実行（ロスター作成） */
export interface LocalSimFetchRun extends LocalSimJobBase {
  kind: "fetch";
  request: LocalSimFetchRequest;
  /** 成功したときのロスター名 */
  roster_name: string | null;
}

/** 子プロセスのジョブ。run と fetch は同時に 1 つだけ動かす */
export type LocalSimRun = LocalSimBattleRun | LocalSimFetchRun;

export interface LocalSimGenerationDetail {
  manifest: LocalSimManifest;
  report: LocalSimReport | null;
}
