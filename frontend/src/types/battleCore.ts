import { Vector3, Obstacle } from "./geometry";
import { MobileSuit } from "./mobileSuit";

/** バトルシミュレーター1ターンぶんの行動ログ */
export interface BattleLog {
    timestamp: number;
    actor_id: string;
    action_type: "MOVE" | "ATTACK" | "DAMAGE" | "DESTROYED" | "MISS" | "DETECTION" | "TARGET_SELECTION" | "WAIT" | "MELEE_COMBO";
    target_id?: string;
    damage?: number;
    message: string;
    position_snapshot: Vector3;
    chatter?: string;
    weapon_name?: string;
    target_max_hp?: number;
    /** スキルが命中/回避の判定を変えた場合 true */
    skill_activated?: boolean;
    /** 行動時点の速度ベクトル */
    velocity_snapshot?: Vector3;
    /** ファジィ推論の中間スコア（デバッグ用） */
    fuzzy_scores?: Record<string, unknown>;
    /** 行動決定時の戦略モード */
    strategy_mode?: string;
    /** 格闘コンボ連続回数 */
    combo_count?: number;
    /** 格闘コンボ演出メッセージ e.g. "2Combo 300ダメージ!!" */
    combo_message?: string;
    /** 行動時点の胴体向き（度数法、XZ平面）— BattleViewer向き可視化用 */
    heading?: number;
}

/** バトルで得た報酬（経験値・クレジット・レベル変化） */
export interface BattleRewards {
    exp_gained: number;
    credits_gained: number;
    level_before: number;
    level_after: number;
    total_exp: number;
    total_credits: number;
    kills?: number;
}

/** バトルAPIのレスポンス全体（ログ・機体情報・報酬を含む） */
export interface BattleResponse {
    winner_id: string | null;
    logs: BattleLog[];
    player_info: MobileSuit;
    enemies_info: MobileSuit[];
    rewards?: BattleRewards;
}

/** バトル結果の履歴レコード（ログを含まない軽量版） */
export interface BattleResult {
    id: string;
    user_id: string | null;
    mission_id: number | null;
    room_id?: string | null;
    battle_log_id?: string | null;
    win_loss: "WIN" | "LOSE" | "DRAW";
    environment?: string;
    player_info?: MobileSuit;
    enemies_info?: MobileSuit[];
    obstacles_info?: Obstacle[];
    ms_snapshot?: MobileSuit;
    kills?: number;
    exp_gained?: number;
    credits_gained?: number;
    level_before?: number;
    level_after?: number;
    level_up?: boolean;
    is_read?: boolean;
    created_at: string;
}

/** battle_logsテーブルのレコード（リプレイ用の全ログを保持） */
export interface BattleLogRecord {
    id: string;
    room_id: string | null;
    mission_id: number | null;
    logs: BattleLog[];
    created_at: string;
}

/** 定期開催バトルの1開催回（ルーム） */
export interface BattleRoom {
    id: string;
    status: "OPEN" | "DOING" | "CLOSED";
    scheduled_at: string;
    created_at: string;
}

/** 個人バトルエントリーレコード */
export interface BattleEntry {
    id: string;
    room_id: string;
    mobile_suit_id: string;
    scheduled_at: string;
    created_at: string;
}

/** エントリー状況確認のレスポンス（エントリー済みか・次回ルーム情報を含む） */
export interface EntryStatusResponse {
    is_entered: boolean;
    entry: BattleEntry | null;
    next_room: {
        id: string;
        status: string;
        scheduled_at: string;
    } | null;
}
