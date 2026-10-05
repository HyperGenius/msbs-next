/* frontend/src/types/localSim.ts */
import { Obstacle } from "./geometry";
import { MobileSuit } from "./mobileSuit";

// ローカルシミュレーションの保存形式。
// backend/scripts/simulation/local_sim/generations.py の Pydantic モデルと項目を揃える。

/** 1戦の勝敗。`manifest.json` の `battles` の1件 */
export interface LocalSimBattleSummary {
    /** 1 始まりの戦闘番号 */
    index: number;
    file: string;
    seed: number;
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

/** 1回の `run` の実行条件と勝敗（`manifest.json`） */
export interface LocalSimManifest {
    schema_version: number;
    /** 世代ディレクトリの名前 */
    generation_id: string;
    label: string;
    created_at: string;
    pinned: boolean;
    roster_name: string;
    player_name: string | null;
    /** 1戦目のシード */
    seed: number;
    rounds: number;
    max_steps: number;
    git: { commit: string | null; dirty: boolean | null };
    theater_id: string | null;
    environment: string;
    minovsky_density: number;
    summary: LocalSimGenerationSummary;
    battles: LocalSimBattleSummary[];
}

/** `battle_NNN.json` からログを除いたもの。ログは NDJSON で別に取得する */
export interface LocalSimBattle {
    index: number;
    seed: number;
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
    log_count: number;
}

/** 世代一覧の API の応答 */
export interface LocalSimGenerationList {
    /** 読み込み元のディレクトリ（絶対パス） */
    root: string;
    /** 新しい順 */
    generations: LocalSimManifest[];
}
