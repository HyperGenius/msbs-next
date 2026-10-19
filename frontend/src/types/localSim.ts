/* frontend/src/types/localSim.ts */
import { DetectionSummary, PartHitSummary, WeaponAccuracyRecord } from "./battleCore";
import { Obstacle } from "./geometry";
import { MobileSuit } from "./mobileSuit";

// ローカルシミュレーションの保存形式。
// backend/scripts/simulation/local_sim/generations.py・analysis.py の Pydantic モデルと項目を揃える。

/** 1戦の勝敗。`manifest.json` の `battles` の1件 */
export interface LocalSimBattleSummary {
    /** 1 始まりの戦闘番号 */
    index: number;
    file: string;
    /** 戦闘のシード。本番から取得した戦闘では null */
    seed: number | null;
    win_loss: "WIN" | "LOSE";
    kills: number;
    /** 戦闘の経過時間（秒） */
    elapsed_time: number;
    steps_used: number;
    /** 最大ステップ数で打ち切ったか */
    timed_out: boolean;
}

/** 世代全体の勝敗 */
export interface LocalSimGenerationSummary {
    battles: number;
    wins: number;
    losses: number;
    timeouts: number;
    total_kills: number;
}

/** 世代の出どころ。local は `run` で実行、production は `fetch-log` で本番から取得 */
export type LocalSimSource = "local" | "production";

/** 1回の `run` の実行条件と勝敗、または `fetch-log` で取得した本番の戦闘（`manifest.json`） */
export interface LocalSimManifest {
    schema_version: number;
    /** 世代ディレクトリの名前 */
    generation_id: string;
    label: string;
    created_at: string;
    pinned: boolean;
    /** 古い世代には無い。無いときは local */
    source?: LocalSimSource;
    /** 本番から取得した世代の、取得元のバトル結果ID */
    source_battle_result_id?: string | null;
    /** 本番から取得した世代の、取得元のルームID */
    source_room_id?: string | null;
    /** 本番から取得した世代では null */
    roster_name: string | null;
    player_name: string | null;
    /** 1戦目のシード。本番から取得した世代では null */
    seed: number | null;
    rounds: number;
    /** 本番から取得した世代では null */
    max_steps: number | null;
    git: { commit: string | null; dirty: boolean | null };
    /** backend/data/fuzzy_rules/ の全ファイルの SHA-256。本番から取得した世代では null */
    fuzzy_rules_hash: string | null;
    theater_id: string | null;
    environment: string;
    minovsky_density: number;
    summary: LocalSimGenerationSummary;
    battles: LocalSimBattleSummary[];
}

/** `battle_NNN.json` からログを除いたもの。ログは NDJSON で別に取得する */
export interface LocalSimBattle {
    index: number;
    seed: number | null;
    win_loss: "WIN" | "LOSE";
    kills: number;
    elapsed_time: number;
    steps_used: number;
    timed_out: boolean;
    environment: string;
    theater_id: string | null;
    theater_name: string | null;
    environment_name: string | null;
    viewer_preset: string | null;
    minovsky_density: number;
    player_info: MobileSuit;
    enemies_info: MobileSuit[];
    obstacles_info: Obstacle[];
    map_bounds: [number, number];
    /** 結果画面の戦果サマリー。項目を足す前に保存した世代では無い */
    part_hit_summary?: PartHitSummary | null;
    weapon_accuracy_summary?: WeaponAccuracyRecord[] | null;
    detection_summary?: DetectionSummary | null;
    log_count: number;
}

/** 世代一覧の API の応答 */
export interface LocalSimGenerationList {
    /** 読み込み元のディレクトリ（絶対パス） */
    root: string;
    /** 新しい順 */
    generations: LocalSimManifest[];
}

/** analysis.py の REPORT_SCHEMA_VERSION。違う report.json は CLI の report で作り直す */
export const LOCAL_SIM_REPORT_SCHEMA_VERSION = 1;

/** 1機の撃墜数と被撃墜数（世代の全戦闘の合計） */
export interface LocalSimUnitStats {
    unit_id: string;
    name: string;
    pilot_name: string | null;
    /** 勝敗と撃墜数を判定する機体か */
    is_player: boolean;
    battles: number;
    kills: number;
    deaths: number;
}

/** 世代の集計値（`report.json`） */
export interface LocalSimReport {
    schema_version: number;
    generation_id: string;
    battles: number;
    wins: number;
    losses: number;
    /** 最大ステップ数で打ち切った戦闘の数 */
    timeouts: number;
    /** 戦闘の経過時間（秒） */
    elapsed_time: { avg: number; min: number; max: number };
    /** 判定する機体の撃墜数の合計 */
    player_kills: number;
    action_counts: Record<string, number>;
    /** `前 → 後` ごとの STRATEGY_CHANGED の回数 */
    strategy_transitions: Record<string, number>;
    weapon_usage: Record<string, number>;
    /** ロスターの順。判定する機体が先頭 */
    units: LocalSimUnitStats[];
    warnings: string[];
}

/** AI の判断を記録したログ（AI_DECISION・TARGET_SELECTION）から、デバッグ表示に使う項目 */
export interface LocalSimDecisionLog {
    timestamp: number;
    action_type: string;
    target_id: string | null;
    message: string;
    strategy_mode: string | null;
    fuzzy_scores: Record<string, unknown> | null;
}
