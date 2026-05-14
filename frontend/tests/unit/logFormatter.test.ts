/* frontend/tests/unit/logFormatter.test.ts */
import { describe, it, expect } from "vitest";
import { formatBattleLog, formatBattleLogs, isProductionDebugLog } from "@/utils/logFormatter";
import { BattleLog } from "@/types/battle";

const PLAYER_ID = "player-001";

/** テスト用ログを生成するヘルパー */
function makeLog(overrides: Partial<BattleLog> = {}): BattleLog {
  return {
    timestamp: 0.1,
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

  it("actor_id / timestamp / action_type をそのまま引き継ぐ", () => {
    const log = makeLog({ timestamp: 0.5, action_type: "MISS" });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.timestamp).toBe(0.5);
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

// ─────────────────────────────────────────────
// abstractDamage — target_max_hp を使ったHP割合ベース変換
// ─────────────────────────────────────────────
describe("formatBattleLog – HP割合ベースのダメージ抽象化", () => {
  it("割合 ≥ 20% → 致命的なダメージ", () => {
    const log = makeLog({ message: "100ダメージを与えた", damage: 100, target_max_hp: 400 });
    const result = formatBattleLog(log, true, PLAYER_ID);
    // 100 / 400 = 25% → 致命的なダメージ
    expect(result.message).toBe("致命的なダメージを与えた");
  });

  it("割合 ≥ 10% かつ < 20% → 手痛いダメージ", () => {
    const log = makeLog({ message: "50ダメージを与えた", damage: 50, target_max_hp: 400 });
    const result = formatBattleLog(log, true, PLAYER_ID);
    // 50 / 400 = 12.5% → 手痛いダメージ
    expect(result.message).toBe("手痛いダメージを与えた");
  });

  it("割合 ≥ 5% かつ < 10% → ダメージ", () => {
    const log = makeLog({ message: "30ダメージを与えた", damage: 30, target_max_hp: 400 });
    const result = formatBattleLog(log, true, PLAYER_ID);
    // 30 / 400 = 7.5% → ダメージ
    expect(result.message).toBe("ダメージを与えた");
  });

  it("割合 < 5% → 軽微なダメージ", () => {
    const log = makeLog({ message: "10ダメージを与えた", damage: 10, target_max_hp: 400 });
    const result = formatBattleLog(log, true, PLAYER_ID);
    // 10 / 400 = 2.5% → 軽微なダメージ
    expect(result.message).toBe("軽微なダメージを与えた");
  });

  it("target_max_hp が 0 のときは絶対値ベースにフォールバックする", () => {
    const log = makeLog({ message: "150ダメージを与えた", damage: 150, target_max_hp: 0 });
    const result = formatBattleLog(log, true, PLAYER_ID);
    expect(result.message).toBe("大ダメージを与えた");
  });

  it("target_max_hp が未指定のときは絶対値ベースにフォールバックする", () => {
    const log = makeLog({ message: "150ダメージを与えた", damage: 150 });
    const result = formatBattleLog(log, true, PLAYER_ID);
    expect(result.message).toBe("大ダメージを与えた");
  });
});

// ─────────────────────────────────────────────
// getLogStyle — TARGET_SELECTION スタイル
// ─────────────────────────────────────────────
describe("formatBattleLog – TARGET_SELECTIONスタイル", () => {
  it("ターゲット選択ログはブルースタイル", () => {
    const log = makeLog({
      message: "[マ・クベ]のGelgoogは[戦術: 近距離優先]に従い、中距離にいるAcguyをターゲットに捕捉！",
      action_type: "TARGET_SELECTION",
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-blue-500");
    expect(result.style.textStyle).toContain("text-blue-400");
  });
});

// ─────────────────────────────────────────────
// getLogStyle — クリティカルヒット・LUK回避スタイル
// ─────────────────────────────────────────────
describe("formatBattleLog – クリティカルヒット・LUK回避スタイル", () => {
  it("★★ クリティカルヒットメッセージはイエロースタイル", () => {
    const log = makeLog({
      message: "[アムロ]のGundamが[ビーム・ライフル]で攻撃！ -> ★★ クリティカルヒット！！ 弱点を的確に捉え、Zakuに150ダメージ！（致命的なヒット）",
      damage: 150,
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-yellow-500");
    expect(result.style.textStyle).toContain("text-yellow-400");
  });

  it("★ [LUK]の奇跡メッセージはスカイスタイル", () => {
    const log = makeLog({
      message: "[アムロ]のGundamが[ビーム・ライフル]で攻撃！ -> 直撃コース！ しかしZakuは信じられない反射神経で紙一重の回避！ ★ [LUK]の奇跡が働いた！",
      action_type: "MISS",
      damage: 0,
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-sky-500");
    expect(result.style.textStyle).toContain("text-sky-400");
  });

  it("クリティカルヒットはリソースメッセージより優先される", () => {
    // ★★ クリティカルヒットが含まれる場合、他のキーワードより優先される
    const log = makeLog({
      message: "[アムロ]のGundamが[ビーム・ライフル]で攻撃！ -> ★★ クリティカルヒット！！ 弱点を的確に捉え、Zakuに100ダメージ！（致命的なヒット）",
      action_type: "ATTACK",
      damage: 100,
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-yellow-500");
  });
});

// ─────────────────────────────────────────────
// skill_activated — スキル発動ハイライト
// ─────────────────────────────────────────────
describe("formatBattleLog – skill_activated スタイル・フラグ", () => {
  it("skill_activated: true のときアンバースタイルが適用される", () => {
    const log = makeLog({
      message: "[アムロ]のGundamが[ビーム・ライフル]で攻撃！ -> 命中！ Zakuに大ダメージ！",
      action_type: "ATTACK",
      damage: 120,
      skill_activated: true,
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-amber-500");
    expect(result.style.textStyle).toContain("text-amber-400");
  });

  it("skill_activated: false のときアンバースタイルは適用されない", () => {
    const log = makeLog({
      message: "[アムロ]のGundamが[ビーム・ライフル]で攻撃！ -> 命中！ Zakuに大ダメージ！",
      action_type: "ATTACK",
      damage: 120,
      skill_activated: false,
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).not.toBe("border-amber-500");
  });

  it("skill_activated: undefined のときアンバースタイルは適用されない", () => {
    const log = makeLog({
      message: "攻撃した",
      action_type: "ATTACK",
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).not.toBe("border-amber-500");
  });

  it("skill_activated フラグが DisplayLog に引き継がれる (true)", () => {
    const log = makeLog({ skill_activated: true });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.skill_activated).toBe(true);
  });

  it("skill_activated フラグが DisplayLog に引き継がれる (undefined)", () => {
    const log = makeLog({});
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.skill_activated).toBeUndefined();
  });

  it("クリティカルヒットは skill_activated より優先される", () => {
    const log = makeLog({
      message: "[アムロ]のGundamが攻撃！ -> ★★ クリティカルヒット！！ Zakuに150ダメージ！",
      action_type: "ATTACK",
      damage: 150,
      skill_activated: true,
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    // クリティカルヒットがスキル発動より優先
    expect(result.style.borderStyle).toBe("border-yellow-500");
  });

  it("★ [LUK] 回避は skill_activated より優先される", () => {
    const log = makeLog({
      message: "攻撃！ -> ★ [LUK]の奇跡が働いた！",
      action_type: "MISS",
      skill_activated: true,
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-sky-500");
  });
});

// ─────────────────────────────────────────────
// 新形式の待機メッセージ — 武器名付きリソース不足
// ─────────────────────────────────────────────
describe("formatBattleLog – 新形式の待機メッセージスタイル", () => {
  it("冷却待ちメッセージ（新形式）はオレンジスタイル", () => {
    const log = makeLog({
      message: "[マ・クベ]のGelgoogは[ジャイアント・バズ]の冷却を待ちながら（残り2ターン）、やむなく待機",
      action_type: "WAIT",
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-orange-500");
    expect(result.style.textStyle).toContain("text-orange-400");
  });

  it("EN枯渇メッセージ（新形式）はオレンジスタイル", () => {
    const log = makeLog({
      message: "[マ・クベ]のGelgoogはENが枯渇し、[ビーム・サーベル]を使えず待機中",
      action_type: "WAIT",
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-orange-500");
    expect(result.style.textStyle).toContain("text-orange-400");
  });

  it("弾薬切れメッセージ（新形式）はオレンジスタイル", () => {
    const log = makeLog({
      message: "[マ・クベ]のGelgoogは[ジャイアント・バズ]の弾薬が尽き、攻撃手段がない",
      action_type: "WAIT",
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-orange-500");
    expect(result.style.textStyle).toContain("text-orange-400");
  });
});

// ─────────────────────────────────────────────
// 新形式の装甲軽減メッセージ — 戦闘描写スタイル
// ─────────────────────────────────────────────
describe("formatBattleLog – 新形式の装甲軽減メッセージスタイル", () => {
  it("高軽減・対実弾装甲（新形式）はパープルスタイル", () => {
    const log = makeLog({
      message: "[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！ (命中: 75%) -> 命中！ しかしAcguyの強固な対実弾装甲が衝撃を受け止め、ダメージは軽微に！ Acguyに50ダメージ！",
      action_type: "ATTACK",
      damage: 50,
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-purple-500");
    expect(result.style.textStyle).toContain("text-purple-400");
  });

  it("低軽減・対実弾装甲（新形式）はパープルスタイル", () => {
    const log = makeLog({
      message: "[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！ (命中: 75%) -> 命中！ Acguyの対実弾装甲をわずかに弾きながらも、Acguyに80ダメージ！",
      action_type: "ATTACK",
      damage: 80,
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-purple-500");
    expect(result.style.textStyle).toContain("text-purple-400");
  });

  it("高軽減・ビーム吸収コーティング（新形式）はパープルスタイル", () => {
    const log = makeLog({
      message: "[アムロ]のGundamが[ビーム・ライフル]で攻撃！ (命中: 80%) -> 命中！ しかしZakuの強固なビーム吸収コーティングが衝撃を受け止め、ダメージは軽微に！ Zakuに30ダメージ！",
      action_type: "ATTACK",
      damage: 30,
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-purple-500");
    expect(result.style.textStyle).toContain("text-purple-400");
  });

  it("低軽減・ビーム吸収コーティング（新形式）はパープルスタイル", () => {
    const log = makeLog({
      message: "[アムロ]のGundamが[ビーム・ライフル]で攻撃！ (命中: 80%) -> 命中！ Zakuのビーム吸収コーティングをわずかに弾きながらも、Zakuに90ダメージ！",
      action_type: "ATTACK",
      damage: 90,
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-purple-500");
    expect(result.style.textStyle).toContain("text-purple-400");
  });
});

// ─────────────────────────────────────────────
// 新形式の攻撃ログ — 武器名付き攻撃メッセージ
// ─────────────────────────────────────────────
describe("formatBattleLog – 武器名付き攻撃ログ", () => {
  it("武器名付き攻撃ログが正しくメッセージを保持する（開発環境）", () => {
    const log = makeLog({
      message: "[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！ (命中: 75%) -> 命中！ Acguyに80ダメージ！（ダメージ）",
      action_type: "ATTACK",
      damage: 80,
      weapon_name: "ジャイアント・バズ",
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.message).toContain("[ジャイアント・バズ]");
    expect(result.message).toContain("命中: 75%");
  });

  it("武器名付き攻撃ログは本番環境で命中率が除去される", () => {
    const log = makeLog({
      message: "[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！ (命中: 75%) -> 命中！ Acguyに80ダメージ！（ダメージ）",
      action_type: "ATTACK",
      damage: 80,
      weapon_name: "ジャイアント・バズ",
    });
    const result = formatBattleLog(log, true, PLAYER_ID);
    expect(result.message).toContain("[ジャイアント・バズ]");
    expect(result.message).not.toContain("命中:");
  });

  it("格闘攻撃ログ（武器なし）が正しく表示される", () => {
    const log = makeLog({
      message: "[アムロ]のGundamが[格闘]で攻撃！ (命中: 70%) -> 命中！ Zakuに60ダメージ！（ダメージ）",
      action_type: "ATTACK",
      damage: 60,
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.message).toContain("[格闘]");
  });
});

// ─────────────────────────────────────────────
// 新形式のターゲット選択メッセージ — 各戦術のナラティブログ
// ─────────────────────────────────────────────
describe("formatBattleLog – 新形式ターゲット選択メッセージ", () => {
  it("CLOSEST戦術のナラティブメッセージはブルースタイル", () => {
    const log = makeLog({
      message: "[マ・クベ]のGelgoogは[戦術: 近距離優先]に従い、中距離にいるAcguyをターゲットに捕捉！",
      action_type: "TARGET_SELECTION",
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-blue-500");
    expect(result.style.textStyle).toContain("text-blue-400");
  });

  it("WEAKEST戦術のナラティブメッセージはブルースタイル", () => {
    const log = makeLog({
      message: "[アムロ]のGundamは[戦術: 弱体ターゲット優先]でスキャン。HP: 45のZakuを狙い撃ちにする！",
      action_type: "TARGET_SELECTION",
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-blue-500");
    expect(result.style.textStyle).toContain("text-blue-400");
  });

  it("STRONGEST戦術のナラティブメッセージはブルースタイル", () => {
    const log = makeLog({
      message: "Gundamは[戦術: 高脅威ターゲット優先]に従い、Zaku（戦略価値: 100.0）を最優先ターゲットに設定！",
      action_type: "TARGET_SELECTION",
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-blue-500");
    expect(result.style.textStyle).toContain("text-blue-400");
  });

  it("THREAT戦術のナラティブメッセージはブルースタイル", () => {
    const log = makeLog({
      message: "Gundamは[戦術: 最大脅威優先]で判断し、最も危険なZaku（脅威度: 1.23）を排除対象に選定！",
      action_type: "TARGET_SELECTION",
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-blue-500");
    expect(result.style.textStyle).toContain("text-blue-400");
  });

  it("RANDOM戦術のナラティブメッセージはブルースタイル", () => {
    const log = makeLog({
      message: "GundamはランダムにZakuをターゲットに選択した",
      action_type: "TARGET_SELECTION",
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-blue-500");
    expect(result.style.textStyle).toContain("text-blue-400");
  });

  it("本番環境でも[戦術: ...]の表記はそのまま保持される", () => {
    const log = makeLog({
      message: "[マ・クベ]のGelgoogは[戦術: 近距離優先]に従い、中距離にいるAcguyをターゲットに捕捉！",
      action_type: "TARGET_SELECTION",
    });
    const result = formatBattleLog(log, true, PLAYER_ID);
    expect(result.message).toContain("[戦術: 近距離優先]");
    expect(result.message).toContain("中距離");
  });
});

// ─────────────────────────────────────────────
// 新形式の索敵ログ — 演出的な発見メッセージ
// ─────────────────────────────────────────────
describe("formatBattleLog – 新形式索敵ログ", () => {
  it("通常の発見メッセージはシアンスタイル", () => {
    const log = makeLog({
      message: "[アムロ]のGundamが近距離にZakuを発見！",
      action_type: "DETECTION",
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-cyan-500");
    expect(result.style.textStyle).toContain("text-cyan-400");
  });

  it("ミノフスキー粒子の中での発見メッセージはシアンスタイル", () => {
    const log = makeLog({
      message: "[マ・クベ]のGelgoogが濃密なミノフスキー粒子の中、中距離にリック・ドムの反応を捉えた！",
      action_type: "DETECTION",
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.style.borderStyle).toBe("border-cyan-500");
    expect(result.style.textStyle).toContain("text-cyan-400");
  });

  it("本番環境で距離ラベルはそのまま保持される（数値変換なし）", () => {
    const log = makeLog({
      message: "[アムロ]のGundamが中距離にZakuを発見！",
      action_type: "DETECTION",
    });
    const result = formatBattleLog(log, true, PLAYER_ID);
    // バックエンドがすでに抽象化したラベルなので再変換されない
    expect(result.message).toContain("中距離");
    expect(result.message).not.toMatch(/\d+m/);
  });
});

// ─────────────────────────────────────────────
// 新形式の命中/ミスログ — 距離状況の組み込み
// ─────────────────────────────────────────────
describe("formatBattleLog – 新形式命中・ミスログの距離コンテキスト", () => {
  it("最適射程でのクリーンヒットメッセージが正しく表示される（開発環境）", () => {
    const log = makeLog({
      message: "[アムロ]のGundamが[ビーム・ライフル]で攻撃！ (命中: 85%) -> 最適射程でクリーンヒット！ Zakuに100ダメージ！（手痛いダメージ）",
      action_type: "ATTACK",
      damage: 100,
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.message).toContain("最適射程でクリーンヒット！");
    expect(result.message).toContain("命中: 85%");
  });

  it("最適射程クリーンヒット - 本番環境で命中率が削除される", () => {
    const log = makeLog({
      message: "[アムロ]のGundamが[ビーム・ライフル]で攻撃！ (命中: 85%) -> 最適射程でクリーンヒット！ Zakuに100ダメージ！（手痛いダメージ）",
      action_type: "ATTACK",
      damage: 100,
    });
    const result = formatBattleLog(log, true, PLAYER_ID);
    expect(result.message).toContain("最適射程でクリーンヒット！");
    expect(result.message).not.toContain("命中:");
  });

  it("距離不一致による回避メッセージが正しく表示される（開発環境）", () => {
    const log = makeLog({
      message: "[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！ (命中: 30%) -> 距離が合わず、Acguyに回避された！",
      action_type: "MISS",
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.message).toContain("距離が合わず");
    expect(result.message).toContain("回避された！");
    expect(result.message).toContain("命中: 30%");
  });

  it("距離不一致による回避メッセージ - 本番環境で命中率が削除される", () => {
    const log = makeLog({
      message: "[マ・クベ]のGelgoogが[ジャイアント・バズ]で攻撃！ (命中: 30%) -> 距離が合わず、Acguyに回避された！",
      action_type: "MISS",
    });
    const result = formatBattleLog(log, true, PLAYER_ID);
    expect(result.message).toContain("距離が合わず");
    expect(result.message).not.toContain("命中:");
  });
});

// ─────────────────────────────────────────────
// UNKNOWN機 — 未索敵表示（ログメッセージ内）
// ─────────────────────────────────────────────
describe("formatBattleLog – UNKNOWN機 メッセージ表示", () => {
  it("UNKNOWN機を含むメッセージが正しく返される（本番環境）", () => {
    const log = makeLog({
      message: "UNKNOWN機が[ビーム・ライフル]で攻撃！ (命中: 60%) -> 命中！ Gundamに50ダメージ！（ダメージ）",
      action_type: "ATTACK",
      damage: 50,
    });
    const result = formatBattleLog(log, true, PLAYER_ID);
    // 距離表記がないのでそのまま、命中率が削除され、ダメージが抽象化される
    expect(result.message).toContain("UNKNOWN機");
    expect(result.message).not.toContain("命中:");
  });

  it("UNKNOWN機を含むメッセージが正しく返される（開発環境）", () => {
    const log = makeLog({
      message: "UNKNOWN機が[ビーム・ライフル]で攻撃！ (命中: 60%) -> 命中！ Gundamに50ダメージ！",
      action_type: "ATTACK",
      damage: 50,
    });
    const result = formatBattleLog(log, false, PLAYER_ID);
    expect(result.message).toContain("UNKNOWN機");
    expect(result.message).toContain("命中: 60%");
  });
});

// ─────────────────────────────────────────────
// isProductionDebugLog — デバッグログ判定
// ─────────────────────────────────────────────
describe("isProductionDebugLog", () => {
  it("「ファジィ推論」を含むメッセージは true を返す", () => {
    expect(isProductionDebugLog("GelgoogはファジィでZaku IIを最優先ターゲットに決定（優先度スコア: 0.868）")).toBe(true);
  });

  it("「優先度スコア」を含むメッセージは true を返す", () => {
    expect(isProductionDebugLog("優先度スコア: 0.75 で決定")).toBe(true);
  });

  it("「UNKNOWN機」を含むメッセージは true を返す", () => {
    expect(isProductionDebugLog("UNKNOWN機が中距離にDom (NPC)を発見！（索敵確率 82%）")).toBe(true);
  });

  it("「[FUZZY]」を含むメッセージは true を返す", () => {
    expect(isProductionDebugLog("[FUZZY] ファジィ推論の中間スコア: 0.5")).toBe(true);
  });

  it("デバッグパターンを含まない通常メッセージは false を返す", () => {
    expect(isProductionDebugLog("[アムロ]のGundamが[ビーム・ライフル]で攻撃！")).toBe(false);
  });

  it("空文字列は false を返す", () => {
    expect(isProductionDebugLog("")).toBe(false);
  });

  it("デバッグパターンの一部のみ含む場合も true を返す（ファジィ推論）", () => {
    expect(isProductionDebugLog("ファジィ推論を適用中")).toBe(true);
  });
});

// ─────────────────────────────────────────────
// formatBattleLogs — デバッグログフィルタリング（本番環境）
// ─────────────────────────────────────────────
describe("formatBattleLogs – 本番環境デバッグログフィルタリング", () => {
  it("本番環境では「ファジィ推論」を含むログを除外する", () => {
    const logs: BattleLog[] = [
      makeLog({ actor_id: PLAYER_ID, message: "GelgoogはファジィでZaku IIを最優先ターゲットに決定（優先度スコア: 0.868）" }),
      makeLog({ actor_id: PLAYER_ID, message: "通常の行動ログ" }),
    ];
    const results = formatBattleLogs(logs, true, PLAYER_ID);
    expect(results).toHaveLength(1);
    expect(results[0].message).toBe("通常の行動ログ");
  });

  it("本番環境では「優先度スコア」を含むログを除外する", () => {
    const logs: BattleLog[] = [
      makeLog({ actor_id: PLAYER_ID, message: "優先度スコア: 0.75 で決定" }),
      makeLog({ actor_id: PLAYER_ID, message: "移動した" }),
    ];
    const results = formatBattleLogs(logs, true, PLAYER_ID);
    expect(results).toHaveLength(1);
    expect(results[0].message).toBe("移動した");
  });

  it("本番環境では「UNKNOWN機」を含むログを除外する", () => {
    const logs: BattleLog[] = [
      makeLog({ actor_id: "enemy-001", message: "UNKNOWN機が中距離にDomを発見！（索敵確率 82%）", target_id: PLAYER_ID }),
      makeLog({ actor_id: PLAYER_ID, message: "攻撃した" }),
    ];
    const results = formatBattleLogs(logs, true, PLAYER_ID);
    // UNKNOWN機のログは除外（target_id === PLAYER_ID でも除外）
    expect(results).toHaveLength(1);
    expect(results[0].message).toBe("攻撃した");
  });

  it("本番環境では「[FUZZY]」を含むログを除外する", () => {
    const logs: BattleLog[] = [
      makeLog({ actor_id: PLAYER_ID, message: "[FUZZY] デバッグ情報" }),
      makeLog({ actor_id: PLAYER_ID, message: "行動ログ" }),
    ];
    const results = formatBattleLogs(logs, true, PLAYER_ID);
    expect(results).toHaveLength(1);
    expect(results[0].message).toBe("行動ログ");
  });

  it("開発環境ではデバッグログを除外しない", () => {
    const logs: BattleLog[] = [
      makeLog({ actor_id: PLAYER_ID, message: "GelgoogはファジィでZaku IIを最優先ターゲットに決定（優先度スコア: 0.868）" }),
      makeLog({ actor_id: PLAYER_ID, message: "通常の行動ログ" }),
    ];
    const results = formatBattleLogs(logs, false, PLAYER_ID);
    expect(results).toHaveLength(2);
  });
});
