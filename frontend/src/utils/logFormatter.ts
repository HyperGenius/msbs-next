/* frontend/src/utils/logFormatter.ts */
import { BattleLog } from "@/types/battle";
import { EN_SHORTAGE_REASON_CODES } from "@/components/BattleViewer/utils";

/**
 * UI 表示に特化したログ表現
 */
export interface DisplayLog {
  timestamp: number;
  actor_id: string;
  action_type: BattleLog["action_type"];
  target_id?: string;
  /** 環境に応じて抽象化・フィルタリング済みのメッセージ */
  message: string;
  /** スキルが命中/回避の判定を変えた場合 true */
  skill_activated?: boolean;
  /** 表示スタイル（ターンハイライトを除く基本スタイル） */
  style: {
    borderStyle: string;
    bgStyle: string;
    textStyle: string;
  };
}

/**
 * 距離の数値（例: `450m`）を抽象化テキストに置換する。
 * 閾値は rankUtils.ts の getOptimalRangeLabel と統一。
 *   ≤ 200m → 近距離
 *   ≤ 400m → 中距離
 *   > 400m → 遠距離
 */
function abstractDistance(message: string): string {
  return message.replace(/(\d+(?:\.\d+)?)m/g, (_, num: string) => {
    const dist = parseFloat(num);
    if (dist <= 200) return "近距離";
    if (dist <= 400) return "中距離";
    return "遠距離";
  });
}

/**
 * `(命中: XX%)` の記述を削除する。
 */
function removeHitRate(message: string): string {
  return message.replace(/\s*\(命中:\s*\d+%\)/g, "").trim();
}

/**
 * ダメージ数値を抽象化テキストに置換する。
 * `targetMaxHp` が指定された場合は HP 割合ベースの4段階ラベルを使用する。
 * 未指定の場合は従来の絶対値ベース3段階ラベルにフォールバックする。
 *   targetMaxHp あり:
 *     ≥20% → 致命的なダメージ
 *     ≥10% → 手痛いダメージ
 *     ≥ 5% → ダメージ
 *     < 5% → 軽微なダメージ
 *   targetMaxHp なし（フォールバック）:
 *     ≥ 100 → 大ダメージ
 *     ≥  30 → ダメージ
 *     <  30 → 軽微なダメージ
 */
function abstractDamage(
  message: string,
  damage: number | undefined,
  targetMaxHp?: number
): string {
  if (damage === undefined) return message;
  let damageLabel: string;
  if (targetMaxHp !== undefined && targetMaxHp > 0) {
    const ratio = damage / targetMaxHp;
    if (ratio >= 0.20) damageLabel = "致命的なダメージ";
    else if (ratio >= 0.10) damageLabel = "手痛いダメージ";
    else if (ratio >= 0.05) damageLabel = "ダメージ";
    else damageLabel = "軽微なダメージ";
  } else {
    damageLabel =
      damage >= 100 ? "大ダメージ" : damage >= 30 ? "ダメージ" : "軽微なダメージ";
  }
  // 「N ダメージ」「ダメージ: N」「Nダメージ」の形式を対象に置換
  return message
    .replace(/\d+\s*ダメージ/g, damageLabel)
    .replace(/ダメージ[：:]\s*\d+/g, damageLabel);
}

/**
 * ログの文を返す。
 * 配信用ログは MOVE・WAIT・TARGET_SELECTION の `message` を省く。その行は構造化された項目から文を作る。
 * 作った文は機体名を含まない。表示する側が行の先頭に機体名を出す。
 *
 * @param names 機体 ID から機体名への対応。TARGET_SELECTION の相手の名前に使う
 */
export function describeBattleLog(log: BattleLog, names?: ReadonlyMap<string, string>): string {
  if (typeof log.message === "string") return log.message;
  switch (log.action_type) {
    case "MOVE":
      return "移動中";
    case "WAIT": {
      const reasonCode = log.details?.reason_code;
      const isEnShortage = typeof reasonCode === "string" && EN_SHORTAGE_REASON_CODES.has(reasonCode);
      return isEnShortage ? "ENが枯渇し、待機中" : "攻撃できず待機中";
    }
    case "TARGET_SELECTION": {
      const targetName = log.target_id ? (names?.get(log.target_id) ?? log.target_id) : "不明な機体";
      return `${targetName}をターゲットに選択`;
    }
    default:
      return "";
  }
}

/**
 * ログの内容に応じた基本スタイル（Tailwind クラス）を返す。
 * 現在ターンのハイライトはコンポーネント側で付与する。
 */
function getLogStyle(log: BattleLog, msg: string): DisplayLog["style"] {

  const isSkillActivated = log.skill_activated === true;

  const isResourceMessage =
    msg.includes("弾切れ") ||
    msg.includes("EN不足") ||
    msg.includes("クールダウン") ||
    msg.includes("待機") ||
    msg.includes("弾薬が尽き") ||
    msg.includes("ENが枯渇") ||
    msg.includes("冷却を待ち");

  const isTerrainMessage =
    log.action_type === "DETECTION" ||
    msg.includes("地形") ||
    msg.includes("索敵");

  const isTargetSelectionMessage = log.action_type === "TARGET_SELECTION";

  const isDisengageMessage = log.action_type === "DISENGAGE";

  const isClashMessage = log.action_type === "MELEE_CLASH";

  const isAttributeMessage =
    msg.includes("BEAM") ||
    msg.includes("PHYSICAL") ||
    msg.includes("ビーム") ||
    msg.includes("実弾");

  const isCriticalHit = msg.includes("★★ クリティカルヒット");

  const isLukEvasion = msg.includes("★ [LUK]");

  if (isCriticalHit) {
    return {
      borderStyle: "border-yellow-500",
      bgStyle: "",
      textStyle: "text-yellow-400 font-bold",
    };
  }
  if (isLukEvasion) {
    return {
      borderStyle: "border-sky-500",
      bgStyle: "",
      textStyle: "text-sky-400 font-semibold",
    };
  }
  if (isSkillActivated) {
    return {
      borderStyle: "border-amber-500",
      bgStyle: "",
      textStyle: "text-amber-400 font-semibold",
    };
  }
  if (isClashMessage) {
    return {
      borderStyle: "border-orange-400",
      bgStyle: "",
      textStyle: "text-orange-300 font-bold",
    };
  }
  if (isDisengageMessage) {
    return {
      borderStyle: "border-purple-500",
      bgStyle: "",
      textStyle: "text-purple-400 font-semibold",
    };
  }
  if (isResourceMessage) {
    return {
      borderStyle: "border-orange-500",
      bgStyle: "",
      textStyle: "text-orange-400 font-semibold",
    };
  }
  if (isTerrainMessage) {
    return {
      borderStyle: "border-cyan-500",
      bgStyle: "",
      textStyle: "text-cyan-400",
    };
  }
  if (isTargetSelectionMessage) {
    return {
      borderStyle: "border-blue-500",
      bgStyle: "",
      textStyle: "text-blue-400",
    };
  }
  if (isAttributeMessage) {
    return {
      borderStyle: "border-purple-500",
      bgStyle: "",
      textStyle: "text-purple-400",
    };
  }
  return {
    borderStyle: "border-green-900",
    bgStyle: "",
    textStyle: "text-green-600",
  };
}

/**
 * `BattleLog` を UI 表示用の `DisplayLog` へ変換する。
 *
 * @param log         変換対象のバトルログ
 * @param isProduction `true` のとき本番向け抽象化（距離・命中率・ダメージ）を適用する
 * @param _playerId   プレイヤー機体 ID（呼び出し元のシグネチャ統一のために受け取るが未使用）
 * @param names       機体 ID から機体名への対応。`describeBattleLog()` に渡す
 */
export function formatBattleLog(
  log: BattleLog,
  isProduction: boolean,
  _playerId: string,
  names?: ReadonlyMap<string, string>
): DisplayLog {
  const baseMessage = describeBattleLog(log, names);
  let message = baseMessage;

  if (isProduction) {
    message = abstractDistance(message);
    message = removeHitRate(message);
    message = abstractDamage(message, log.damage, log.target_max_hp);
  }

  return {
    timestamp: log.timestamp,
    actor_id: log.actor_id,
    action_type: log.action_type,
    target_id: log.target_id,
    message,
    skill_activated: log.skill_activated,
    style: getLogStyle(log, baseMessage),
  };
}
