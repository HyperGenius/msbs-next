import { describe, it, expect } from "vitest";
import { PlayerWeapon } from "@/types/battle";
import { countUpgradeSteps, resolveWeaponSpec } from "@/app/garage/weaponUpgrade";

function makePlayerWeapon(
  customStats: PlayerWeapon["custom_stats"],
  snapshot: Record<string, unknown> = { id: "w", name: "Beam Rifle", power: 100, range: 400, accuracy: 85 }
): PlayerWeapon {
  return {
    id: "pw",
    master_weapon_id: "beam_rifle",
    base_snapshot: snapshot,
    custom_stats: customStats,
    equipped_ms_id: null,
    equipped_slot: null,
    acquired_at: "2026-10-01T00:00:00Z",
  };
}

describe("countUpgradeSteps", () => {
  it("未改造なら 0 を返す", () => {
    expect(countUpgradeSteps(makePlayerWeapon({}))).toBe(0);
  });

  it("威力と命中率の段階数を合計する", () => {
    // 威力は 5、命中率は 1.0 刻み
    const pw = makePlayerWeapon({ power_bonus: 10, accuracy_bonus: 3 });
    expect(countUpgradeSteps(pw)).toBe(5);
  });

  it("上限で切り詰められた最後の段階も 1 段として数える", () => {
    // 命中率 85 の上限ボーナスは 85 × 0.3 = 25.5（26 段目が 0.5 で打ち切られる）
    const pw = makePlayerWeapon({ accuracy_bonus: 25.5 });
    expect(countUpgradeSteps(pw)).toBe(26);
  });

  it("浮動小数の誤差で段階数を多く数えない", () => {
    const pw = makePlayerWeapon({ accuracy_bonus: 0.1 + 0.2 + 0.7 });
    expect(countUpgradeSteps(pw)).toBe(1);
  });
});

describe("resolveWeaponSpec", () => {
  it("改造差分を威力と命中率に加算し、弾数・EN 消費はそのまま返す", () => {
    const pw = makePlayerWeapon(
      { power_bonus: 15, accuracy_bonus: 2 },
      { id: "w", name: "Beam Rifle", power: 100, range: 400, accuracy: 85, max_ammo: null, en_cost: 20 }
    );
    const spec = resolveWeaponSpec(pw);
    expect(spec.power).toBe(115);
    expect(spec.accuracy).toBe(87);
    expect(spec.max_ammo).toBeNull();
    expect(spec.en_cost).toBe(20);
  });
});
