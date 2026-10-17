/* frontend/tests/unit/resultSummaryParity.test.ts */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, it, expect } from "vitest";
import { computePartHitSummary } from "@/hooks/usePartHitSummary";
import { computeWeaponAccuracySummary, fromWeaponAccuracyRecords } from "@/hooks/useWeaponAccuracySummary";
import { computeDetectionSummary } from "@/hooks/useDetectionSummary";
import {
  BattleLog,
  DetectionSummary,
  MobileSuit,
  PartHitSummary,
  WeaponAccuracyRecord,
} from "@/types/battle";

// バックエンドの tests/unit/test_result_summary.py も同じデータを読む。
const FIXTURE_PATH = fileURLToPath(
  new URL("../../../backend/tests/fixtures/result_summary_parity.json", import.meta.url)
);

interface ParityFixture {
  player_info: { id: string; weapons: { name: string }[] };
  enemies_info: MobileSuit[];
  logs: BattleLog[];
  expected: {
    part_hit_summary: PartHitSummary;
    weapon_accuracy_summary: WeaponAccuracyRecord[];
    detection_summary: DetectionSummary;
  };
}

const fixture: ParityFixture = JSON.parse(readFileSync(FIXTURE_PATH, "utf-8"));
const playerId = fixture.player_info.id;
const equippedWeaponNames = fixture.player_info.weapons.map((w) => w.name);

describe("戦果サマリーのバックエンドとの一致", () => {
  it("被弾部位の集計がバックエンドの保存値と一致する", () => {
    expect(computePartHitSummary(playerId, fixture.logs)).toEqual(fixture.expected.part_hit_summary);
  });

  it("武器ごとの命中率がバックエンドの保存値と一致する", () => {
    const fromLogs = computeWeaponAccuracySummary(playerId, fixture.logs, equippedWeaponNames);
    expect(fromLogs).toEqual(fromWeaponAccuracyRecords(fixture.expected.weapon_accuracy_summary));
  });

  it("索敵の集計がバックエンドの保存値と一致する", () => {
    expect(computeDetectionSummary(playerId, fixture.logs, fixture.enemies_info)).toEqual(
      fixture.expected.detection_summary
    );
  });
});

describe("fromWeaponAccuracyRecords", () => {
  it("保存値の順を保ち、試行0件の命中率を null にする", () => {
    const stats = fromWeaponAccuracyRecords([
      { weapon_name: "ビームライフル", hits: 1, attempts: 4 },
      { weapon_name: "シールドミサイル", hits: 0, attempts: 0 },
    ]);
    expect(stats).toEqual([
      { weaponName: "ビームライフル", hits: 1, attempts: 4, accuracy: 0.25 },
      { weaponName: "シールドミサイル", hits: 0, attempts: 0, accuracy: null },
    ]);
  });
});
