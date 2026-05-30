# CLAUDE.md — このプロジェクトでの作業ガイドライン

このファイルは、Claude Code がこのリポジトリで作業する際の規約・構造・判断基準を記述します。

---

## プロジェクト概要

MSBS（Mobile Suit Battle Simulator）は Next.js (App Router) + FastAPI で構成されたオンライン対戦ゲームです。
詳細なシステム設計は `Agent.md` および `docs/` を参照してください。

## Git ワークフロー

### Issueの起票ルール
- Issueは必ず `.github/ISSUE_TEMPLATE/` ディレクトリにあるテンプレートを参照してから起票すること

### Issueの作業ルール
- Issueに着手する前に必ずブランチを作成すること
- ブランチ命名規則: `feature/issue-{番号}-{概要}` または `fix/issue-{番号}-{概要}`

### Pull Requestのルール
- 作業が完了したらプルリクエストを作成すること
- プルリクエストを作成したら必ず `docs/features` ディレクトリ内の該当ドキュメントを更新すること
