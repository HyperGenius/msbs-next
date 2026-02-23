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
    optimal_range?: number;
    decay_rate?: number;
    max_ammo?: number | null;
    en_cost?: number;
    cool_down_turn?: number;
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
    tactics: Tactics;
    beam_resistance?: number;
    physical_resistance?: number;
    terrain_adaptability?: Record<string, string>;
    max_en?: number;
    en_recovery?: number;
    max_propellant?: number;
    /** NPC の場合のパイロットレベル（スナップショットから）*/
    npc_pilot_level?: number;
    /** NPC フラグ（スナップショットから）*/
    is_npc?: boolean;
}

/**
 * バトルログ
 */
export interface BattleLog {
    turn: number;
    actor_id: string;
    action_type: "MOVE" | "ATTACK" | "DAMAGE" | "DESTROYED" | "MISS" | "DETECTION" | "TARGET_SELECTION";
    target_id?: string;
    damage?: number;
    message: string;
    position_snapshot: Vector3;
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
 * バトル結果（履歴）
 */
export interface BattleResult {
    id: string;
    user_id: string | null;
    mission_id: number | null;
    win_loss: "WIN" | "LOSE" | "DRAW";
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
    level: number;
    exp: number;
    credits: number;
    skill_points: number;
    skills: Record<string, number>;
    inventory?: Record<string, number>;
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
    target_stat: "hp" | "armor" | "mobility" | "weapon_power";
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
    remaining_credits: number;
}

/**
 * 武器装備リクエスト
 */
export interface EquipWeaponRequest {
    weapon_id: string;
    slot_index?: number;
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
