/* frontend/src/components/BattleViewer/hooks/useBattleChapters.ts */
import { useMemo } from "react";
import { BattleLog, MobileSuit } from "@/types/battle";

/** チャプターの種別。演出用のアイコン・配色の出し分けに使う */
export type ChapterKind =
  | "COMBO"
  | "CRITICAL"
  | "DESTROYED_ENEMY"
  | "DESTROYED_SELF"
  | "DESTROYED_ALLY"
  | "DETECTION"
  | "DISENGAGE"
  | "CLASH";

/** チャプター抽出に使う自機の情報。`team_id` はソロ参加なら null（僚機なし） */
export interface ChapterPlayer {
  id: string;
  name: string;
  team_id?: string | null;
}

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
  // 自機識別リングと同じ青で「味方側の出来事」を示す（BattleViewer パレットの既存色）
  DESTROYED_ALLY: { icon: "☠", accentColor: "#4488ff" },
  DETECTION: { icon: "📡", accentColor: "#22d3ee" },
  DISENGAGE: { icon: "↩", accentColor: "#6fe6ff" },
  CLASH: { icon: "⚡", accentColor: "#ffd84a" },
};

function nameOf(id: string, player: ChapterPlayer, enemies: MobileSuit[]): string {
  if (id === player.id) return player.name;
  return enemies.find((e) => e.id === id)?.name ?? id;
}

/**
 * `DESTROYED` ログの撃破者を推定する。見つからなければ null。
 * `DESTROYED` ログの `actor_id` は被撃破ユニット自身で撃破者を持たないため、直前のログが
 * 同じ対象への `ATTACK`/`MELEE_COMBO` ならその `actor_id` を撃破者とみなす。
 * 戦果画面の撃墜数と食い違わないよう、バックエンドの `compute_unit_kills`（battle_digest.py）と同じ規則にしている。
 */
function findDestroyer(logs: BattleLog[], index: number): string | null {
  if (index === 0) return null;
  const prev = logs[index - 1];
  const destroyed = logs[index];
  if ((prev.action_type === "ATTACK" || prev.action_type === "MELEE_COMBO") && prev.target_id === destroyed.actor_id) {
    return prev.actor_id;
  }
  return null;
}

/**
 * 自機・自チーム関連ログから「読むログ」ではなく「ジャンプ先」としてのチャプターのみを抽出する。
 * 通常のATTACK/MISSは対象外とし、格闘コンボ・クリティカル・撃破・自機起点の索敵成功・自機の仕切り直し・自機が絡む鍔迫り合いのみを拾う。
 * 撃破は自機・僚機の被撃破と、自機・僚機による敵機の撃破に限る（Issue #676）
 * （方針の詳細はIssue #521のモックアップ: https://claude.ai/artifact/RNmQeBem8BFxyuYDXhontS）。
 * 表示文言は message の自由文ではなく action_type 等の構造化フィールドから組み立てる。
 */
export function computeBattleChapters(
  logs: BattleLog[],
  player: ChapterPlayer,
  enemies: MobileSuit[]
): ChapterEvent[] {
  const chapters: ChapterEvent[] = [];
  // enemies は「自機以外の全ユニット」で僚機も含む。ソロ参加のプレイヤーは team_id が null だが、
  // enemies 側はシミュレーターが自動付与した team_id を持つため、null 同士を一致とみなさないよう先に弾く
  const allyIds = new Set(
    player.team_id ? enemies.filter((e) => e.team_id === player.team_id).map((e) => e.id) : []
  );

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
      if (log.actor_id === player.id) {
        const style = KIND_STYLE.DESTROYED_SELF;
        chapters.push({
          id: `${index}-destroyed-self`,
          timestamp: log.timestamp,
          kind: "DESTROYED_SELF",
          icon: style.icon,
          accentColor: style.accentColor,
          label: "自機が撃破された",
        });
      } else if (allyIds.has(log.actor_id)) {
        const style = KIND_STYLE.DESTROYED_ALLY;
        chapters.push({
          id: `${index}-destroyed-ally`,
          timestamp: log.timestamp,
          kind: "DESTROYED_ALLY",
          icon: style.icon,
          accentColor: style.accentColor,
          label: `僚機${nameOf(log.actor_id, player, enemies)}が撃破された`,
        });
      } else if (enemies.some((e) => e.id === log.actor_id)) {
        // 敵機の撃破は自機・僚機が撃破したものだけを出す（第三者同士の撃破や撃破者不明のログは出さない）
        const destroyerId = findDestroyer(logs, index);
        if (destroyerId && (destroyerId === player.id || allyIds.has(destroyerId))) {
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
      }
      return;
    }

    if (log.action_type === "DISENGAGE" && isSelfActor) {
      const style = KIND_STYLE.DISENGAGE;
      chapters.push({
        id: `${index}-disengage`,
        timestamp: log.timestamp,
        kind: "DISENGAGE",
        icon: style.icon,
        accentColor: style.accentColor,
        label: log.target_id ? `${nameOf(log.target_id, player, enemies)}から仕切り直し` : "仕切り直し",
      });
      return;
    }

    if (log.action_type === "MELEE_CLASH" && (isSelfActor || isSelfTarget)) {
      const style = KIND_STYLE.CLASH;
      const opponentId = isSelfActor ? log.target_id : log.actor_id;
      chapters.push({
        id: `${index}-clash`,
        timestamp: log.timestamp,
        kind: "CLASH",
        icon: style.icon,
        accentColor: style.accentColor,
        label: opponentId ? `${nameOf(opponentId, player, enemies)}と鍔迫り合い` : "鍔迫り合い",
      });
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
 * 依存配列には `player` オブジェクトの参照ではなく `id`/`name`/`team_id` のプリミティブを使う。
 * 呼び出し側が `{id, name, team_id}` をレンダーのたびにインライン生成しても、参照比較では
 * ないため不要な再計算が起きない。
 */
export function useBattleChapters(
  logs: BattleLog[],
  player: ChapterPlayer | null,
  enemies: MobileSuit[]
): ChapterEvent[] {
  const playerId = player?.id;
  const playerName = player?.name;
  const playerTeamId = player?.team_id ?? null;
  return useMemo(() => {
    if (!playerId || !playerName) return [];
    return computeBattleChapters(logs, { id: playerId, name: playerName, team_id: playerTeamId }, enemies);
  }, [logs, playerId, playerName, playerTeamId, enemies]);
}
