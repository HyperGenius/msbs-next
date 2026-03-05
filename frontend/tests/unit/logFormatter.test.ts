/* frontend/tests/unit/logFormatter.test.ts */
import { describe, it, expect } from "vitest";
import { formatBattleLog, formatBattleLogs } from "@/utils/logFormatter";
import { BattleLog } from "@/types/battle";

const PLAYER_ID = "player-001";

/** テスト用ログを生成するヘルパー */
function makeLog(overrides: Partial<BattleLog> = {}): BattleLog {
  return {
    turn: 1,
    actor_id: PLAYER_ID,
    action_type: "ATTACK",
    message: "攻撃した",
    position_snapshot: { x: 0, y: 0, z: 0 },
    ...overrides,
  };
}

// ─────────────────────────────────────────────
// formatBattleLog — 開発環境（isProduction: false）
// ─────────────────────────────────────────────
describe("formatBattleLog – 開発環境", () => {
  it("メッセージをそのまま返す（距離変換なし）", () => {
    const log = makeLog({ message: "450m の距離から射撃した" });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.message).toBe("450m の距離から射撃した");
  });

  it("命中率をそのまま残す", () => {
    const log = makeLog({ message: "射撃 (命中: 75%)" });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.message).toBe("射撃 (命中: 75%)");
  });

  it("ダメージ数値をそのまま返す", () => {
    const log = makeLog({ message: "150ダメージを与えた", damage: 150 });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.message).toBe("150ダメージを与えた");
  });

  it("actor_id / turn / action_type をそのまま引き継ぐ", () => {
    const log = makeLog({ turn: 5, action_type: "MISS" });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.turn).toBe(5);
    expect(result.action_type).toBe("MISS");
    expect(result.actor_id).toBe(PLAYER_ID);
  });
});

// ─────────────────────────────────────────────
// formatBattleLog — 本番環境（isProduction: true）
// ─────────────────────────────────────────────
describe("formatBattleLog – 本番環境", () => {
  describe("距離の抽象化", () => {
    it("≤200m を「近距離」に変換する", () => {
      const log = makeLog({ message: "150m から接近した" });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("近距離 から接近した");
    });

    it("≤400m を「中距離」に変換する", () => {
      const log = makeLog({ message: "350m から狙撃した" });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("中距離 から狙撃した");
    });

    it(">400m を「遠距離」に変換する", () => {
      const log = makeLog({ message: "600m の距離から射撃した" });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("遠距離 の距離から射撃した");
    });

    it("400m ちょうどは「中距離」に変換する", () => {
      const log = makeLog({ message: "400m の位置" });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("中距離 の位置");
    });

    it("200m ちょうどは「近距離」に変換する", () => {
      const log = makeLog({ message: "200m の位置" });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("近距離 の位置");
    });

    it("複数の距離表記をすべて変換する", () => {
      const log = makeLog({ message: "100m から移動して 500m の敵を狙った" });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("近距離 から移動して 遠距離 の敵を狙った");
    });
  });

  describe("命中率の非表示", () => {
    it("(命中: XX%) を削除する", () => {
      const log = makeLog({ message: "射撃 (命中: 75%)" });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("射撃");
    });

    it("命中率を含まないメッセージはそのまま", () => {
      const log = makeLog({ message: "移動した" });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("移動した");
    });

    it("命中率 0% も削除される", () => {
      const log = makeLog({ message: "射撃ミス (命中: 0%)" });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("射撃ミス");
    });
  });

  describe("ダメージの抽象化", () => {
    it("damage ≥ 100 → 大ダメージ", () => {
      const log = makeLog({ message: "150ダメージを与えた", damage: 150 });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("大ダメージを与えた");
    });

    it("damage ≥ 30 → ダメージ", () => {
      const log = makeLog({ message: "50ダメージを与えた", damage: 50 });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("ダメージを与えた");
    });

    it("damage < 30 → 軽微なダメージ", () => {
      const log = makeLog({ message: "10ダメージを与えた", damage: 10 });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("軽微なダメージを与えた");
    });

    it("damage が undefined のときはメッセージを変更しない", () => {
      const log = makeLog({ message: "50ダメージを与えた", damage: undefined });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("50ダメージを与えた");
    });

    it("damage 100 ちょうどは「大ダメージ」", () => {
      const log = makeLog({ message: "100ダメージを与えた", damage: 100 });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("大ダメージを与えた");
    });

    it("damage 30 ちょうどは「ダメージ」", () => {
      const log = makeLog({ message: "30ダメージを与えた", damage: 30 });
      const result = formatBattleLog(log, true, PLAYER_ID);
      expect(result.message).toBe("ダメージを与えた");
    });
  });

  it("距離・命中率・ダメージを組み合わせて変換する", () => {
    const log = makeLog({
      message: "450m から射撃 (命中: 80%) 75ダメージを与えた",
      damage: 75,
    });
    const result = formatBattleLog(log, true, PLAYER_ID);
    expect(result.message).toBe("遠距離 から射撃 ダメージを与えた");
  });
});

// ─────────────────────────────────────────────
// getLogStyle — スタイル判定
// ─────────────────────────────────────────────
describe("formatBattleLog – スタイル判定", () => {
  it("弾切れメッセージはオレンジスタイル", () => {
    const log = makeLog({ message: "弾切れのため待機" });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-orange-500");
    expect(result.style.textStyle).toContain("text-orange-400");
  });

  it("EN不足メッセージはオレンジスタイル", () => {
    const log = makeLog({ message: "EN不足で射撃キャンセル" });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-orange-500");
  });

  it("索敵メッセージはシアンスタイル", () => {
    const log = makeLog({ message: "索敵中", action_type: "DETECTION" });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-cyan-500");
    expect(result.style.textStyle).toContain("text-cyan-400");
  });

  it("ビームメッセージはパープルスタイル", () => {
    const log = makeLog({ message: "ビーム兵器で攻撃" });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-purple-500");
  });

  it("通常メッセージはデフォルトグリーンスタイル", () => {
    const log = makeLog({ message: "移動した" });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-green-900");
    expect(result.style.textStyle).toContain("text-green-600");
  });
});

// ─────────────────────────────────────────────
// formatBattleLogs — フィルタリング
// ─────────────────────────────────────────────
describe("formatBattleLogs – フィルタリング", () => {
  const logs: BattleLog[] = [
    makeLog({ actor_id: PLAYER_ID, target_id: undefined }),
    makeLog({ actor_id: "enemy-001", target_id: PLAYER_ID }),
    makeLog({ actor_id: "enemy-001", target_id: "enemy-002" }),
    makeLog({ actor_id: "ally-001", target_id: "enemy-001" }),
  ];

  it("開発環境ではすべてのログを返す", () => {
    const results = formatBattleLogs(logs, false, PLAYER_ID);
    expect(results).toHaveLength(4);
  });

  it("本番環境では playerId に関連するログのみ返す", () => {
    const results = formatBattleLogs(logs, true, PLAYER_ID);
    // actor_id === PLAYER_ID (1件) + target_id === PLAYER_ID (1件)
    expect(results).toHaveLength(2);
    expect(results.every(
      (r) => r.actor_id === PLAYER_ID || logs.find(
        (l) => l.actor_id === r.actor_id && l.target_id === PLAYER_ID
      )
    )).toBe(true);
  });

  it("本番環境で playerId が空文字のときはすべてのログを返す", () => {
    const results = formatBattleLogs(logs, true, "");
    expect(results).toHaveLength(4);
  });

  it("本番環境ではメッセージも抽象化される", () => {
    const productionLogs: BattleLog[] = [
      makeLog({ actor_id: PLAYER_ID, message: "300m から射撃 (命中: 60%) 40ダメージ", damage: 40 }),
    ];
    const results = formatBattleLogs(productionLogs, true, PLAYER_ID);
    expect(results[0].message).toBe("中距離 から射撃 ダメージ");
  });
});
