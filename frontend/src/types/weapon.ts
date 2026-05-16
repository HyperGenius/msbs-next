/** 武器のスペック定義（機体に装備するマスターデータと同形式） */
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

/** 機体の戦術設定（ターゲット優先度と交戦距離の方針） */
export interface Tactics {
    priority: "CLOSEST" | "WEAKEST" | "RANDOM" | "STRONGEST" | "THREAT";
    range: "MELEE" | "RANGED" | "BALANCED" | "FLEE";
}
