---
title: "P1-03-1 PDF Generation v1 Runbook"
version: "0.3.0"
owner: "SoChi-lab Backend Team"
last_updated: "2025-12-24"
status: "active"
tags: [runbook, backend, pdf-generation, core-foundation]
---

# 🎯 Purpose

完成形パズルデータ（JSON）から、**思考用の教材PDF（問題のみ）**を自動生成する。  
解答は 3D Viewer 側に委ね、PDF は「立体を想像するための媒体」として設計する。

---

## 🧩 Problem Design Policy (v1)

- PDF は **問題のみ**（答えは載せない）
- 問題は **完成形 − 抜いたピース** で構成する
- 使用不可マスは表現しない
- 空白は「薄い点（・）」で示す
- 3D Viewer で完成形を確認できることを前提とする

---

## 📥 Inputs

### 必須
- 完成形パズルJSON  
  例：`puzzle_5x4x3_0000.json`
- ピース定義JSON  
  例：`master_pieces.json`
- 抜くピースID配列  
  例：`["V", "W"]`

---

## 📤 Output

- A4縦 / 1ページ PDF
- 内容
  - ヘッダ（タイトル・Puzzle ID・Missing Pieces）
  - 3 Layer（Top / Middle / Bottom）盤面
  - 凡例

---

## 📐 Page & Layout Spec

### Page
- Size: A4 Portrait (595 × 842 pt)
- Margin: 36 pt

### Cell & Grid
- Cell size: **28 pt**
- Grid size: 5 × 4 (140 × 112 pt)

### Layer Order (Top → Bottom)
1. Layer 3 (Top / うえ)
2. Layer 2 (Middle / なか)
3. Layer 1 (Bottom / した)

---

## 🧊 Rendering Rules

### Cell Types

| 種別 | 表現 |
|---|---|
| ヒントセル | 色あり塗り + ピース記号 |
| 欠けセル | 白背景 + 薄い点「・」 |
| 使用不可 | 表現しない |

### Text & Color
- ピース記号：12pt / 黒
- 欠け点「・」：10pt / グレー (setFillGray(0.75))

---

## 🧾 Legend

PDF下部に以下を表示：

```
凡例：色＋文字 = ヒント / ・ = 空き
Missing Pieces: V, W
```

---

## 🔧 Implementation Notes (ReportLab)

- 座標原点は左下
- 各 Layer はラベル + グリッドで構成
- JSON の (x,y,z) を Layer 別に振り分け
- 抜いたピースIDに該当するセルは「・」を描画

---

## 🚦 Done Criteria

- JSON入力のみでPDFが生成できる
- PDF上で立体構造を想像できる
- 3D Viewer の完成形と整合する
