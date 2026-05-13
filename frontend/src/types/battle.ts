/* frontend/src/types/battle.ts */

/**
 * 3次元ベクトル座標
 */
export interface Vector3 {
    x: number;
    y: number;
    z: number;
}

/**
 * 武器
 */
export interface Weapon {
    id: string;
    name: string;
    power: number;
    range: number;
    accuracy: number;
    type?: string;
    weapon_type?: "MELEE" | "CLOSE_RANGE" | "RANGED";
    optimal_range?: number;
    decay_rate?: number;
    max_ammo?: number | null;
    en_cost?: number;
    cool_down_turn?: number;
    is_melee?: boolean;
    /** 威力ランク (S〜E) - APIから付与される */
    power_rank?: string;
    /** 射程ランク (S〜E) - APIから付与される */
    range_rank?: string;
    /** 命中率ランク (S〜E) - APIから付与される */
    accuracy_rank?: string;
}

/**
 * 戦術設定
 */
export interface Tactics {
    priority: "CLOSEST" | "WEAKEST" | "RANDOM" | "STRONGEST" | "THREAT";
    range: "MELEE" | "RANGED" | "BALANCED" | "FLEE";
}

/**
 * Mobile Suit
 */
export interface MobileSuit {
    id: string;
    user_id?: string | null;
    name: string;
    max_hp: number;
    current_hp: number;
    armor: number;
    mobility: number;
    sensor_range?: number;
    position: Vector3;
    weapons: Weapon[];
    side: "PLAYER" | "ENEMY";
    team_id?: string | null;
    tactics: Tactics;
    beam_resistance?: number;
    physical_resistance?: number;
    melee_aptitude?: number;
    shooting_aptitude?: number;
    accuracy_bonus?: number;
    evasion_bonus?: number;
    acceleration_bonus?: number;
    turning_bonus?: number;
    terrain_adaptability?: Record<string, string>;
    max_en?: number;
    en_recovery?: number;
    max_propellant?: number;
    /** NPC の場合のパイロットレベル（スナップショットから）*/
    npc_pilot_level?: number;
    /** NPC フラグ（スナップショットから）*/
    is_npc?: boolean;
    /** HP ランク (S〜E) - APIから付与される */
    hp_rank?: string;
    /** 装甲ランク (S〜E) - APIから付与される */
    armor_rank?: string;
    /** 機動性ランク (S〜E) - APIから付与される */
    mobility_rank?: string;
}

/**
 * バトルログ
 */
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
    /** 格闘コンボ連続回数 (Phase C) */
    combo_count?: number;
    /** 格闘コンボ演出メッセージ e.g. "2Combo 300ダメージ!!" (Phase C) */
    combo_message?: string;
}

/**
 * バトル結果のAPIレスポンス
 */
export interface BattleResponse {
    winner_id: string | null;
    logs: BattleLog[];
    player_info: MobileSuit;
    enemies_info: MobileSuit[];
    rewards?: BattleRewards;
}

/**
 * バトル報酬
 */
export interface BattleRewards {
    exp_gained: number;
    credits_gained: number;
    level_before: number;
    level_after: number;
    total_exp: number;
    total_credits: number;
    kills?: number;
}

/**
 * 機体更新用の型定義（ガレージ機能で使用）
 */
export interface MobileSuitUpdate {
    name?: string;
    max_hp?: number;
    armor?: number;
    mobility?: number;
    tactics?: Tactics;
    melee_aptitude?: number;
    shooting_aptitude?: number;
    accuracy_bonus?: number;
    evasion_bonus?: number;
    acceleration_bonus?: number;
    turning_bonus?: number;
}

/**
 * ミッション定義
 */
export interface Mission {
    id: number;
    name: string;
    difficulty: number;
    description: string;
    environment?: string;
    special_effects?: string[];
    enemy_config: {
        enemies: Array<{
            name: string;
            max_hp: number;
            armor: number;
            mobility: number;
            position: Vector3;
            weapon: Weapon;
            terrain_adaptability?: Record<string, string>;
        }>;
    };
}

/**
 * バトル結果（履歴）- logsを含まない軽量版
 */
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

/**
 * バトルログレコード（battle_logsテーブル）
 */
export interface BattleLogRecord {
    id: string;
    room_id: string | null;
    mission_id: number | null;
    logs: BattleLog[];
    created_at: string;
}

/**
 * バトルルーム（定期更新バトルの開催回）
 */
export interface BattleRoom {
    id: string;
    status: "OPEN" | "DOING" | "CLOSED";
    scheduled_at: string;
    created_at: string;
}

/**
 * バトルエントリー
 */
export interface BattleEntry {
    id: string;
    room_id: string;
    mobile_suit_id: string;
    scheduled_at: string;
    created_at: string;
}

/**
 * エントリー状況レスポンス
 */
export interface EntryStatusResponse {
    is_entered: boolean;
    entry: BattleEntry | null;
    next_room: {
        id: string;
        status: string;
        scheduled_at: string;
    } | null;
}

/**
 * パイロット情報
 */
export interface Pilot {
    id: string;
    user_id: string;
    name: string;
    faction: string;
    background: string;
    level: number;
    exp: number;
    credits: number;
    skill_points: number;
    skills: Record<string, number>;
    inventory?: Record<string, number>;
    // ステータスポイントシステム
    status_points: number;
    dex: number;
    intel: number;
    ref: number;
    tou: number;
    luk: number;
    awq: number;
    created_at: string;
    updated_at: string;
}

/**
 * スキル定義
 */
export interface SkillDefinition {
    id: string;
    name: string;
    description: string;
    effect_per_level: number;
    max_level: number;
}

/**
 * スキル習得リクエスト
 */
export interface SkillUnlockRequest {
    skill_id: string;
}

/**
 * スキル習得レスポンス
 */
export interface SkillUnlockResponse {
    pilot: Pilot;
    message: string;
}

/**
 * ショップ商品のスペック
 */
export interface ShopItemSpecs {
    max_hp: number;
    armor: number;
    mobility: number;
    sensor_range: number;
    weapons: Weapon[];
    beam_resistance?: number;
    physical_resistance?: number;
    melee_aptitude?: number;
    shooting_aptitude?: number;
    accuracy_bonus?: number;
    evasion_bonus?: number;
    acceleration_bonus?: number;
    turning_bonus?: number;
}

/**
 * ショップ商品
 */
export interface ShopListing {
    id: string;
    name: string;
    price: number;
    description: string;
    specs: ShopItemSpecs;
}

/**
 * 購入レスポンス
 */
export interface PurchaseResponse {
    message: string;
    mobile_suit_id: string;
    remaining_credits: number;
}

/**
 * 強化リクエスト
 */
export interface UpgradeRequest {
    mobile_suit_id: string;
    target_stat: "hp" | "armor" | "mobility" | "weapon_power" | "melee_aptitude" | "shooting_aptitude" | "accuracy_bonus" | "evasion_bonus" | "acceleration_bonus" | "turning_bonus";
    steps?: number;
}

/**
 * 強化レスポンス
 */
export interface UpgradeResponse {
    message: string;
    mobile_suit: MobileSuit;
    remaining_credits: number;
    cost_paid: number;
}

/**
 * 強化プレビュー
 */
export interface UpgradePreview {
    mobile_suit_id: string;
    stat_type: string;
    current_value: number;
    new_value: number;
    cost: number;
    at_max_cap: boolean;
}

/**
 * 一括強化リクエスト
 */
export interface BulkUpgradeRequest {
    mobile_suit_id: string;
    upgrades: Record<string, number>;  // e.g. { "hp": 2, "armor": 1 }
}

/**
 * 一括強化レスポンス
 */
export interface BulkUpgradeResponse {
    message: string;
    mobile_suit: MobileSuit;
    remaining_credits: number;
    total_cost_paid: number;
}

/**
 * 武器ショップ商品
 */
export interface WeaponListing {
    id: string;
    name: string;
    price: number;
    description: string;
    weapon: Weapon;
}

/**
 * 武器購入レスポンス
 */
export interface WeaponPurchaseResponse {
    message: string;
    weapon_id: string;
    player_weapon_id: string;
    remaining_credits: number;
}

/**
 * 武器装備リクエスト
 */
export interface EquipWeaponRequest {
    player_weapon_id: string;
    slot_index?: number;
}

/**
 * プレイヤー武器インスタンス
 */
export interface PlayerWeapon {
    id: string;
    master_weapon_id: string;
    base_snapshot: Record<string, unknown>;
    custom_stats: Record<string, unknown>;
    equipped_ms_id: string | null;
    equipped_slot: number | null;
    acquired_at: string;
}

/**
 * ランキングエントリー
 */
export interface LeaderboardEntry {
    rank: number;
    user_id: string;
    pilot_name: string;
    wins: number;
    losses: number;
    kills: number;
    credits_earned: number;
}

/**
 * プレイヤープロフィール（公開情報）
 */
export interface PlayerProfile {
    pilot_name: string;
    level: number;
    wins: number;
    losses: number;
    kills: number;
    mobile_suit: MobileSuit | null;
    skills: Record<string, number>;
}

/**
 * フレンド関係
 */
export interface Friend {
    id: string;
    user_id: string;
    friend_user_id: string;
    status: "PENDING" | "ACCEPTED" | "BLOCKED";
    pilot_name: string | null;
    created_at: string;
}

/**
 * チームメンバー
 */
export interface TeamMember {
    user_id: string;
    is_ready: boolean;
    joined_at: string;
}

/**
 * チーム
 */
export interface Team {
    id: string;
    owner_user_id: string;
    name: string;
    status: "FORMING" | "READY" | "DISBANDED";
    members: TeamMember[];
    created_at: string;
}

/**
 * チームエントリーリクエスト
 */
export interface TeamEntryRequest {
    team_id: string;
    mobile_suit_id: string;
}

/**
 * チームエントリーレスポンス
 */
export interface TeamEntryResponse {
    message: string;
    entry_ids: string[];
    room_id: string;
}

// =============================================================
// マスター機体データ管理（管理者専用）
// =============================================================

/**
 * マスター機体スペック（管理者用）
 */
export interface MasterMobileSuitSpec {
    max_hp: number;
    armor: number;
    mobility: number;
    sensor_range: number;
    beam_resistance: number;
    physical_resistance: number;
    melee_aptitude: number;
    shooting_aptitude: number;
    accuracy_bonus: number;
    evasion_bonus: number;
    acceleration_bonus: number;
    turning_bonus: number;
    weapons: Weapon[];
}

/**
 * マスター機体エントリー（管理者用）
 */
export interface MasterMobileSuit {
    id: string;
    name: string;
    price: number;
    faction: string;
    description: string;
    specs: MasterMobileSuitSpec;
}

/**
 * マスター機体新規追加リクエスト
 */
export type MasterMobileSuitCreate = MasterMobileSuit;

/**
 * マスター機体更新リクエスト
 */
export interface MasterMobileSuitUpdate {
    name?: string;
    price?: number;
    faction?: string;
    description?: string;
    specs?: MasterMobileSuitSpec;
}

// =============================================================
// マスター武器データ管理（管理者専用）
// =============================================================

/**
 * マスター武器エントリー（管理者用）
 */
export interface MasterWeapon {
    id: string;
    name: string;
    price: number;
    description: string;
    weapon: Weapon;
}

/**
 * マスター武器新規追加リクエスト
 */
export type MasterWeaponCreate = MasterWeapon;

/**
 * マスター武器更新リクエスト
 */
export interface MasterWeaponUpdate {
    name?: string;
    price?: number;
    description?: string;
    weapon?: Weapon;
}
