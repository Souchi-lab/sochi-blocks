---
title: "P1-03-1 PDF Generation v1 Runbook"
version: "0.2.0"
owner: "SoChi-lab Backend Team"
last_updated: "2025-12-24"
status: "active"
tags: [runbook, backend, pdf-generation, core-foundation]
---

# 🎯 Purpose

教材コンテンツ（パズル定義・解答データ）から、**印刷可能な教材PDFを自動生成**する。
本Runbookは **MVP（v1）として最小構成でPDFを生成できる状態** をゴールとする。

* 対象：単一パズル（ID指定）
* 出力：1パズル = 1 PDF
* 想定利用：家庭印刷 / 教材配布

---

## 🗺️ Architecture Overview

```mermaid
flowchart LR
    A[Client / Frontend] -->|GET /api/v1/puzzles/{id}/pdf| B[FastAPI]
    B --> C[(PostgreSQL)]
    B --> D[PDF Generator Service]
    D -->|binary| B
    B -->|application/pdf| A
```

責務分離：

| レイヤ | 責務 |
|------|------|
| API | 認証・パラメータ検証・レスポンス |
| Service | PDFレイアウト生成 |
| DB | パズル定義・解答データ管理 |

---

## 📐 Tech Stack

* Backend: Python 3.11
* Framework: FastAPI
* PDF: ReportLab
* ORM: SQLAlchemy (既存)

---

## 🔧 Procedures

### Step 1: 依存関係追加

```bash
docker compose exec backend poetry add reportlab
```

### Step 2: PDF生成サービス実装

**File**: `backend/services/pdf_generator.py`

責務：
* パズルDTOを受け取る
* PDFをメモリ上で生成
* bytes を返却

最低限含める要素：
* パズルタイトル
* 問題説明（任意）
* 盤面図（簡易図 or テキスト）
* 解答（存在する場合）

### Step 3: APIエンドポイント実装

**Endpoint**: `GET /api/v1/puzzles/{puzzle_id}/pdf`

* puzzle_id の存在検証
* DB取得失敗時は 404
* StreamingResponse で返却
* Content-Disposition に filename 指定

### Step 4: 日本語フォント（必要な場合）

```dockerfile
RUN apt-get update && apt-get install -y fonts-noto-cjk
```

---

## 🧪 Verification

```bash
curl -o puzzle.pdf http://localhost:5000/api/v1/puzzles/{id}/pdf
```

確認項目：
* PDFが破損せず開ける
* 日本語が文字化けしない
* レイアウトが1ページに収まる

---

## 🚦 Done Criteria

* API経由でPDFが取得できる
* 教材として最低限成立する内容が含まれる
* Frontend からの呼び出しに耐える
