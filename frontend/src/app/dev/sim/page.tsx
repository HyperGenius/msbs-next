/* frontend/src/app/dev/sim/page.tsx */
import { Suspense } from "react";
import { notFound } from "next/navigation";
import DevSimViewer from "./_components/DevSimViewer";

/** ローカルシミュレーションの結果を再生する開発用ページ。開発環境以外は 404 にする。 */
export default function DevSimPage() {
  if (process.env.NODE_ENV !== "development") notFound();
  return (
    // DevSimViewer は useSearchParams で選択中の世代とバトルを読む。
    <Suspense>
      <DevSimViewer />
    </Suspense>
  );
}
