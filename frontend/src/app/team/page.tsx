/* frontend/src/app/team/page.tsx */
"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Header from "@/components/Header";
import {
  useTeamStatus,
  useFriends,
  useMobileSuits,
  createTeam,
  inviteTeamMember,
  toggleTeamReady,
  leaveTeam,
  teamEntry,
} from "@/services/api";
import { SciFiPanel, SciFiHeading, SciFiButton, SciFiInput } from "@/components/ui";

export default function TeamPage() {
  const { isSignedIn, userId } = useAuth();
  const { team, isLoading, mutate: mutateTeam } = useTeamStatus();
  const { friends } = useFriends();
  const { mobileSuits } = useMobileSuits();

  const [teamName, setTeamName] = useState("");
  const [selectedMsId, setSelectedMsId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  const clearMessages = () => {
    setMessage("");
    setError("");
  };

  const handleCreateTeam = async () => {
    if (!teamName.trim()) return;
    clearMessages();
    setIsProcessing(true);
    try {
      await createTeam(teamName.trim());
      mutateTeam();
      setTeamName("");
      setMessage("チームを作成しました");
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleInvite = async (userId: string) => {
    if (!team) return;
    clearMessages();
    setIsProcessing(true);
    try {
      await inviteTeamMember(team.id, userId);
      mutateTeam();
      setMessage("メンバーを招待しました");
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleToggleReady = async () => {
    if (!team) return;
    clearMessages();
    setIsProcessing(true);
    try {
      await toggleTeamReady(team.id);
      mutateTeam();
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleLeave = async () => {
    if (!team) return;
    clearMessages();
    setIsProcessing(true);
    try {
      await leaveTeam(team.id);
      mutateTeam();
      setMessage("チームを離脱しました");
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleTeamEntry = async () => {
    if (!team || !selectedMsId) return;
    clearMessages();
    setIsProcessing(true);
    try {
      const result = await teamEntry({ team_id: team.id, mobile_suit_id: selectedMsId });
      mutateTeam();
      setMessage(result.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    } finally {
      setIsProcessing(false);
    }
  };

  // フレンドのうちまだチームに招待していないメンバーのリスト
  const invitableFriends = friends?.filter(
    (f) =>
      !team?.members.some(
        (m) => m.user_id === f.friend_user_id || m.user_id === f.user_id
      )
  );

  return (
    <main className="min-h-screen bg-[#050505] text-[#00ff41] p-4 sm:p-6 md:p-8 font-mono">
      <div className="max-w-3xl mx-auto">
        <Header />

        <SciFiHeading level={1} className="mb-6 text-2xl">
          SQUAD FORMATION — Team Console
        </SciFiHeading>

        {!isSignedIn ? (
          <SciFiPanel variant="secondary">
            <div className="p-6 text-center text-[#ffb000]">
              チーム機能を利用するにはログインが必要です
            </div>
          </SciFiPanel>
        ) : isLoading ? (
          <SciFiPanel>
            <div className="p-6 text-center text-[#00ff41]/60">
              データを読み込み中...
            </div>
          </SciFiPanel>
        ) : (
          <div className="space-y-6">
            {/* メッセージ表示 */}
            {error && (
              <SciFiPanel variant="secondary">
                <div className="p-4 text-[#ff4444]">{error}</div>
              </SciFiPanel>
            )}
            {message && (
              <SciFiPanel>
                <div className="p-4 text-[#00ff41]">{message}</div>
              </SciFiPanel>
            )}

            {/* チーム未所属：作成フォーム */}
            {!team && (
              <SciFiPanel variant="accent">
                <div className="p-6">
                  <SciFiHeading level={2} variant="accent" className="mb-4 text-lg">
                    新規チーム作成
                  </SciFiHeading>
                  <p className="text-sm text-[#00f0ff]/60 mb-4">
                    チームに所属していません。新しいチームを作成しましょう。
                  </p>
                  <div className="flex gap-3">
                    <div className="flex-1">
                      <SciFiInput
                        value={teamName}
                        onChange={(e) => setTeamName(e.target.value)}
                        placeholder="チーム名を入力"
                        onKeyDown={(e) => e.key === "Enter" && handleCreateTeam()}
                        variant="accent"
                      />
                    </div>
                    <SciFiButton
                      onClick={handleCreateTeam}
                      disabled={!teamName.trim() || isProcessing}
                      variant="accent"
                    >
                      作成
                    </SciFiButton>
                  </div>
                </div>
              </SciFiPanel>
            )}

            {/* チーム情報 */}
            {team && (
              <>
                {/* チームステータスパネル */}
                <SciFiPanel variant="primary" chiseled>
                  <div className="p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <SciFiHeading level={2} className="text-xl">
                          {team.name}
                        </SciFiHeading>
                        <span
                          className={`text-xs px-2 py-1 border font-mono mt-1 inline-block ${
                            team.status === "READY"
                              ? "border-[#00ff41] text-[#00ff41] bg-[#00ff41]/10"
                              : "border-[#ffb000] text-[#ffb000] bg-[#ffb000]/10"
                          }`}
                        >
                          {team.status === "READY" ? "★ ALL READY" : "FORMING..."}
                        </span>
                      </div>
                      <SciFiButton
                        onClick={handleLeave}
                        disabled={isProcessing}
                        variant="secondary"
                        size="sm"
                      >
                        {team.owner_user_id === userId
                          ? "解散"
                          : "離脱"}
                      </SciFiButton>
                    </div>

                    {/* メンバー一覧 */}
                    <div className="mt-4">
                      <p className="text-xs text-[#00ff41]/50 uppercase tracking-widest mb-3">
                        Squad Members ({team.members.length} / 3)
                      </p>
                      <div className="space-y-2">
                        {team.members.map((member) => (
                          <div
                            key={member.user_id}
                            className="flex justify-between items-center p-3 border border-[#00ff41]/20 bg-[#0a0a0a]/60"
                          >
                            <div className="flex items-center gap-3">
                              <span
                                className={`w-2 h-2 rounded-full ${
                                  member.is_ready
                                    ? "bg-[#00ff41] shadow-[0_0_6px_#00ff41]"
                                    : "bg-[#333]"
                                }`}
                              />
                              <span className="text-sm text-[#00ff41]/80">
                                {member.user_id === team.owner_user_id && (
                                  <span className="text-[#ffb000] mr-1">▶</span>
                                )}
                                {member.user_id}
                              </span>
                            </div>
                            <span
                              className={`text-xs font-mono ${
                                member.is_ready
                                  ? "text-[#00ff41]"
                                  : "text-[#00ff41]/30"
                              }`}
                            >
                              {member.is_ready ? "READY" : "STANDBY"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* アクションボタン */}
                    <div className="mt-6 flex flex-wrap gap-3">
                      <SciFiButton
                        onClick={handleToggleReady}
                        disabled={isProcessing}
                        variant="primary"
                      >
                        READY 切替
                      </SciFiButton>
                    </div>
                  </div>
                </SciFiPanel>

                {/* チームエントリーパネル */}
                {team.status === "READY" && mobileSuits && mobileSuits.length > 0 && (
                  <SciFiPanel variant="secondary">
                    <div className="p-6">
                      <SciFiHeading level={2} variant="secondary" className="mb-4 text-lg">
                        チームエントリー
                      </SciFiHeading>
                      <p className="text-sm text-[#ffb000]/60 mb-4">
                        全メンバーの準備が完了しました。使用機体を選択してエントリーしてください。
                      </p>
                      <div className="flex gap-3 flex-wrap">
                        <select
                          value={selectedMsId}
                          onChange={(e) => setSelectedMsId(e.target.value)}
                          className="flex-1 bg-[#0a0a0a] border-2 border-[#ffb000]/50 text-[#ffb000] px-4 py-2 font-mono text-sm focus:border-[#ffb000] focus:outline-none"
                        >
                          <option value="">-- 機体を選択 --</option>
                          {mobileSuits.map((ms) => (
                            <option key={ms.id} value={ms.id}>
                              {ms.name}
                            </option>
                          ))}
                        </select>
                        <SciFiButton
                          onClick={handleTeamEntry}
                          disabled={!selectedMsId || isProcessing}
                          variant="secondary"
                        >
                          エントリー
                        </SciFiButton>
                      </div>
                    </div>
                  </SciFiPanel>
                )}

                {/* フレンドを招待パネル */}
                {invitableFriends && invitableFriends.length > 0 && team.members.length < 3 && (
                  <SciFiPanel variant="accent">
                    <div className="p-6">
                      <SciFiHeading level={2} variant="accent" className="mb-4 text-lg">
                        フレンドを招待
                      </SciFiHeading>
                      <div className="space-y-2">
                        {invitableFriends.map((friend) => (
                          <div
                            key={friend.id}
                            className="flex justify-between items-center p-3 border border-[#00f0ff]/20 bg-[#0a0a0a]/60"
                          >
                            <span className="text-sm text-[#00f0ff]/80">
                              {friend.pilot_name || friend.friend_user_id}
                            </span>
                            <SciFiButton
                              onClick={() => handleInvite(friend.friend_user_id)}
                              disabled={isProcessing}
                              variant="accent"
                              size="sm"
                            >
                              招待
                            </SciFiButton>
                          </div>
                        ))}
                      </div>
                    </div>
                  </SciFiPanel>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
