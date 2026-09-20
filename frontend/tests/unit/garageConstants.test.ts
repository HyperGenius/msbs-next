import { describe, it, expect } from "vitest";
import { getWeaponSlots, getWeaponSlotLabel } from "@/app/garage/constants";

describe("getWeaponSlots", () => {
  it("スロット0/1を右腕・左腕、2以降をラックNとしてラベリングする", () => {
    const slots = getWeaponSlots(4);
    expect(slots.map((s) => s.labelJa)).toEqual([
      "右腕",
      "左腕",
      "ラック1",
      "ラック2",
    ]);
    expect(slots.map((s) => s.label)).toEqual([
      "Right Arm",
      "Left Arm",
      "Rack 1",
      "Rack 2",
    ]);
  });

  it("weaponSlotCountが2以下のMSにも右腕・左腕のみでそのまま適用できる", () => {
    const slots = getWeaponSlots(2);
    expect(slots.map((s) => s.labelJa)).toEqual(["右腕", "左腕"]);
  });

  it("未設定・不正な値はデフォルトのスロット数にフォールバックする", () => {
    expect(getWeaponSlots(undefined).map((s) => s.labelJa)).toEqual([
      "右腕",
      "左腕",
    ]);
    expect(getWeaponSlots(0).map((s) => s.labelJa)).toEqual(["右腕", "左腕"]);
  });
});

describe("getWeaponSlotLabel", () => {
  it("indexのみから部位ラベルを解決する", () => {
    expect(getWeaponSlotLabel(0)).toBe("右腕");
    expect(getWeaponSlotLabel(1)).toBe("左腕");
    expect(getWeaponSlotLabel(2)).toBe("ラック1");
    expect(getWeaponSlotLabel(5)).toBe("ラック4");
  });
});
