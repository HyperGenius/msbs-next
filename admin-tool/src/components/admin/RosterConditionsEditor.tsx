"use client";

import { useAdminEnvironments } from "@/hooks/useAdminEnvironments";
import { OBSTACLE_DENSITIES } from "@/lib/theater";
import type { LocalSimRoster } from "@/types/localSim";
import { NumberField, SelectField } from "@/components/admin/RosterFields";

type Conditions = LocalSimRoster["conditions"];

interface RosterConditionsEditorProps {
  conditions: Conditions;
  original: Conditions;
  onChange: (conditions: Conditions) => void;
}

/** 戦域の条件（環境・ミノフスキー濃度・障害物の密度）の編集欄 */
export default function RosterConditionsEditor({ conditions, original, onChange }: RosterConditionsEditorProps) {
  const { environments } = useAdminEnvironments();
  const density = conditions.battlefield.obstacle_density ?? "";
  const originalDensity = original.battlefield.obstacle_density ?? "";

  // 環境が候補に無いとき（マスターの取得前や削除後）も、いま入っている値を選べるようにする。
  const environmentOptions = [
    ...(environments ?? []).map((e) => ({ value: e.id, label: `${e.name} (${e.id})` })),
  ];
  if (!environmentOptions.some((o) => o.value === conditions.environment)) {
    environmentOptions.unshift({ value: conditions.environment, label: conditions.environment });
  }

  function changeEnvironment(id: string) {
    const master = environments?.find((e) => e.id === id);
    if (!master) return;
    // 環境タイプの効果は、ロスターに写しとして持つ。環境を変えたら写しも取り替える。
    onChange({
      ...conditions,
      environment: id,
      environment_name: master.name,
      viewer_preset: master.viewer_preset,
      environment_profile: {
        environment_id: master.id,
        sensor_range_multiplier: master.sensor_range_multiplier,
        ranged_accuracy_penalty: master.ranged_accuracy_penalty,
        ranged_penalty_ref_distance: master.ranged_penalty_ref_distance,
        default_obstacle_density: master.default_obstacle_density,
        default_terrain_grade: master.default_terrain_grade,
      },
    });
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
      <SelectField
        label="環境"
        value={conditions.environment}
        original={original.environment}
        options={environmentOptions}
        onChange={changeEnvironment}
      />
      <NumberField
        label="ミノフスキー濃度 (0-1)"
        step="0.05"
        value={conditions.minovsky_density}
        original={original.minovsky_density}
        onChange={(value) => onChange({ ...conditions, minovsky_density: value })}
      />
      <SelectField
        label="障害物の密度"
        value={density}
        original={originalDensity}
        options={[
          ...(density === "" ? [{ value: "", label: "（未指定）" }] : []),
          ...OBSTACLE_DENSITIES.map((d) => ({ value: d, label: d })),
        ]}
        onChange={(value) => onChange({ ...conditions, battlefield: { ...conditions.battlefield, obstacle_density: value } })}
      />
    </div>
  );
}
