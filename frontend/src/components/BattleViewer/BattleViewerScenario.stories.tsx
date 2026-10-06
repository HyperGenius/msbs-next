import { useMemo, useState } from "react";
import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import BattleViewer from ".";
import ChapterTrack from "./ui/ChapterTrack";
import { useBattleChapters } from "./hooks/useBattleChapters";
import TurnController from "@/components/history/TurnController";
import { Obstacle } from "@/types/battle";
import {
    BattleScenario,
    buildEnShortageScenario,
    buildMeleeClashScenario,
    buildSkirmishObstacles,
    buildSkirmishScenario,
} from "./__stories__/battleScenarioFixtures";

interface ScenarioStoryArgs {
    environment: string;
    theaterName?: string | null;
    minovskyDensity?: number | null;
    buildScenario: () => BattleScenario;
    buildObstacles?: () => Obstacle[];
}

/** BattleDetailModal と同じ部品構成で、複数の演出を含むバトルを通し再生する。 */
function ScenarioStory({ environment, theaterName, minovskyDensity, buildScenario, buildObstacles }: ScenarioStoryArgs) {
    const { logs, player, enemies } = useMemo(() => buildScenario(), [buildScenario]);
    const obstacles = useMemo(() => buildObstacles?.(), [buildObstacles]);
    const [currentTimestamp, setCurrentTimestamp] = useState(0);
    const [recenterToken, setRecenterToken] = useState(0);
    const chapters = useBattleChapters(logs, player, enemies);
    const maxTimestamp = logs[logs.length - 1].timestamp;

    const handleChapterSeek = (timestamp: number) => {
        setCurrentTimestamp(timestamp);
        setRecenterToken((t) => t + 1);
    };

    return (
        <div className="p-4 max-w-3xl mx-auto">
            <BattleViewer
                logs={logs}
                player={player}
                enemies={enemies}
                obstacles={obstacles}
                currentTimestamp={currentTimestamp}
                environment={environment}
                theaterName={theaterName}
                minovskyDensity={minovskyDensity}
                recenterToken={recenterToken}
            />
            <ChapterTrack chapters={chapters} currentTimestamp={currentTimestamp} onSeek={handleChapterSeek} />
            <TurnController
                currentTimestamp={currentTimestamp}
                maxTimestamp={maxTimestamp}
                onTimestampChange={setCurrentTimestamp}
            />
        </div>
    );
}

const meta: Meta<ScenarioStoryArgs> = {
    title: "BattleViewer/Scenario",
    component: ScenarioStory,
    // Canvas を並べると WebGL コンテキスト数の上限を超えるため、Docs ページを作らない
    tags: ["!autodocs"],
    parameters: {
        layout: "fullscreen",
        backgrounds: { default: "dark" },
    },
    args: { environment: "SPACE", buildScenario: buildSkirmishScenario },
    argTypes: {
        environment: { control: "select", options: ["SPACE", "GROUND", "COLONY", "UNDERWATER", "FOREST"] },
        minovskyDensity: { control: { type: "range", min: 0, max: 1, step: 0.05 } },
        buildScenario: { table: { disable: true } },
        buildObstacles: { table: { disable: true } },
    },
};

export default meta;
type Story = StoryObj<ScenarioStoryArgs>;

export const Skirmish: Story = {};

/** ENゲージの追従・20%未満での赤色表示・EN不足イベントでの2回点滅（Issue #534） */
export const EnShortage: Story = {
    args: { buildScenario: buildEnShortageScenario },
};

/** 正面からの斬り合いで鍔迫り合いになり、押し離された後に射撃へ切り替える。チャプターにも出る。 */
export const MeleeClash: Story = {
    args: { buildScenario: buildMeleeClashScenario },
};

/** 森林の戦域。障害物は木立として描く。LOS を ON にすると遮断中の木立が赤くなる。 */
export const Forest: Story = {
    args: {
        environment: "FOREST",
        theaterName: "東南アジア密林",
        minovskyDensity: 0.3,
        buildObstacles: buildSkirmishObstacles,
    },
};

/** ミノフスキー濃度が高い戦域。画面全体に粒子のもやがかかる。 */
export const HighMinovskyDensity: Story = {
    args: {
        environment: "FOREST",
        theaterName: "東南アジア密林",
        minovskyDensity: 0.9,
        buildObstacles: buildSkirmishObstacles,
    },
};

/** 濃度 0 ではもやを出さない。宇宙の障害物は従来どおり円柱で描く。 */
export const SpaceWithoutMinovsky: Story = {
    args: {
        environment: "SPACE",
        theaterName: "ソロモン宙域",
        minovskyDensity: 0,
        buildObstacles: buildSkirmishObstacles,
    },
};

/** 未知の描画プリセットは SPACE の描画にフォールバックする。 */
export const UnknownViewerPreset: Story = {
    args: {
        environment: "VOLCANO",
        theaterName: "未知の戦域",
        minovskyDensity: 0.5,
        buildObstacles: buildSkirmishObstacles,
    },
};
