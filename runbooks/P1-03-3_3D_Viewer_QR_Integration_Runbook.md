---
title: "P1-03-3 3D Viewer QR Integration Runbook"
version: "0.1.0"
owner: "SoChi-lab Frontend Team"
last_updated: "2025-12-27"
status: "draft"
tags: [runbook, frontend, qr-integration, 3d-viewer]
---

# 🎯 Purpose

PDFに埋め込まれたQRコードをスキャンすることで、3Dビューワーが自動的に起動し、QRコードにエンコードされたパズルIDと抜かれたピースの情報に基づいて、該当するパズルを3Dビューワーに表示できるようにする。

---

## 💡 Background

- **バックエンド実装済み**:
  - P1-03-1: パズル問題PDF生成機能がバックエンドで実装済み。
  - P1-03-2: PDF生成APIが利用可能 (`GET /api/v1/puzzles/{puzzle_id}/pdf?removed_pieces=V,W`)。
  - PDF内のQRコードは、以下の形式のURLをエンコードするようになっている。
    `http://localhost:8080/viewer?puzzle_id={puzzle_id}&removed_pieces={removed_pieces_str}`
    (例: `http://localhost:8080/viewer?puzzle_id=5x4x3_0000&removed_pieces=V,W`)

- **フロントエンド未実装**:
  - 現在、3DビューワーはQRコードからのURLを解析し、パズルを表示する機能は未実装。

---

## 🤝 Integration Policy / Strategy

1.  **URLパラメータの解析**: 3Dビューワーは、起動時にURLのクエリパラメータから `puzzle_id` と `removed_pieces` を解析する。
2.  **パズルデータの取得**: 解析した `puzzle_id` を使用して、バックエンドAPIからパズルデータ（例: `puzzle_5x4x3_0000.json` の内容）を取得する。
    *   **注意**: 現在、パズルデータ自体を取得するAPIエンドポイントは未定義。必要に応じて `GET /api/v1/puzzles/{puzzle_id}` のようなAPIをバックエンドで別途実装する必要がある。
3.  **パズルの表示**: 取得したパズルデータと、URLから解析した `removed_pieces` の情報に基づいて、3Dビューワーにパズルを表示する。

---

## 🔧 Procedures (Frontend)

### Step 1: URLパラメータの解析ロジックの実装

- **対象ファイル例**: `frontend/src/App.tsx` または `frontend/src/components/Viewer.tsx` など、アプリケーションのルートコンポーネントまたはビューワーコンポーネント。
- **実装内容**:
  - コンポーネントのマウント時（`useEffect` など）に、`window.location.search` を使用してURLのクエリ文字列を取得する。
  - `URLSearchParams` オブジェクトを使用して `puzzle_id` と `removed_pieces` パラメータを抽出する。
  - `removed_pieces` はカンマ区切りの文字列として取得されるため、配列に変換する。

### Step 2: パズルデータ取得APIの呼び出し

- **対象ファイル例**: 上記と同様のコンポーネント。
- **実装内容**:
  - 解析した `puzzle_id` を使用して、バックエンドからパズルデータを取得するAPIを呼び出す。
  - 例: `fetch('/api/v1/puzzles/${puzzleId}')`
  - 取得したパズルデータをコンポーネントのステートに保存する。

### Step 3: 3Dビューワーでのパズル表示ロジックの調整

- **対象ファイル例**: `frontend/src/components/Viewer.tsx` など、実際にパズルを描画するコンポーネント。
- **実装内容**:
  - 取得したパズルデータと、URLから解析した `removed_pieces` の情報に基づいて、パズルを3Dビューワーに表示する。
  - `removed_pieces` に含まれるピースは、ビューワー上で非表示にするか、特別な表示（例: 半透明）にする。

---

## 🧪 Verification (Frontend)

1.  **フロントエンドの起動**: `npm run dev` などでフロントエンドアプリケーションを起動する。
2.  **URLへのアクセス**:
    *   QRコードをスキャンするか、ブラウザで以下のURLに直接アクセスする。
      `http://localhost:8080/viewer?puzzle_id=5x4x3_0000&removed_pieces=V,W`
3.  **表示の確認**:
    *   3Dビューワーが起動し、`5x4x3_0000` のパズルが表示されること。
    *   ピース `V` と `W` が抜かれた状態で表示されること。

---

## 🚦 Done Criteria

1.  QRコードから読み取ったURL（または手動入力URL）で3Dビューワーが起動する。
2.  URLパラメータから `puzzle_id` と `removed_pieces` が正しく解析される。
3.  解析された情報に基づいて、該当するパズルが3Dビューワーに表示される。
4.  `removed_pieces` に指定されたピースが、ビューワー上で正しく処理（非表示など）される。

---
