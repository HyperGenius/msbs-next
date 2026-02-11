/* frontend/src/app/rankings/page.tsx */
"use client";

import { useState } from "react";
import { useRankings } from "@/services/api";
import { useUser } from "@clerk/nextjs";
import Header from "@/components/Header";
import Link from "next/link";
import PlayerProfileModal from "@/components/Social/PlayerProfileModal";

export default function RankingsPage() {
  const { rankings, isLoading, isError } = useRankings(100);
  const { user } = useUser();
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  return (
    <main className="min-h-screen bg-gray-900 text-green-400 p-8 font-mono">
      <div className="max-w-6xl mx-auto">
        <Header />

        <div className="mb-6 flex justify-between items-center">
          <h1 className="text-3xl font-bold border-l-4 border-green-500 pl-2">
            Pilot Rankings
          </h1>
          <Link
            href="/"
            className="px-4 py-2 bg-green-900 hover:bg-green-800 rounded font-bold transition-colors"
          >
            ← Back to Dashboard
          </Link>
        </div>

        {isLoading && (
          <div className="text-center py-12">
            <p className="text-xl">Loading rankings...</p>
          </div>
        )}

        {isError && (
          <div className="bg-red-900/30 border border-red-500 p-4 rounded">
            <p className="text-red-400">
              Failed to load rankings. Check if backend is running.
            </p>
          </div>
        )}

        {rankings && rankings.length === 0 && !isLoading && (
          <div className="bg-gray-800 border border-gray-700 p-8 rounded text-center">
            <p className="text-xl text-gray-400">No ranking data available.</p>
            <p className="text-sm text-gray-500 mt-2">
              Complete battles to appear on the leaderboard.
            </p>
          </div>
        )}

        {rankings && rankings.length > 0 && (
          <div className="bg-gray-800 border border-green-800 rounded-lg overflow-hidden">
            {/* Table Header */}
            <div className="bg-green-900/30 px-6 py-4 grid grid-cols-6 gap-4 font-bold text-green-300 border-b border-green-800">
              <div className="text-center">Rank</div>
              <div className="col-span-2">Pilot Name</div>
              <div className="text-center">Wins</div>
              <div className="text-center">Kills</div>
              <div className="text-center">Credits</div>
            </div>

            {/* Table Body */}
            <div className="divide-y divide-gray-700">
              {rankings.map((entry) => {
                const isCurrentUser = user?.id === entry.user_id;
                return (
                  <button
                    key={entry.user_id}
                    onClick={() => setSelectedUserId(entry.user_id)}
                    className={`w-full px-6 py-4 grid grid-cols-6 gap-4 transition-colors text-left ${
                      isCurrentUser
                        ? "bg-green-900/20 hover:bg-green-900/30"
                        : "hover:bg-gray-700/50"
                    }`}
                  >
                    {/* Rank */}
                    <div className="text-center font-bold">
                      {entry.rank <= 3 ? (
                        <span
                          className={`inline-block px-3 py-1 rounded ${
                            entry.rank === 1
                              ? "bg-yellow-600 text-yellow-100"
                              : entry.rank === 2
                              ? "bg-gray-400 text-gray-900"
                              : "bg-orange-700 text-orange-100"
                          }`}
                        >
                          #{entry.rank}
                        </span>
                      ) : (
                        <span className="text-gray-400">#{entry.rank}</span>
                      )}
                    </div>

                    {/* Pilot Name */}
                    <div className="col-span-2 flex items-center">
                      <span
                        className={`${
                          isCurrentUser ? "text-green-300 font-bold" : ""
                        }`}
                      >
                        {entry.pilot_name}
                      </span>
                      {isCurrentUser && (
                        <span className="ml-2 px-2 py-0.5 bg-green-900 text-green-300 text-xs rounded">
                          YOU
                        </span>
                      )}
                    </div>

                    {/* Wins */}
                    <div className="text-center">
                      <span className="text-green-400 font-bold">
                        {entry.wins}
                      </span>
                      <span className="text-gray-500 text-sm ml-1">
                        / {entry.losses}
                      </span>
                    </div>

                    {/* Kills */}
                    <div className="text-center text-red-400">{entry.kills}</div>

                    {/* Credits */}
                    <div className="text-center text-yellow-400">
                      {entry.credits_earned.toLocaleString()}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Legend */}
        {rankings && rankings.length > 0 && (
          <div className="mt-6 p-4 bg-gray-800 border border-gray-700 rounded">
            <h3 className="text-sm font-bold mb-2 text-gray-400">Legend:</h3>
            <div className="grid grid-cols-3 gap-4 text-xs text-gray-500">
              <div>
                <span className="text-green-400">●</span> Wins / Losses
              </div>
              <div>
                <span className="text-red-400">●</span> Total Kills
              </div>
              <div>
                <span className="text-yellow-400">●</span> Credits Earned
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Click on a pilot name to view their profile and mobile suit
              configuration.
            </p>
          </div>
        )}
      </div>

      {/* Player Profile Modal */}
      {selectedUserId && (
        <PlayerProfileModal
          userId={selectedUserId}
          onClose={() => setSelectedUserId(null)}
        />
      )}
    </main>
  );
}
