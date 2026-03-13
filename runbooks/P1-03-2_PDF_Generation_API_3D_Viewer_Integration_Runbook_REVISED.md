---
title: "P1-03-2 PDF Generation API & 3D Viewer Integration Runbook"
version: "0.2.0"
owner: "SoChi-lab Frontend Team"
last_updated: "2025-12-24"
status: "active"
tags: [runbook, frontend, backend-api, pdf-generation, core-foundation]
---

# 🎯 Purpose

3D Viewer 上で表示中のパズルを **教材PDFとして即時ダウンロード**できるようにする。
本Runbookは **UI連携とブラウザDLまでの最短経路** を定義する。

---

## 🗺️ User Flow

```mermaid
flowchart LR
    A[3D Viewer] -->|Click PDF| B[Frontend]
    B -->|GET /api/v1/puzzles/{id}/pdf| C[Backend]
    C -->|PDF Binary| B
    B -->|Download| D[Browser]
```

---

## 📐 Tech Stack

* Frontend: React + TypeScript
* HTTP: fetch (推奨)
* Backend: FastAPI PDF API

---

## 🔧 Procedures

### Step 1: UIボタン追加

* Viewer ヘッダ or ツールバーに「PDF出力」ボタン
* puzzleId は Viewer state から取得

### Step 2: API呼び出し

```ts
const res = await fetch(`/api/v1/puzzles/${puzzleId}/pdf`);
if (!res.ok) throw new Error("PDF download failed");
const blob = await res.blob();
```

### Step 3: ダウンロード処理

```ts
const url = URL.createObjectURL(blob);
const a = document.createElement("a");
a.href = url;
a.download = `puzzle_${puzzleId}.pdf`;
a.click();
URL.revokeObjectURL(url);
```

---

## 🧪 Verification

* ローカル起動（docker-compose up）
* PDFボタンクリックでDL開始
* Safari / Chrome 両方で確認

---

## 🚦 Done Criteria

* UIからPDFが取得できる
* 既存3D Viewer機能を壊さない
* エラー時に console.error が出る
