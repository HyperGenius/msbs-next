export type Faction = "FEDERATION" | "ZEON";

export type StatKey = "SHT" | "MEL" | "INT" | "REF" | "TOU" | "LUK";

export interface Background {
  id: string;
  name: string;
  description: string;
  baseStats: Record<StatKey, number>;
}

export type BonusAllocation = Record<StatKey, number>;
