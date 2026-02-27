import { redirect } from "next/navigation";

/**
 * Engineering機能はGarage画面に統合されました。
 * このページへのアクセスは /garage にリダイレクトします。
 */
export default function EngineeringPage() {
  redirect("/garage");
}
