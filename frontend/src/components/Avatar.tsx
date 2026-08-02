/* frontend/src/components/Avatar.tsx */
"use client";

import { UserButton, useUser } from "@clerk/nextjs";
import { IconUser } from "@/components/icons/TablerIcons";

type AvatarProps = {
  size?: string;
};

/*
 * ヘッダー用アバター表示
 * - 装飾ではなくステータス表示の一部として扱い、グラデーションは使用しない
 * - Clerkのデフォルト生成アバター(未設定時にグラデーション背景で描画される)は
 *   userButtonAvatarImageを非表示にした上で、緑1pxアウトライン円+緑モノクロアイコンに差し替える
 * - UserButtonのトリガー部分は avatarBox/avatarImage ではなく
 *   userButtonAvatarBox/userButtonAvatarImage というappearanceキーで制御する
 *   (avatarBox/avatarImageはUserProfile側のアバター編集UIに適用されるキーで、トリガーには効かない)
 * - ユーザーが独自の画像をアップロード済み(hasImage)の場合はその画像をそのまま表示する
 */
export default function Avatar({ size = "w-10 h-10" }: AvatarProps) {
  const { user } = useUser();
  const hasCustomImage = user?.hasImage ?? false;

  return (
    <div className={`relative ${size}`} suppressHydrationWarning>
      <UserButton
        appearance={{
          elements: {
            userButtonAvatarBox: `${size} border border-[#00ff41] bg-transparent`,
            userButtonAvatarImage: hasCustomImage ? "" : "opacity-0",
          },
        }}
      />
      {!hasCustomImage && (
        <IconUser className="absolute inset-0 m-auto w-5 h-5 text-[#00ff41] pointer-events-none" />
      )}
    </div>
  );
}
