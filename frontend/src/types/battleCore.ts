import { Vector3, Obstacle } from "./geometry";
import { MobileSuit } from "./mobileSuit";
import { ObjectiveDetail } from "./mission";

/** バトルシミュレーター1ターンぶんの行動ログ */
export interface BattleLog {
    timestamp: number;
    actor_id: string;
    action_type: "MOVE" | "ATTACK" | "DAMAGE" | "DESTROYED" | "MISS" | "DETECTION" | "TARGET_SELECTION" | "WAIT" | "MELEE_COMBO" | "BOOST_START" | "BOOST_END" | "DISENGAGE" | "MELEE_CLASH" | "RETREAT_COMPLETE";
    target_id?: string;
    damage?: number;
    /** 配信用ログの MOVE・WAIT・TARGET_SELECTION の行には無い。表示するときは `describeBattleLog()` で作る */
    message?: string;
    position_snapshot: Vector3;
    chatter?: string;
    weapon_name?: string;
    /** 使用した武器のID（フロントエンドでの武器特定用） */
    weapon_id?: string;
    /** クリティカルヒット判定 */
    is_crit?: boolean;
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
    /** 攻撃方向 "FRONT" | "FRONT_SIDE" | "REAR_SIDE" | "REAR" */
    attack_sector?: string;
    /** 命中部位 "HEAD" | "TORSO" | "RIGHT_ARM" | "LEFT_ARM" | "RIGHT_LEG" | "LEFT_LEG"（Issue #503） */
    hit_part?: string;
    /** 使用武器のスロット部位ロール "RIGHT_ARM" | "LEFT_ARM" | "RACK"（Issue #504） */
    weapon_slot_role?: string;
    /** ログ種別ごとの追加情報。EN 消費ログの `en`（消費後の EN 残量）や `reason_code` など（Issue #533） */
    details?: Record<string, unknown> | null;
}

/** 配信用ログ（replay）のバージョン。backend/app/engine/replay_log.py の REPLAY_LOG_VERSION と同じ値 */
export const REPLAY_LOG_VERSION = 1;

/** 配信用ログの先頭行。旧形式のログには無い */
export interface ReplayLogHeader {
    replay_version: number;
}

/**
 * 配信用ログの1行（先頭行の後に続く）。
 * 値の無い項目はキーごと省かれる。MOVE・WAIT・TARGET_SELECTION の行は message を持たない。
 * AI_DECISION の行は無く、TARGET_SELECTION は機体ごとに相手が変わった行だけがある。
 */
export type ReplayBattleLog = Omit<
    BattleLog,
    "fuzzy_scores" | "strategy_mode" | "attack_sector" | "hit_part" | "weapon_slot_role"
>;

/** 部位別の被弾/命中1件分の集計（回数・合計ダメージ） */
export interface PartHitStat {
    hits: number;
    damage: number;
}

/** バトル結果に紐づく部位別命中サマリー（Issue #504） */
export interface PartHitSummary {
    /** 被弾部位別の集計（キー: hit_part） */
    taken: Record<string, PartHitStat>;
    /** 命中させた武器スロット別の集計（キー: weapon_slot_role） */
    dealt: Record<string, PartHitStat>;
}

/** 自機の武器1つ分の命中数と試行数。バックエンドが保存した形 */
export interface WeaponAccuracyRecord {
    weapon_name: string;
    hits: number;
    attempts: number;
}

/** 索敵の集計 */
export interface DetectionSummary {
    /** 自機が索敵に成功した敵機数（重複なし） */
    captured: number;
    /** `enemies_info` の件数 */
    total: number;
}

/** バトルで得た戦利品。kind が BLUEPRINT なら設計図 */
export interface BlueprintLootItem {
    kind: "BLUEPRINT";
    blueprint_id: string;
    target_type: "MOBILE_SUIT" | "WEAPON";
    target_id: string;
    /** 未所持の設計図を入手したか。false なら換金された */
    is_new: boolean;
    /** 所持済みの設計図を換金したクレジット。バトル報酬の credits_gained には含まない */
    credits_awarded: number;
    /** 機体・武器マスターの表示名。マスターが無ければ target_id */
    target_name: string;
}

/** バトルで得た技術断片。数値は入手した時点のもの */
export interface TechFragmentLootItem {
    kind: "TECH_FRAGMENT";
    tech_id: string;
    /** 入手後の累計断片数 */
    fragment_count: number;
    /** 入手後の技術Lv */
    level: number;
    max_level: number;
    /** この断片で技術Lvが上がったか */
    is_level_up: boolean;
    /** 次のLvまでに必要な断片数。最大Lvなら null */
    fragments_to_next_level: number | null;
    /** 最大Lv後の断片を換金したクレジット。バトル報酬の credits_gained には含まない */
    credits_awarded: number;
    /** 技術マスターの表示名。マスターが無ければ tech_id */
    target_name: string;
}

/** バトルで得た戦利品（設計図または技術断片） */
export type LootItem = BlueprintLootItem | TechFragmentLootItem;

/** バトルで得た報酬（経験値・クレジット・レベル変化） */
export interface BattleRewards {
    exp_gained: number;
    credits_gained: number;
    level_before: number;
    level_after: number;
    total_exp: number;
    total_credits: number;
    kills?: number;
    loot?: LootItem[];
}

/** バトルAPIのレスポンス全体（ログ・機体情報・報酬を含む） */
export interface BattleResponse {
    winner_id: string | null;
    logs: BattleLog[];
    player_info: MobileSuit;
    enemies_info: MobileSuit[];
    rewards?: BattleRewards;
    /** フィールド範囲 [min, max] (m)。BattleViewerの背景グリッド整列用 (Issue #436) */
    map_bounds?: [number, number] | null;
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
    /** フィールド範囲 [min, max] (m)。マイグレーション前の既存レコードは null (Issue #436) */
    map_bounds?: [number, number] | null;
    /** 定期バトルの戦域。ソロミッションと戦域導入前のバトルは null */
    theater_id?: string | null;
    /** 戦闘時のミノフスキー濃度 (0〜1) */
    minovsky_density?: number | null;
    /** 戦域・環境タイプの表示名。マスターに無ければ null */
    theater_name?: string | null;
    environment_name?: string | null;
    /** BattleViewer の描画プリセット。マスターに無ければ null */
    viewer_preset?: string | null;
    kills?: number;
    exp_gained?: number;
    credits_gained?: number;
    level_before?: number;
    level_after?: number;
    level_up?: boolean;
    is_read?: boolean;
    created_at: string;
    /** 戦闘ダイジェスト（Issue #415）。マイグレーション前の既存レコードは null */
    player_survived?: boolean | null;
    min_hp_percent?: number | null;
    damage_severity?: "無傷" | "軽微" | "中破" | "大破" | "撃墜" | null;
    damage_taken_count?: number | null;
    max_hit_damage?: number | null;
    dodge_count?: number | null;
    attacks_received_count?: number | null;
    pilot_ms_name?: string | null;
    digest_tag?: string | null;
    /** ルールベースで生成された一言ログ */
    digest_text?: string | null;
    /** 部位別の被弾/命中集計（Issue #504）。マイグレーション前の既存レコードは null */
    part_hit_summary?: PartHitSummary | null;
    /** 武器ごとの命中数と試行数（試行数の多い順）。保存を始める前の結果は null */
    weapon_accuracy_summary?: WeaponAccuracyRecord[] | null;
    /** 索敵の集計。保存を始める前の結果は null */
    detection_summary?: DetectionSummary | null;
    /** 戦利品の一覧。ドロップなしは空配列、導入前のバトルは null */
    loot?: LootItem[] | null;
    /** 作戦の結果。定期バトルの結果に入る。ソロミッションと導入前のバトルは null */
    objective_status?: "SUCCESS" | "FAILURE" | "DRAW" | null;
    /** 達成した数（例: 離脱させた友軍の数） */
    objective_progress?: number | null;
    /** 成功に必要な数。0 は達成度を数えない目標 */
    objective_required?: number | null;
    /** 作戦の達成度の内訳と、ビューア用の撤退ポイント・ロール。友軍を数えない目標は null */
    objective_detail?: ObjectiveDetail | null;
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
    /** 作戦ID。null はデイリーバトルロイヤル */
    mission_id?: number | null;
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
