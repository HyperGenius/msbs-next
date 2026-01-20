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
}