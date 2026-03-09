/* frontend/src/utils/logFormatter.ts */
import { BattleLog } from "@/types/battle";

/**
 * UI 表示に特化したログ表現
 */
export interface DisplayLog {
  turn: number;
  actor_id: string;
  action_type: BattleLog["action_type"];
  target_id?: string;
  /** 環境に応じて抽象化・フィルタリング済みのメッセージ */
  message: string;
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
 * ログの内容に応じた基本スタイル（Tailwind クラス）を返す。
 * 現在ターンのハイライトはコンポーネント側で付与する。
 */
function getLogStyle(log: BattleLog): DisplayLog["style"] {
  const msg = log.message;

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

  const isAttributeMessage =
    msg.includes("BEAM") ||
    msg.includes("PHYSICAL") ||
    msg.includes("ビーム") ||
    msg.includes("実弾");

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
 * @param _playerId   プレイヤー機体 ID（`formatBattleLogs` でのフィルタリングに使用。
 *                    単一ログ変換では未使用だがシグネチャの統一のために受け取る）
 */
export function formatBattleLog(
  log: BattleLog,
  isProduction: boolean,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _playerId: string
): DisplayLog {
  let message = log.message;

  if (isProduction) {
    message = abstractDistance(message);
    message = removeHitRate(message);
    message = abstractDamage(message, log.damage, log.target_max_hp);
  }

  return {
    turn: log.turn,
    actor_id: log.actor_id,
    action_type: log.action_type,
    target_id: log.target_id,
    message,
    style: getLogStyle(log),
  };
}

/**
 * `BattleLog[]` を `DisplayLog[]` へ変換する。
 * 本番環境（`isProduction === true`）では、`playerId` に関連するログのみを残す
 * （actor または target が playerId と一致するもの）。
 *
 * @param logs        変換対象のバトルログ配列
 * @param isProduction 本番向け抽象化フラグ
 * @param playerId    フィルタリング基準となるプレイヤー機体 ID
 */
export function formatBattleLogs(
  logs: BattleLog[],
  isProduction: boolean,
  playerId: string
): DisplayLog[] {
  const filtered =
    isProduction && playerId
      ? logs.filter(
          (log) =>
            log.actor_id === playerId ||
            (log.target_id != null && log.target_id === playerId)
        )
      : logs;

  return filtered.map((log) => formatBattleLog(log, isProduction, playerId));
}
