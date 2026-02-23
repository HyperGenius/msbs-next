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

/** チームの使い方ステップ定義 */
const HOW_TO_STEPS = [
  { step: 1, label: "チームを作成", desc: "チーム名を入力して小隊を結成する" },
  { step: 2, label: "フレンドを招待", desc: "フレンド一覧から最大2名を招待する" },
  { step: 3, label: "READY を切替", desc: "全メンバーが準備完了すると READY 状態になる" },
  { step: 4, label: "チームエントリー", desc: "リーダーが機体を選択してバトルに登録する" },
];

/** ヒント表示コンポーネント */
function Hint({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-2 text-xs text-[#00f0ff]/60 flex items-start gap-1">
      <span className="text-[#00f0ff] shrink-0">ℹ</span>
      {children}
    </p>
  );
}

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

  const handleInvite = async (targetUserId: string) => {
    if (!team) return;
    clearMessages();
    setIsProcessing(true);
    try {
      await inviteTeamMember(team.id, targetUserId);
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

  const isOwner = team?.owner_user_id === userId;
  const teamFull = (team?.members.length ?? 0) >= 3;
  const allReady = team?.status === "READY";
  const hasMobileSuits = (mobileSuits?.length ?? 0) > 0;

  /** チームエントリーが押せない理由を返す（複数の場合は最優先の1件） */
  const entryBlockReason = (): string | null => {
    if (!isOwner) return "チームエントリーはリーダーのみ実行できます";
    if (!allReady) return "全メンバーが READY 状態になるまでエントリーできません";
    if (!hasMobileSuits) return "機体がありません。ガレージで機体を入手してください";
    if (!selectedMsId) return "使用する機体を選択してください";
    return null;
  };

  const entryHint = entryBlockReason();

  /** 招待ができない理由を返す */
  const inviteBlockReason = (): string | null => {
    if (!isOwner) return "メンバー招待はリーダーのみ実行できます";
    if (teamFull) return "チームが満員（3名）です。メンバーが離脱するまで招待できません";
    if (!friends || friends.length === 0) return "フレンドがいません。ランキング等からフレンド申請を送りましょう";
    if (!invitableFriends || invitableFriends.length === 0) return "招待できるフレンドがいません（すでにチームに参加済み、または招待条件を満たしていません）";
    return null;
  };

  const inviteHint = inviteBlockReason();

  return (
    <main className="min-h-screen bg-[#050505] text-[#00ff41] p-4 sm:p-6 md:p-8 font-mono">
      <div className="max-w-3xl mx-auto">
        <Header />

        <SciFiHeading level={1} className="mb-6 text-2xl">
          SQUAD FORMATION — Team Console
        </SciFiHeading>

        {/* ─── 使い方ガイド ─── */}
        <SciFiPanel variant="accent" className="mb-6">
          <div className="p-4">
            <p className="text-xs text-[#00f0ff]/50 uppercase tracking-widest mb-3">
              How to use — 使い方
            </p>
            <ol className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {HOW_TO_STEPS.map(({ step, label, desc }) => {
                // 現在の進行状態でどのステップがアクティブかを判定
                const active =
                  (!team && step === 1) ||
                  (team && !teamFull && step === 2) ||
                  (team && teamFull && !allReady && step === 3) ||
                  (team && allReady && step === 4);
                return (
                  <li
                    key={step}
                    className={`p-3 border text-center transition-all ${
                      active
                        ? "border-[#00f0ff] bg-[#00f0ff]/10 text-[#00f0ff]"
                        : "border-[#00f0ff]/20 text-[#00f0ff]/40"
                    }`}
                  >
                    <div className={`text-lg font-bold mb-1 ${active ? "text-[#00f0ff]" : "text-[#00f0ff]/30"}`}>
                      {step}
                    </div>
                    <div className="text-xs font-bold mb-1">{label}</div>
                    <div className="text-[10px] leading-tight">{desc}</div>
                  </li>
                );
              })}
            </ol>
          </div>
        </SciFiPanel>

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

            {/* ─── チーム未所属：作成フォーム ─── */}
            {!team && (
              <SciFiPanel variant="accent">
                <div className="p-6">
                  <SciFiHeading level={2} variant="accent" className="mb-2 text-lg">
                    新規チーム作成
                  </SciFiHeading>
                  <p className="text-sm text-[#00f0ff]/60 mb-4">
                    チームに所属していません。チーム名を入力して小隊を結成しましょう。
                  </p>
                  <div className="flex gap-3">
                    <div className="flex-1">
                      <SciFiInput
                        value={teamName}
                        onChange={(e) => setTeamName(e.target.value)}
                        placeholder="チーム名を入力（例: Team Alpha）"
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
                  {!teamName.trim() && (
                    <Hint>チーム名を入力すると「作成」ボタンが有効になります</Hint>
                  )}
                </div>
              </SciFiPanel>
            )}

            {/* ─── チーム情報 ─── */}
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
                            allReady
                              ? "border-[#00ff41] text-[#00ff41] bg-[#00ff41]/10"
                              : "border-[#ffb000] text-[#ffb000] bg-[#ffb000]/10"
                          }`}
                        >
                          {allReady ? "★ ALL READY" : "FORMING..."}
                        </span>
                      </div>
                      <SciFiButton
                        onClick={handleLeave}
                        disabled={isProcessing}
                        variant="secondary"
                        size="sm"
                      >
                        {isOwner ? "解散" : "離脱"}
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

                    {/* Ready 切替ボタン */}
                    <div className="mt-6 flex flex-wrap gap-3 items-start">
                      <div>
                        <SciFiButton
                          onClick={handleToggleReady}
                          disabled={isProcessing}
                          variant="primary"
                        >
                          READY 切替
                        </SciFiButton>
                        {!allReady && (
                          <Hint>
                            全メンバーが READY になるとチームステータスが{" "}
                            <span className="text-[#00ff41]">ALL READY</span> に変わります
                          </Hint>
                        )}
                      </div>
                    </div>
                  </div>
                </SciFiPanel>

                {/* ─── チームエントリーパネル（常に表示・無効時はヒント付き） ─── */}
                <SciFiPanel variant="secondary">
                  <div className="p-6">
                    <SciFiHeading level={2} variant="secondary" className="mb-2 text-lg">
                      チームエントリー
                    </SciFiHeading>
                    <p className="text-sm text-[#ffb000]/60 mb-4">
                      全メンバーの準備が完了したら、リーダーが機体を選択してバトルに登録します。
                    </p>

                    {entryHint ? (
                      // エントリー不可のとき：無効化した選択欄 ＋ ヒント
                      <div>
                        <div className="flex gap-3 flex-wrap opacity-40 cursor-not-allowed pointer-events-none">
                          <select
                            disabled
                            aria-disabled="true"
                            className="flex-1 bg-[#0a0a0a] border-2 border-[#ffb000]/50 text-[#ffb000] px-4 py-2 font-mono text-sm"
                          >
                            <option>-- 機体を選択 --</option>
                          </select>
                          <SciFiButton disabled aria-disabled="true" variant="secondary">
                            エントリー
                          </SciFiButton>
                        </div>
                        <Hint>{entryHint}</Hint>
                      </div>
                    ) : (
                      // エントリー可能のとき
                      <div>
                        <div className="flex gap-3 flex-wrap">
                          <select
                            value={selectedMsId}
                            onChange={(e) => setSelectedMsId(e.target.value)}
                            className="flex-1 bg-[#0a0a0a] border-2 border-[#ffb000]/50 text-[#ffb000] px-4 py-2 font-mono text-sm focus:border-[#ffb000] focus:outline-none"
                          >
                            <option value="">-- 機体を選択 --</option>
                            {mobileSuits?.map((ms) => (
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
                        {!selectedMsId && (
                          <Hint>使用する機体を選択するとエントリーできます</Hint>
                        )}
                      </div>
                    )}
                  </div>
                </SciFiPanel>

                {/* ─── フレンドを招待パネル（常に表示・無効時はヒント付き） ─── */}
                <SciFiPanel variant="accent">
                  <div className="p-6">
                    <SciFiHeading level={2} variant="accent" className="mb-2 text-lg">
                      フレンドを招待
                    </SciFiHeading>
                    <p className="text-sm text-[#00f0ff]/60 mb-4">
                      フレンドをチームに招待できます（最大 3 名まで）。
                    </p>

                    {inviteHint ? (
                      // 招待不可のとき：無効化したボタン ＋ ヒント
                      <div>
                        <div className="opacity-40 cursor-not-allowed pointer-events-none">
                          <div className="p-3 border border-[#00f0ff]/20 bg-[#0a0a0a]/40 flex justify-between items-center">
                            <span className="text-sm text-[#00f0ff]/60">（招待できるフレンドがいません）</span>
                            <SciFiButton disabled aria-disabled="true" variant="accent" size="sm">
                              招待
                            </SciFiButton>
                          </div>
                        </div>
                        <Hint>{inviteHint}</Hint>
                      </div>
                    ) : (
                      // 招待可能のとき
                      <div className="space-y-2">
                        {invitableFriends?.map((friend) => (
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
                    )}
                  </div>
                </SciFiPanel>
              </>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
