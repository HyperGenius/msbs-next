import { TechRequirementStatus } from "./shop";

/** 設計図・技術断片を入手できる戦域 */
export interface ObtainableTheater {
    /** 戦域の表示名 */
    label: string;
    /** true なら勝利時だけドロップする */
    requires_win: boolean;
}

/** 設計図の入手経路。MIGRATION は設計図システム導入時の付与 */
export type BlueprintSource = "MIGRATION" | "DROP";

/** 設計図コレクション（図鑑）の1件 */
export interface BlueprintCollectionItem {
    blueprint_id: string;
    target_type: "MOBILE_SUIT" | "WEAPON";
    target_id: string;
    target_name: string;
    /** 機体の勢力。武器と共通機体は空文字 */
    faction: string;
    is_standard_issue: boolean;
    is_owned: boolean;
    /** 入手日時。未所持なら null */
    acquired_at: string | null;
    /** 入手経路。未所持なら null */
    source: BlueprintSource | null;
    /** パイロットの勢力で入手できるか */
    is_available_to_faction: boolean;
    /** 入手できる戦域。所持済み・標準配備・勢力外は空 */
    obtainable_theaters: ObtainableTheater[];
    /** 購入に必要な技術Lvと現在Lv。標準配備品は空 */
    tech_requirements: TechRequirementStatus[];
}

/** プレイヤーの技術ごとの進捗 */
export interface PlayerTechnologyProgress {
    tech_id: string;
    name: string;
    description: string;
    level: number;
    max_level: number;
    /** 累計の断片入手数 */
    fragment_count: number;
    /** 次のLvに必要な累計断片数。最大Lvなら null */
    next_level_threshold: number | null;
    /** 次のLvまでに必要な断片数。最大Lvなら null */
    fragments_to_next_level: number | null;
    /** 最大Lv後に断片を入手したときに付与するクレジット */
    overflow_credit_value: number;
    /** 技術断片を入手できる戦域 */
    obtainable_theaters: ObtainableTheater[];
}
