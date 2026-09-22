/* frontend/src/components/BattleViewer/hooks/useBattleChapters.ts */
import { useMemo } from "react";
import { BattleLog, MobileSuit } from "@/types/battle";

/** チャプターの種別。演出用のアイコン・配色の出し分けに使う */
export type ChapterKind = "COMBO" | "CRITICAL" | "DESTROYED_ENEMY" | "DESTROYED_SELF" | "DETECTION";

/** チャプタートラックに表示する1件分のイベント（Issue #521） */
export interface ChapterEvent {
  id: string;
  timestamp: number;
  kind: ChapterKind;
  icon: string;
  label: string;
  detail?: string;
  accentColor: string;
}

const KIND_STYLE: Record<ChapterKind, { icon: string; accentColor: string }> = {
  COMBO: { icon: "⚔", accentColor: "#4ade80" },
  CRITICAL: { icon: "💥", accentColor: "#ff5555" },
  DESTROYED_ENEMY: { icon: "☠", accentColor: "#facc15" },
  DESTROYED_SELF: { icon: "☠", accentColor: "#ef4444" },
  DETECTION: { icon: "📡", accentColor: "#22d3ee" },
};

function nameOf(id: string, player: { id: string; name: string }, enemies: MobileSuit[]): string {
  if (id === player.id) return player.name;
  return enemies.find((e) => e.id === id)?.name ?? id;
}

/**
 * 自機関連ログから「読むログ」ではなく「ジャンプ先」としてのチャプターのみを抽出する。
 * 通常のATTACK/MISSは対象外とし、格闘コンボ・クリティカル・撃破・自機起点の索敵成功のみを拾う
 * （方針の詳細はIssue #521のモックアップ: https://claude.ai/artifact/RNmQeBem8BFxyuYDXhontS）。
 * 表示文言は message の自由文ではなく action_type 等の構造化フィールドから組み立てる。
 */
export function computeBattleChapters(
  logs: BattleLog[],
  player: { id: string; name: string },
  enemies: MobileSuit[]
): ChapterEvent[] {
  const chapters: ChapterEvent[] = [];

  logs.forEach((log, index) => {
    const isSelfActor = log.actor_id === player.id;
    const isSelfTarget = log.target_id === player.id;

    if (log.action_type === "MELEE_COMBO" && isSelfActor) {
      const style = KIND_STYLE.COMBO;
      chapters.push({
        id: `${index}-combo`,
        timestamp: log.timestamp,
        kind: "COMBO",
        icon: style.icon,
        accentColor: style.accentColor,
        label: log.combo_count ? `${log.combo_count}HIT格闘コンボ` : "格闘コンボ",
        detail: log.damage != null ? `-${log.damage}` : undefined,
      });
      return;
    }

    if (log.action_type === "ATTACK" && log.is_crit && (isSelfActor || isSelfTarget)) {
      const style = KIND_STYLE.CRITICAL;
      chapters.push({
        id: `${index}-critical`,
        timestamp: log.timestamp,
        kind: "CRITICAL",
        icon: style.icon,
        accentColor: style.accentColor,
        label: log.weapon_name ? `${log.weapon_name} クリティカルヒット` : "クリティカルヒット",
        detail: log.damage != null ? `-${log.damage}` : undefined,
      });
      return;
    }

    if (log.action_type === "DESTROYED") {
      const isSelf = log.actor_id === player.id;
      const isEnemy = enemies.some((e) => e.id === log.actor_id);
      if (isSelf) {
        const style = KIND_STYLE.DESTROYED_SELF;
        chapters.push({
          id: `${index}-destroyed-self`,
          timestamp: log.timestamp,
          kind: "DESTROYED_SELF",
          icon: style.icon,
          accentColor: style.accentColor,
          label: "自機が撃破された",
        });
      } else if (isEnemy) {
        const style = KIND_STYLE.DESTROYED_ENEMY;
        chapters.push({
          id: `${index}-destroyed-enemy`,
          timestamp: log.timestamp,
          kind: "DESTROYED_ENEMY",
          icon: style.icon,
          accentColor: style.accentColor,
          label: `${nameOf(log.actor_id, player, enemies)}を撃破`,
        });
      }
      return;
    }

    if (log.action_type === "DETECTION" && isSelfActor && log.target_id) {
      const style = KIND_STYLE.DETECTION;
      chapters.push({
        id: `${index}-detection`,
        timestamp: log.timestamp,
        kind: "DETECTION",
        icon: style.icon,
        accentColor: style.accentColor,
        label: `${nameOf(log.target_id, player, enemies)}を発見`,
      });
    }
  });

  return chapters;
}

/**
 * `computeBattleChapters` をメモ化するフック。
 * `logs` の参照が変わらない限り再計算しない（BattleViewer 全体の再計算方針に合わせる）。
 * 依存配列には `player` オブジェクトの参照ではなく `id`/`name` のプリミティブを使う。
 * 呼び出し側が `{id, name}` をレンダーのたびにインライン生成しても、参照比較では
 * ないため不要な再計算が起きない。
 */
export function useBattleChapters(
  logs: BattleLog[],
  player: { id: string; name: string } | null,
  enemies: MobileSuit[]
): ChapterEvent[] {
  const playerId = player?.id;
  const playerName = player?.name;
  return useMemo(() => {
    if (!playerId || !playerName) return [];
    return computeBattleChapters(logs, { id: playerId, name: playerName }, enemies);
  }, [logs, playerId, playerName, enemies]);
}
