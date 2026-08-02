/* frontend/src/components/Avatar.tsx */
"use client";

import { UserButton, useUser } from "@clerk/nextjs";
import { IconUser } from "@/components/icons/TablerIcons";

type AvatarProps = {
  sizePx?: number;
};

/*
 * ヘッダー用アバター表示
 * - 装飾ではなくステータス表示の一部として扱い、グラデーションは使用しない
 * - UserButtonのトリガー部分は avatarBox/avatarImage ではなく
 *   userButtonAvatarBox/userButtonAvatarImage というappearanceキーで制御する
 *   (avatarBox/avatarImageはUserProfile側のアバター編集UIに適用されるキーで、トリガーには効かない)
 * - ClerkはデフォルトアバターをCSS-in-JS(emotion)のinline styleで描画しており、
 *   className文字列(通常の詳細度)では上書きできない。appearance.elementsにはCSSプロパティの
 *   オブジェクトも渡せる(emotionのcssとして後勝ちでマージされる)ため、そちらで確実に上書きする
 * - ユーザーが独自の画像をアップロード済み(hasImage)の場合はその画像をそのまま表示する
 */
export default function Avatar({ sizePx = 40 }: AvatarProps) {
  const { user } = useUser();
  const hasCustomImage = user?.hasImage ?? false;

  return (
    <div
      className="relative"
      style={{ width: sizePx, height: sizePx }}
      suppressHydrationWarning
    >
      <UserButton
        appearance={{
          elements: {
            userButtonAvatarBox: {
              width: sizePx,
              height: sizePx,
              border: "1px solid #00ff41",
              backgroundColor: "transparent",
              backgroundImage: "none",
              boxShadow: "none",
            },
            userButtonAvatarImage: hasCustomImage
              ? {}
              : { opacity: 0, visibility: "hidden" },
          },
        }}
      />
      {!hasCustomImage && (
        <IconUser className="absolute inset-0 m-auto w-5 h-5 text-[#00ff41] pointer-events-none z-10" />
      )}
    </div>
  );
}
