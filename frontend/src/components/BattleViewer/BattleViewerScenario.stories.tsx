import { useMemo, useState } from "react";
import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import BattleViewer from ".";
import ChapterTrack from "./ui/ChapterTrack";
import { useBattleChapters } from "./hooks/useBattleChapters";
import TurnController from "@/components/history/TurnController";
import { BattleScenario, buildEnShortageScenario, buildSkirmishScenario } from "./__stories__/battleScenarioFixtures";

interface ScenarioStoryArgs {
    environment: string;
    buildScenario: () => BattleScenario;
}

/** BattleDetailModal と同じ部品構成で、複数の演出を含むバトルを通し再生する。 */
function ScenarioStory({ environment, buildScenario }: ScenarioStoryArgs) {
    const { logs, player, enemies } = useMemo(() => buildScenario(), [buildScenario]);
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
                currentTimestamp={currentTimestamp}
                environment={environment}
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
        environment: { control: "select", options: ["SPACE", "GROUND", "COLONY", "UNDERWATER"] },
        buildScenario: { table: { disable: true } },
    },
};

export default meta;
type Story = StoryObj<ScenarioStoryArgs>;

export const Skirmish: Story = {};

/** ENゲージの追従・20%未満での赤色表示・EN不足イベントでの2回点滅（Issue #534） */
export const EnShortage: Story = {
    args: { buildScenario: buildEnShortageScenario },
};
