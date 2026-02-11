"use client";

import { usePlayerProfile } from "@/services/api";
import { Tactics } from "@/types/battle";

interface PlayerProfileModalProps {
  userId: string;
  onClose: () => void;
}

export default function PlayerProfileModal({
  userId,
  onClose,
}: PlayerProfileModalProps) {
  const { profile, isLoading, isError } = usePlayerProfile(userId);

  const getTacticsLabel = (tactics: Tactics) => {
    const priority = {
      CLOSEST: "最接近",
      WEAKEST: "弱体優先",
      RANDOM: "ランダム",
      STRONGEST: "強敵優先",
      THREAT: "脅威度優先",
    }[tactics.priority] || tactics.priority;

    const range = {
      MELEE: "近接戦",
      RANGED: "遠距離",
      BALANCED: "バランス",
      FLEE: "回避重視",
    }[tactics.range] || tactics.range;

    return `${priority} / ${range}`;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-gray-900 border-4 border-green-800 rounded-lg p-8">
          {/* Header */}
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-3xl font-bold text-green-400 mb-2">
                Pilot Profile
              </h2>
              {profile && (
                <p className="text-gray-400">Viewing: {profile.pilot_name}</p>
              )}
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-red-900 hover:bg-red-800 rounded font-bold transition-colors"
            >
              ✕ Close
            </button>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="text-center py-12">
              <p className="text-xl text-gray-400">Loading profile...</p>
            </div>
          )}

          {/* Error State */}
          {isError && (
            <div className="bg-red-900/30 border border-red-500 p-4 rounded">
              <p className="text-red-400">Failed to load pilot profile.</p>
            </div>
          )}

          {/* Profile Content */}
          {profile && (
            <div className="space-y-6">
              {/* Pilot Stats */}
              <div className="bg-gray-800 border border-green-800 rounded-lg p-6">
                <h3 className="text-xl font-bold text-green-400 mb-4">
                  Pilot Statistics
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-gray-500 text-sm">Level</p>
                    <p className="text-2xl font-bold text-green-400">
                      {profile.level}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-500 text-sm">Wins</p>
                    <p className="text-2xl font-bold text-green-400">
                      {profile.wins}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-500 text-sm">Losses</p>
                    <p className="text-2xl font-bold text-red-400">
                      {profile.losses}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-500 text-sm">Total Kills</p>
                    <p className="text-2xl font-bold text-yellow-400">
                      {profile.kills}
                    </p>
                  </div>
                </div>

                {/* Win Rate */}
                {profile.wins + profile.losses > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-700">
                    <p className="text-gray-500 text-sm">Win Rate</p>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-700 rounded-full h-4 overflow-hidden">
                        <div
                          className="bg-green-500 h-full"
                          style={{
                            width: `${
                              (profile.wins / (profile.wins + profile.losses)) *
                              100
                            }%`,
                          }}
                        />
                      </div>
                      <span className="text-green-400 font-bold">
                        {(
                          (profile.wins / (profile.wins + profile.losses)) *
                          100
                        ).toFixed(1)}
                        %
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Mobile Suit */}
              {profile.mobile_suit && (
                <div className="bg-gray-800 border border-green-800 rounded-lg p-6">
                  <h3 className="text-xl font-bold text-green-400 mb-4">
                    Mobile Suit: {profile.mobile_suit.name}
                  </h3>

                  {/* Stats Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div>
                      <p className="text-gray-500 text-sm">HP</p>
                      <p className="text-lg font-bold">
                        {profile.mobile_suit.max_hp}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500 text-sm">Armor</p>
                      <p className="text-lg font-bold">
                        {profile.mobile_suit.armor}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500 text-sm">Mobility</p>
                      <p className="text-lg font-bold">
                        {profile.mobile_suit.mobility.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500 text-sm">Sensor Range</p>
                      <p className="text-lg font-bold">
                        {profile.mobile_suit.sensor_range || 500}
                      </p>
                    </div>
                  </div>

                  {/* Weapons */}
                  <div className="mt-4 pt-4 border-t border-gray-700">
                    <h4 className="text-lg font-bold text-green-400 mb-3">
                      Weapons
                    </h4>
                    <div className="space-y-2">
                      {profile.mobile_suit.weapons.map((weapon, index) => (
                        <div
                          key={index}
                          className="bg-gray-900 border border-gray-700 rounded p-3"
                        >
                          <div className="flex justify-between items-start mb-2">
                            <span className="font-bold text-green-400">
                              {weapon.name}
                            </span>
                            <span
                              className={`px-2 py-1 rounded text-xs ${
                                weapon.type === "BEAM"
                                  ? "bg-blue-900 text-blue-300"
                                  : "bg-orange-900 text-orange-300"
                              }`}
                            >
                              {weapon.type || "PHYSICAL"}
                            </span>
                          </div>
                          <div className="grid grid-cols-3 gap-2 text-sm text-gray-400">
                            <div>
                              <span className="text-gray-500">Power:</span>{" "}
                              {weapon.power}
                            </div>
                            <div>
                              <span className="text-gray-500">Range:</span>{" "}
                              {weapon.range}
                            </div>
                            <div>
                              <span className="text-gray-500">Accuracy:</span>{" "}
                              {weapon.accuracy}%
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Tactics */}
                  <div className="mt-4 pt-4 border-t border-gray-700">
                    <h4 className="text-lg font-bold text-green-400 mb-2">
                      Tactics
                    </h4>
                    <p className="text-gray-300">
                      {getTacticsLabel(profile.mobile_suit.tactics)}
                    </p>
                  </div>
                </div>
              )}

              {/* Skills */}
              {Object.keys(profile.skills).length > 0 && (
                <div className="bg-gray-800 border border-green-800 rounded-lg p-6">
                  <h3 className="text-xl font-bold text-green-400 mb-4">
                    Skills
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {Object.entries(profile.skills).map(([skillId, level]) => (
                      <div
                        key={skillId}
                        className="bg-gray-900 border border-gray-700 rounded p-3"
                      >
                        <p className="font-bold text-green-400">{skillId}</p>
                        <p className="text-sm text-gray-400">Level {level}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* No Mobile Suit Warning */}
              {!profile.mobile_suit && (
                <div className="bg-yellow-900/30 border border-yellow-700 p-4 rounded">
                  <p className="text-yellow-400">
                    This pilot has not configured a mobile suit yet.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
