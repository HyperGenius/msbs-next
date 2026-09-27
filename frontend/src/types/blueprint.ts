/** 設計図を入手できる戦域 */
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
}
