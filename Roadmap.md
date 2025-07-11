---

title: "SoChi BLOCKS Roadmap"
version: "0.1.7"  # Phase0 完了 / Vision タスク復活
owner: "SoChi‑lab"
last\_updated: "2025-07-10"
status: "draft"
tags: \[roadmap, timeline, governance]

---

# 🗺️ SoChi BLOCKS｜開発ロードマップ

> **目的**: Vision を現実に落とし込み、誰が・いつ・何を作るかを一元管理する。メタコメント (`<!-- deliverable:… task:… milestone:… status:… -->`) は GitHub Actions で JSON 化し、進捗レポート生成に利用。

---

## フェーズ一覧

| Phase                          | 期間 (目安)    | 主目的                                   | マイルストーン              | 状態        |
| ------------------------------ | ---------- | ------------------------------------- | -------------------- | --------- |
| **0. Project Init**\$1✅ Closed |            |                                       |                      |           |
| **1. Core Foundation**         | 2025‑08〜09 | DB 拡張 / 3D Viewer MVP / PDF v1        | **Core\_Foundation** | ⏳ Planned |
| **2. Advanced Docs**           | 2025‑10    | mkdocs nav / Glossary / i18n scaffold | **Docs\_MVP**        | ⏳ Planned |
| **3. Advanced Features**       | 2025‑10〜12 | リアルタイム対戦 / 教材投稿 UI / i18n             | **Feature\_MVP**     | ⏳ Planned |
| **4. Public Release**          | 2026‑01    | β公開 & 初期ユーザテスト                        | **Public\_Beta**     | ⏳ Planned |

---

## Phase 0 — Project Init (✅ Closed)

| ID          | Deliverable          | Status                                                                                      | 担当           | 備考                                                                                           |
| ----------- | -------------------- | ------------------------------------------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------- |
| P0‑01       | `CODE_OF_CONDUCT.md` | **Done**                                                                                    | Project Lead | PR #1 merged <!-- deliverable:CoC task:P0-01 milestone:Project_Init status:done -->          |
| P0‑02       | `CONTRIBUTING.md`    | **Done**                                                                                    | Maintainers  | PR #2 merged <!-- deliverable:Contributing task:P0-02 milestone:Project_Init status:done --> |
| P0‑03       | `GOVERNANCE.md`      | **Done**                                                                                    | Project Lead | PR #3 merged <!-- deliverable:Governance task:P0-03 milestone:Project_Init status:done -->   |
| P0‑04       | Core `README.md`     | **Done**                                                                                    | Maintainers  | PR #4 merged <!-- deliverable:Readme task:P0-04 milestone:Project_Init status:done -->       |
| \$1**Done** | Project Lead         | 完了条件: v1.0 タグ付 <!-- deliverable:Vision.md task:P0-05 milestone:Project_Init status:done --> |              |                                                                                              |

> **Phase 0** は P0‑05 完了後に Close。

---

## Phase 1 — Core Foundation (⏳ Planned)

| ID    | Deliverable                  | Status          | 担当           | GitHub Issue                                                                              |   |
| ----- | ---------------------------- | --------------- | ------------ | ----------------------------------------------------------------------------------------- | - |
| P1‑01 | DB スキーマ拡張（パズル定義・メタ情報）        | **In Progress** | Backend Dev  | #1 <!-- deliverable:Schema task:P1-01 milestone:Core_Foundation status:in_progress -->    |   |
| P1‑02 | 3D Viewer MVP（回転・ズーム・ピース配置）  | **Todo**        | Frontend Dev | #2 <!-- deliverable:3DViewer task:P1-02 milestone:Core_Foundation status:todo -->         |   |
| P1‑03 | PDF 自動生成 v1（教材テンプレ）          | **Todo**        | Backend Dev  | #3 <!-- deliverable:PDFv1 task:P1-03 milestone:Core_Foundation status:todo -->            |   |
| P1‑04 | 教材管理 UI（CRUD）                | **Todo**        | Full‑stack   | #4 <!-- deliverable:AdminUI task:P1-04 milestone:Core_Foundation status:todo -->          |   |
| P1‑05 | 基本 API（認証 / コンテンツ取得）         | **Todo**        | Backend Dev  | #5 <!-- deliverable:API task:P1-05 milestone:Core_Foundation status:todo -->              |   |
| P1‑06 | ディレクトリ再編（backend/db/infra 等） | **In Progress** | All Devs     | #6 <!-- deliverable:Dir_Reorg task:P1-06 milestone:Core_Foundation status:in_progress --> |   |

<!-- Subtasks for P1‑01 -->

<!-- deliverable:ER_Diagram task:P1-01-1 milestone:Core_Foundation status:done -->

<!-- deliverable:Schema_Migration task:P1-01-2 milestone:Core_Foundation status:in_progress -->

<!-- deliverable:JSON_to_DB_Migration_Script task:P1-01-3 milestone:Core_Foundation status:todo -->

<!-- deliverable:Sample_Data_Select_Test task:P1-01-4 milestone:Core_Foundation status:todo -->

<!-- deliverable:Docs_Update task:P1-01-5 milestone:Core_Foundation status:todo -->

<!-- deliverable:Solution_Data_Import task:P1-01-6 milestone:Core_Foundation status:todo -->

---

## Phase 2 — Advanced Docs (⏳ Planned)

| ID    | Deliverable         | Status   | 担当        | 備考 / Issue                                                                                  |
| ----- | ------------------- | -------- | --------- | ------------------------------------------------------------------------------------------- |
| P2‑01 | `docs/_index.md` 初版 | **Todo** | Docs Team | mkdocs nav 反映 <!-- deliverable:docs/_index.md task:P2-01 milestone:Docs_MVP status:todo --> |
| P2‑02 | `Glossary.md` 雛形    | **Todo** | Docs Team | 基本20語登録 <!-- deliverable:Glossary.md task:P2-02 milestone:Docs_MVP status:todo -->          |

---

## 🏁 マイルストーン定義

| Milestone            | 完了条件                                   |
| -------------------- | -------------------------------------- |
| **Project\_Init**    | Phase 0 すべて完了、レポジトリ公開                  |
| **Core\_Foundation** | Phase 1 すべて完了、Docker でサーバ & Viewer が起動 |
| **Docs\_MVP**        | Phase 2 すべて完了、mkdocs CI が動作            |
| **Feature\_MVP**     | Phase 3 すべて完了、i18n & 対戦モード β           |
| **Public\_Beta**     | Phase 4 すべて完了、外部ユーザがサインアップし教材を体験できる    |

---

## 📌 補足

* **メタコメント活用**：CI スクリプトで `<deliverable|task|milestone|status>` を抽出し、JSON へ加工 → ダッシュボード表示予定。
* **i18n**：Phase 2 で docs/ja/, docs/en/ のディレクトリを用意し、Phase 4 UI で英語・日本語切替を実装予定。
* **Glossary**：Phase 2 で 20 語、Phase 4 で 50 語を目標に追加していく予定。

> 🔖 *内容追加・修正希望があれば Issue / PR コメントでお気軽に！*
