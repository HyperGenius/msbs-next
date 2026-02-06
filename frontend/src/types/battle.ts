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
}

/**
 * 戦術設定
 */
export interface Tactics {
    priority: "CLOSEST" | "WEAKEST" | "RANDOM";
    range: "MELEE" | "RANGED" | "BALANCED" | "FLEE";
}

/**
 * Mobile Suit
 */
export interface MobileSuit {
    id: string;
    name: string;
    max_hp: number;
    current_hp: number;
    armor: number;
    mobility: number;
    position: Vector3;
    weapons: Weapon[];
    side: "PLAYER" | "ENEMY";
    tactics: Tactics;
}

/**
 * バトルログ
 */
export interface BattleLog {
    turn: number;
    actor_id: string;
    action_type: "MOVE" | "ATTACK" | "DAMAGE" | "DESTROYED" | "MISS";
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
    enemy_config: {
        enemies: Array<{
            name: string;
            max_hp: number;
            armor: number;
            mobility: number;
            position: Vector3;
            weapon: Weapon;
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
    created_at: string;
    updated_at: string;
}