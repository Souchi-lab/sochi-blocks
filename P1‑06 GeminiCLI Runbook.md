# P1‑06 GeminiCLI Runbook 🧑‍💻 (v0.2)

> **現状フォルダ構成**（2025‑07‑11 時点）
>
> ```text
> .
> │  CODE_OF_CONDUCT.md
> │  CONTRIBUTING.md
> │  GOVERNANCE.md
> │  LICENSE
> │  P1‑06 GeminiCLI Runbook.md
> │  README.md
> │  Roadmap.md
> │  schema.sql
> │  Vision.md
> └─.github/...
> ```
>
> **= src/ も docker-compose.yml も無い** 状態。Runbook では *存在前提* のファイルを**プレースホルダ生成**に切り替えて対応します。

---

## 0. 前提

* ブランチ `feature/p1-06-dir-reorg` が dev から切られている。
* Python v3.12 & Poetry。

```bash
BRANCH=feature/p1-06-dir-reorg
PR_TITLE="feat: P1-06 dir reorg + Alembic bootstrap"
```

---

## 1. ディレクトリ & ファイル整備

```bash
########## 1‑1. backend 雛形 ##########
mkdir -p backend/{models,services,api}
# まだ app が無いのでプレースホルダを作成
printf "# placeholder\nprint(\"backend bootstrapped\")" > backend/app.py

########## 1‑2. schema.sql → db/ ##########
mkdir -p db
git mv schema.sql db/schema.sql

########## 1‑3. Docker eco‑system ##########
# docker-compose.yml が無いので最低限だけ生成
mkdir -p infra/docker
cat > infra/docker/docker-compose.yml <<'YAML'
version: '3.9'
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: example
    ports:
      - "5432:5432"
YAML
# Dockerfile* が無い場合はスキップ可

########## 1‑4. CI helper ##########
mkdir -p infra/scripts
# .github/workflows があれば後で path 修正 (ここでは移動なし)

########## 1‑5. Alembic init ##########
poetry add --group dev alembic
alembic init db/migrations

########## 1‑6. placeholder for terraform ##########
mkdir -p infra/terraform
printf "# Terraform IaC (placeholder)\n\n未実装です。TODO: Phase‑3 で具体化。" > infra/terraform/README.md

########## 1‑7. docs, tests 雛形 ##########
mkdir -p docs tests/unit
```

**コミット例**

1. `chore(dir): scaffold backend/, db/, infra/, docs/, tests/`
2. `chore(db): move schema.sql -> db/`
3. `chore(db): bootstrap alembic`

---

## 2. テスト & CI 確認（最低限）

```bash
pytest -q || true   # テストまだ無いので true でスキップ可
poetry run alembic upgrade head  # migration OK?
```

---

## 3. README・Roadmap 更新

```bash
# Roadmap.md version bump
sed -i -e 's/version: .*/version: 0.1.8/' -e 's/last_updated:.*/last_updated: 2025-07-11/' Roadmap.md

git add Roadmap.md README.md
git commit -m "docs: update paths & bump version to v0.1.8"
```

---

## 4. プッシュ & PR 作成

```bash
git push -u origin $BRANCH
gh pr create --title "$PR_TITLE" \
  --body "P1-06 directory re‑organization & Alembic bootstrap (placeholder files included). See P1-06-directory-reorg-proposal.md for details." \
  --base dev
```

---

## 5. レビュー / マージ条件

* CI Green（テスト未実装でも workflow が落ちないか）
* 2 approvals
* squash merge into dev

---

### MEMO

* `.github/workflows/` の `paths:` などは新ディレクトリに合わせて後続 PR で修正。
* Docker／Compose の本設定は Phase‑2 で Flesh‑out。

> 🚀 **Gemini CLI**、この Runbook v0.2 を実行してね！
