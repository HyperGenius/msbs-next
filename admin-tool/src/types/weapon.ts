/** 武器のスペック定義のうち id/name を除いた部分（マスター武器の weapon(JSON)列と同形式） */
export interface WeaponSpec {
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
    /** 装備に必要なビームジェネレータLv (BEAM属性武器のみ有効) */
    required_beam_generator_lv?: number;
    /** 威力ランク (S〜E) - APIから付与される */
    power_rank?: string;
    /** 射程ランク (S〜E) - APIから付与される */
    range_rank?: string;
    /** 命中率ランク (S〜E) - APIから付与される */
    accuracy_rank?: string;
}

/** 武器のスペック定義（機体に装備するマスターデータと同形式）。id/name は機体武器スロット内での識別に使う */
export interface Weapon extends WeaponSpec {
    id: string;
    name: string;
}

/** 機体の戦術設定（ターゲット優先度と交戦距離の方針） */
export interface Tactics {
    priority: "CLOSEST" | "WEAKEST" | "RANDOM" | "STRONGEST" | "THREAT";
    range: "MELEE" | "RANGED" | "BALANCED" | "FLEE";
}
