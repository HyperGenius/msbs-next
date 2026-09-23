import { useMemo } from "react";
import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { buildEffectScenario, EffectScenarioOptions, WEAPONS } from "./__stories__/battleLogFixtures";
import { EffectReplayStage } from "./__stories__/EffectReplayStage";

interface EffectStoryArgs extends EffectScenarioOptions {
    environment: string;
    replayIntervalMs: number;
}

/** 演出 1 件を 1 対 1 で繰り返し再生する。ログは backend と同じ形で組み立てる。 */
function EffectStory({
    environment,
    replayIntervalMs,
    effect,
    attacker,
    weapon,
    distance,
    damage,
    comboCount,
}: EffectStoryArgs) {
    // logs の参照が変わると再生ラッパーが即時リプレイするため、引数が変わった時だけ作り直す
    const scenario = useMemo(
        () => buildEffectScenario({ effect, attacker, weapon, distance, damage, comboCount }),
        [effect, attacker, weapon, distance, damage, comboCount],
    );
    return (
        <EffectReplayStage
            scenario={scenario}
            environment={environment}
            replayIntervalMs={replayIntervalMs}
        />
    );
}

const meta: Meta<EffectStoryArgs> = {
    title: "BattleViewer/Effects",
    component: EffectStory,
    // Canvas を並べると WebGL コンテキスト数の上限を超えるため、Docs ページを作らない
    tags: ["!autodocs"],
    parameters: {
        layout: "fullscreen",
        backgrounds: { default: "dark" },
    },
    args: {
        effect: "HIT",
        attacker: "PLAYER",
        weapon: "BEAM_RIFLE",
        distance: 400,
        damage: 150,
        comboCount: 2,
        environment: "SPACE",
        replayIntervalMs: 2500,
    },
    argTypes: {
        effect: { control: "select", options: ["HIT", "CRITICAL", "MISS", "MELEE_COMBO"] },
        attacker: { control: "inline-radio", options: ["PLAYER", "ENEMY"] },
        weapon: { control: "select", options: Object.keys(WEAPONS) },
        distance: { control: { type: "range", min: 50, max: 1500, step: 50 } },
        damage: { control: { type: "range", min: 10, max: 1000, step: 10 } },
        comboCount: {
            control: { type: "range", min: 1, max: 5, step: 1 },
            if: { arg: "effect", eq: "MELEE_COMBO" },
        },
        environment: { control: "select", options: ["SPACE", "GROUND", "COLONY", "UNDERWATER"] },
        replayIntervalMs: { control: { type: "range", min: 0, max: 6000, step: 500 } },
    },
};

export default meta;
type Story = StoryObj<EffectStoryArgs>;

export const Hit: Story = {};

export const Critical: Story = {
    args: { effect: "CRITICAL", damage: 350 },
};

export const Miss: Story = {
    args: { effect: "MISS" },
};

export const MeleeCombo: Story = {
    args: { effect: "MELEE_COMBO", weapon: "BEAM_SABER", distance: 50, comboCount: 3 },
};

/** 実弾武器の飛翔体。武器名に「ビーム」を含まない武器は実弾として描画される。 */
export const BulletProjectile: Story = {
    args: { weapon: "MACHINE_GUN", damage: 40 },
};

export const EnemyAttack: Story = {
    args: { attacker: "ENEMY", weapon: "MACHINE_GUN", damage: 60 },
};

export const Underwater: Story = {
    args: { environment: "UNDERWATER" },
};
