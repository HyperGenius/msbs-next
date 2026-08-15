/* frontend/src/components/BattleViewer/hooks/useBattleSnapshot.ts */

import { BattleLog, MobileSuit } from "@/types/battle";
import { DEFAULT_MAX_EN, EN_WARNING_THRESHOLD } from "../utils";
import { WarningType } from "../types";

/** 浮動小数点数の誤差許容値（タイムスタンプ比較用） */
const TIMESTAMP_EPSILON = 1e-9;

/**
 * 物理補間（velocity外挿）を適用する最大時間（秒）。
 * MOVE ログは残距離が MOVE_LOG_MIN_DIST 未満になると出力されなくなるため、
 * 停止・撃破後は velocity_snapshot が更新されないまま古い速度ベクトルが残り続ける。
 * dt に上限を設けないと、そのまま停止/撃破後も古い速度で位置を外挿し続けてしまい、
 * 戦闘終盤ほど実際の位置から大きくズレた場所に照準線・攻撃ラインが表示される
 * （BattleViewerで照準線が無関係な方向を指す不具合の原因）。
 */
const MAX_VELOCITY_EXTRAPOLATION_SECONDS = 1.0;

/** 角度を最短回転方向で線形補間する（度数法） */
function lerpAngle(from: number, to: number, t: number): number {
    const diff = ((to - from + 180) % 360) - 180;
    return from + diff * t;
}

export interface UnitSnapshot {
    pos: { x: number; y: number; z: number };
    hp: number;
    en: number;
    ammo: Record<string, number>;
    warnings: WarningType[];
    /** 現在の胴体向き（度数法）— BattleViewer向き矢印表示用 */
    heading?: number;
    /** 現在のターゲットMS ID — BattleViewer照準線・ハイライト表示用 */
    targetId?: string;
}

/**
 * getBattleSnapshot の差分更新用キャッシュエントリ。
 * 「前回どこまでログを読んだか（nextIndex）」と「その時点の状態」を保持し、
 * 再生が進む（currentTimestamp が増える）限りは続きからのみ走査すればよいようにする。
 */
interface SnapshotCacheEntry {
    /** このエントリがどの logs 配列に対して計算されたものか（バトルが変われば作り直す） */
    logs: BattleLog[];
    /** 直近に計算した currentTimestamp */
    timestamp: number;
    /** 次に走査すべき logs のインデックス（このインデックスより前は処理済み） */
    nextIndex: number;
    pos: { x: number; y: number; z: number };
    hp: number;
    en: number;
    ammo: Record<string, number>;
    heading?: number;
    prevHeadingTs?: number;
    unitTargetId?: string;
    lastVelocity?: { x: number; y: number; z: number };
    lastVelocityPos?: { x: number; y: number; z: number };
    lastVelocityTs?: number;
    /** 直近（currentTimestamp以下）の自ユニットのATTACK発生時刻。クールダウン判定用（未攻撃時は -Infinity） */
    lastAttackTimestamp: number;
}

/** targetId（+任意のサフィックス）ごとに SnapshotCacheEntry を保持するキャッシュ */
export type SnapshotCache = Map<string, SnapshotCacheEntry>;

function createInitialEntry(initialMs: MobileSuit, logs: BattleLog[]): SnapshotCacheEntry {
    const ammo: Record<string, number> = {};
    initialMs.weapons.forEach(weapon => {
        if (weapon.max_ammo !== null && weapon.max_ammo !== undefined) {
            ammo[weapon.id] = weapon.max_ammo;
        }
    });
    return {
        logs,
        timestamp: -Infinity,
        nextIndex: 0,
        pos: initialMs.position,
        hp: initialMs.max_hp, // 戦闘開始時は満タンと仮定
        en: initialMs.max_en || DEFAULT_MAX_EN,
        ammo,
        // 未攻撃時に 0 を使うと、戦闘開始直後（currentTimestamp が小さい）でも
        // 「直近0秒に攻撃した」とみなされクールダウン警告が誤表示されるため、
        // 「まだ攻撃していない」ことを表す -Infinity で初期化する
        lastAttackTimestamp: -Infinity,
    };
}

// 現在のタイムスタンプ時点での情報を計算する関数（Hookではない）
//
// cache を渡すと「前回状態＋前回スキャン位置」を保持した差分更新になり、
// 再生が進行するだけ（currentTimestamp が単調増加するだけ）であれば
// 前回処理済みのログを読み直さずに続きから走査する（Issue #465）。
// cache を渡さない場合や、currentTimestamp が巻き戻った場合（シーク操作等）は
// 従来どおり先頭からの全走査で状態を再構築する。
// cacheKey 省略時は targetId をキーに使う（同一ユニットで複数の基準時刻を追う場合に指定する）。
export function getBattleSnapshot(
    targetId: string,
    initialMs: MobileSuit,
    logs: BattleLog[],
    currentTimestamp: number,
    cache?: SnapshotCache,
    cacheKey: string = targetId
): UnitSnapshot {
    const cached = cache?.get(cacheKey);
    const canResume =
        cached !== undefined &&
        cached.logs === logs &&
        currentTimestamp >= cached.timestamp - TIMESTAMP_EPSILON;
    const entry = canResume ? cached! : createInitialEntry(initialMs, logs);

    // 前回のスキャン位置（nextIndex）から続きを走査して状態を差分更新する
    for (let i = entry.nextIndex; i < logs.length; i++) {
        const log = logs[i];
        if (log.timestamp > currentTimestamp + TIMESTAMP_EPSILON) break;
        entry.nextIndex = i + 1;

        // 位置更新
        if (log.actor_id === targetId && log.position_snapshot) {
            entry.pos = log.position_snapshot;
        }

        // velocity_snapshot を記録（ログ間の物理補間用）
        if (log.actor_id === targetId && log.velocity_snapshot) {
            entry.lastVelocity = log.velocity_snapshot;
            entry.lastVelocityPos = log.position_snapshot;
            entry.lastVelocityTs = log.timestamp;
        }

        // 向き更新（自ユニットのログに heading フィールドがあれば取得）
        if (log.actor_id === targetId && log.heading !== undefined) {
            entry.heading = log.heading;
            entry.prevHeadingTs = log.timestamp;
        }

        // ターゲット更新（TARGET_SELECTION ログから現在のターゲットを追跡）
        if (log.actor_id === targetId && log.action_type === "TARGET_SELECTION" && log.target_id) {
            entry.unitTargetId = log.target_id;
        }

        // HP更新
        if (log.action_type === "DAMAGE" && log.actor_id === targetId && log.damage) {
            entry.hp -= log.damage;
        }
        if ((log.action_type === "ATTACK" || log.action_type === "MELEE_COMBO") && log.target_id === targetId && log.damage) {
            entry.hp -= log.damage;
        }

        // リソース消費・クールダウン基準時刻の更新: log.weapon_id から実際に使用した武器を特定する
        // weapon_id が無い古いログについては後方互換のため先頭武器を使用したと仮定する
        if (log.action_type === "ATTACK" && log.actor_id === targetId) {
            entry.lastAttackTimestamp = log.timestamp;
            const weapon = log.weapon_id
                ? initialMs.weapons.find(w => w.id === log.weapon_id) ?? initialMs.weapons[0]
                : initialMs.weapons[0];
            if (weapon) {
                if (weapon.en_cost) {
                    entry.en = Math.max(0, entry.en - weapon.en_cost);
                }
                if (weapon.max_ammo && entry.ammo[weapon.id] !== undefined) {
                    entry.ammo[weapon.id] = Math.max(0, entry.ammo[weapon.id] - 1);
                }
            }
        }
    }
    entry.timestamp = currentTimestamp;

    // heading補間: 前後のheadingログの間を線形補間してスムーズな向き変化を実現する
    // entry.nextIndex より前は処理済み（=currentTimestamp以下）なので、未来側の探索は
    // そこから始めればよく、毎回先頭から探し直す必要はない
    let heading = entry.heading;
    if (heading !== undefined && entry.prevHeadingTs !== undefined) {
        for (let i = entry.nextIndex; i < logs.length; i++) {
            const log = logs[i];
            if (log.actor_id === targetId && log.heading !== undefined) {
                const t = (currentTimestamp - entry.prevHeadingTs) / (log.timestamp - entry.prevHeadingTs);
                heading = lerpAngle(heading, log.heading, Math.max(0, Math.min(1, t)));
                break;
            }
        }
    }

    // 物理補間: pos = prev_pos + velocity × dt（ログ間の滑らかな移動表示）
    // dt が MAX_VELOCITY_EXTRAPOLATION_SECONDS を超える場合は外挿を行わない
    // （撃破後など velocity_snapshot の更新が止まった場合に、古い速度ベクトルのまま
    // 無限に外挿されて実際の位置から大きくズレるのを防ぐ。この場合 pos は上のループで
    // 設定済みの最後の position_snapshot のままになる）
    let pos = entry.pos;
    if (entry.lastVelocity && entry.lastVelocityTs !== undefined && entry.lastVelocityPos !== undefined) {
        const dt = currentTimestamp - entry.lastVelocityTs;
        if (dt > 0 && dt <= MAX_VELOCITY_EXTRAPOLATION_SECONDS) {
            pos = {
                x: entry.lastVelocityPos.x + entry.lastVelocity.x * dt,
                y: entry.lastVelocityPos.y + entry.lastVelocity.y * dt,
                z: entry.lastVelocityPos.z + entry.lastVelocity.z * dt,
            };
        }
    }

    // 警告状態を判定
    const warnings: WarningType[] = [];
    // EN不足: EN_WARNING_THRESHOLD以下
    const maxEn = initialMs.max_en || DEFAULT_MAX_EN;
    if (maxEn > 0 && entry.en / maxEn < EN_WARNING_THRESHOLD) {
        warnings.push('energy');
    }

    // 弾切れ: 第1武器の弾薬が0
    const firstWeapon = initialMs.weapons[0];
    if (firstWeapon && firstWeapon.max_ammo !== null && firstWeapon.max_ammo !== undefined) {
        if (entry.ammo[firstWeapon.id] === 0) {
            warnings.push('ammo');
        }
    }

    // クールダウン判定（簡易版：最後の攻撃から一定時間以内）
    // 注: より正確な実装には武器ごとのクールダウン追跡が必要
    // cool_down_turn を秒換算（1ターン = 0.1s）
    const cooldownSeconds = (firstWeapon?.cool_down_turn || 0) * 0.1;
    if (cooldownSeconds > 0 && currentTimestamp - entry.lastAttackTimestamp < cooldownSeconds) {
        warnings.push('cooldown');
    }

    if (cache) cache.set(cacheKey, entry);

    return {
        pos,
        hp: Math.max(0, entry.hp),
        en: entry.en,
        ammo: { ...entry.ammo },
        warnings,
        heading,
        targetId: entry.unitTargetId,
    };
}

/**
 * 指定タイムスタンプ時点でプレイヤーが索敵済みの敵MSのIDセットを返す。
 * バトルログから action_type === "DETECTION" かつ actor_id === playerId のエントリを収集する。
 * 索敵は永続的（一度発見したMSは以降も表示し続ける）。
 */
export function getDetectedUnits(
    playerId: string,
    logs: BattleLog[],
    currentTimestamp: number
): Set<string> {
    const detected = new Set<string>();
    for (const log of logs) {
        if (log.timestamp > currentTimestamp + TIMESTAMP_EPSILON) break;
        if (log.action_type === "DETECTION" && log.actor_id === playerId && log.target_id) {
            detected.add(log.target_id);
        }
    }
    return detected;
}
