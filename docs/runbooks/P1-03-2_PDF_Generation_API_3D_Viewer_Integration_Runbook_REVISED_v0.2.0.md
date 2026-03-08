---
title: "P1-03-2 PDF Generation API & 3D Viewer Integration Runbook"
version: "0.2.0"
owner: "SoChi-lab Frontend Team"
last_updated: "2025-12-26"
status: "active"
tags: [runbook, frontend, backend-api, pdf-generation, core-foundation]
---

# 🎯 Purpose

バックエンドで実装されるPDF生成API（`P1-03-1`）をフロントエンド（3Dビューワー）から呼び出し、現在表示中のパズルを **問題PDF（1枚）** として出力・ダウンロードできるようにする。

> 本Runbookは「**PDFの見た目（ビジュアル契約）**」を前提条件として明文化し、P1-03-1 側の生成結果をフロントから検証できるようにする。

---

## 🗺️ Overview

```mermaid
flowchart LR
  A[3D Viewer UI] -->|GET /api/v1/puzzles/{id}/pdf?removed_pieces=V,W| B[Backend PDF API]
  B -->|application/pdf| A
  A --> C[Browser Download]
```

---

## 🎨 Visual Contract (MUST) — v1 PDF Look

P1-03-1 が生成するPDFは、以下の見た目（契約）を満たすこと。フロントエンドはこの見た目を「期待結果」として検証する。

### Page & Layout
- A4縦 / 1ページ
- ヘッダに以下を表示
  - タイトル（例：`SoChi BLOCKS Puzzle`）
  - Puzzle ID
  - `Missing Pieces:`（抜いたピースを表示）
- 本文に 3つのレイヤーを横並びで表示
  - `Layer 1 (Bottom)` / `Layer 2 (Middle)` / `Layer 3 (Top)`
  - 各レイヤーは 5×4 のグリッド（枠線あり）
- ページ下部にQRコード（3D Viewerへの導線）

### Cell Rendering Rules
- **ヒントセル（残っているピース）**
  - セル背景をピース色で塗りつぶす（視認性優先）
  - ※ v1ではセル内の文字（F/I/…）は任意。あってもなくても良い（色認知が主）
- **空いているマス（抜いたピースの領域）**
  - **白（塗りなし）**
  - 点（・）などのマーカーは **付けない**（v1決定）
- **使用不可マス**
  - v1では概念として扱わない（完成形ベースのため）

### Missing Pieces Rendering
- `Missing Pieces:` の右に、抜いたピース（例：V, W）を
  - **色付き**
  - **形状が分かるミニグリッド**
 で表示する

---

## 📐 Tech Stack

- **Frontend**: React, TypeScript
- **Backend**: Flask
- **HTTP Client**: fetch（推奨） or axios
- **PDF Delivery**: `application/pdf` を Blob として取得し、ブラウザのダウンロード機能へ渡す

---

## 🔌 API Contract

### Endpoint
- `GET /api/v1/puzzles/{puzzle_id}/pdf`

### Query Parameters
- `removed_pieces`（任意）
  - 例：`removed_pieces=V,W`
  - 未指定の場合の扱いは P1-03-1 に従う（推奨：デフォルトは空＝欠けなし）

### Response
- `200 OK`
- `Content-Type: application/pdf`
- `Content-Disposition: attachment; filename="puzzle_{id}_problem.pdf"`（推奨）

---

## 🔧 Procedures

### Step 1: フロントエンドに「PDF出力」ボタンを追加

対象例：`frontend/src/components/ViewerToolbar.tsx`（実際の配置先に合わせて調整）

- 「PDF出力」ボタンを追加
- クリックで `handleDownloadPdf()` を呼ぶ

### Step 2: PDF生成APIの呼び出し

`fetch` でPDFを取得し、Blob化する。

- 例：`/api/v1/puzzles/${puzzleId}/pdf?removed_pieces=${removedPieces.join(",")}`
- `removedPieces` はUI状態（例：問題生成で抜いたピース）に合わせて渡す

### Step 3: PDFファイルのダウンロード

- Blob を `URL.createObjectURL()` でURL化
- `<a download>` を生成してクリック
- 後処理として `URL.revokeObjectURL()`

---

## 🧪 Verification (Frontend)

1. **起動**: `docker-compose up` でサービス起動
2. **3Dビューワー**: `http://localhost:8080` を開く
3. **PDF出力**: 「PDF出力」ボタンをクリック
4. **ダウンロード確認**: PDFが保存されること
5. **見た目確認（重要）**: PDFを開き、以下を満たすことを確認
   - 3つのレイヤーが横並び（Layer 1/2/3）
   - ヒントセルが **色付き**
   - 空いているマスが **白**
   - Missing Pieces が **色付き＆形状表示**
   - QRコードが下部に表示

---

## 🚦 Done Criteria

1. 3DビューワーのUIに「PDF出力」ボタンがある
2. クリックで `GET /api/v1/puzzles/{id}/pdf` が呼ばれる（removed_pieces 付き）
3. PDFがブラウザ経由で保存できる
4. 生成PDFが **Visual Contract (MUST)** を満たす（色分け、空白=白、Missing Pieces形状、3レイヤー横並び、QR）

---

## 📝 Notes

- 本Runbookは「フロントでPDFを描画する」ものではなく、**バックエンド生成PDFを取得してダウンロードする**ことに専念する。
- 見た目（Visual Contract）は P1-03-1 の実装結果を検証する基準としても機能する。
