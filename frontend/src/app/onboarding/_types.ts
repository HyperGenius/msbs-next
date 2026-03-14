export type Faction = "FEDERATION" | "ZEON";

export type StatKey = "DEX" | "INT" | "REF" | "TOU" | "LUK";

export interface Background {
  id: string;
  name: string;
  description: string;
  baseStats: Record<StatKey, number>;
}

export type BonusAllocation = Record<StatKey, number>;
