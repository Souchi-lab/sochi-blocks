<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

## SoChi BLOCKS プロジェクト安定稼働のための具体的な修正ポイント

以下は、ご提示いただいた包括的方針を踏まえた上で、**根本原因の解消と安定稼働のために必要な修正ポイント**です。修正の意図を端的に記載していますので、各ポイントに沿って適用を進めてください。

### 1. Dockerfile.backend の修正

- **Poetryの仮想環境をOFF化し、システム環境に直接インストール**
- 必要なmain/dev依存を一括導入（`RUN poetry install --no-root --only main,dev`）
- ソースコード/マイグレーションファイルも忘れずにCOPY
- solver用のRubyセットアップ、CMDはdocker-composeで上書き

```dockerfile
FROM python:3.13-slim

RUN pip install --no-cache-dir poetry
WORKDIR /workspace

ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_NO_INTERACTION=1

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --only main,dev

COPY . .
COPY db/migrations/versions/ db/migrations/versions/

RUN apt-get update && apt-get install -y ruby ruby-json
COPY tools/pentomino/ /opt/solver/
ENV SOLVER_HOME=/opt/solver
```

**主なポイント**

- システムインストール化と依存ファイルの明示的COPYで、仮想環境やマイグレーションの不整合を徹底排除できます。


### 2. docker-compose.yml のbackendサービス command修正

- **起動時コマンドを `poetry run python backend/app.py` に統一**
- 必ずPoetry経由でFlaskアプリを実行し、依存の食い違い・PATH問題の連鎖を断ちます

```yaml
backend:
  container_name: sochi_backend
  build:
    context: ../../
    dockerfile: infra/docker/Dockerfile.backend
  env_file: ../../.env
  depends_on:
    db:
      condition: service_healthy
  command: poetry run python backend/app.py
  volumes:
    - ../../:/workspace
```


---

### 3. backend/scripts/solution_data_import.py の get_or_create_dummy 修正

- **IntegrityError発生時のロールバック後でもNone返却時は必ず例外をraise**
- 「.id AttributeError」を根治するガードを実装

```python
def get_or_create_dummy(session, model, id_val, **kwargs):
    instance = session.query(model).filter_by(id=id_val).first()
    if not instance:
        creation_args = {"id": id_val}
        if model.__tablename__ == "master_user":
            creation_args.update({
                "username": f"Dummy {model.__tablename__}",
                "email": f"dummy_{model.__tablename__}@{id_val}.com",
                "password_hash": "dummy_password_hash",
                "is_active": True,
                "created_at": func.now(),
                "updated_at": func.now()
            })
        elif model.__tablename__ == "master_base_puzzle":
            creation_args.update({
                "name": f"Dummy {model.__tablename__}",
                "puzzle_type_id": kwargs['puzzle_type_id'],
                "author_id": kwargs['author_id'],
                "created_at": func.now()
            })
        else:
            creation_args.update({"name": f"Dummy {model.__tablename__}"})

        instance = model(**creation_args)
        session.add(instance)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            instance = session.query(model).filter_by(id=id_val).first()
            if not instance:
                raise Exception(f"Failed to get or create dummy instance for {model.__tablename__} with id {id_val}")
    return instance
```


### 4. backend/app.py の修正

- **Flaskの起動確認・API基本動作の例**

```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello from backend!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```


### 5. pyproject.toml へのflask追加

- **Poetry依存にFlaskを必ず追加**

```toml
[tool.poetry.dependencies]
python = "^3.13"
psycopg2-binary = ">=2.9.10,<3.0.0"
flask = "^3.0.3"   # 追加
```


## 適用の流れ

1. コード・構成ファイルを上記の通り修正
2. `poetry lock` で依存を同期
3. `docker compose build --no-cache` で完全再ビルド
4. `docker compose up` で起動
5. Alembicマイグレーション（`upgrade head`）、データインポート等を順次実施
6. Flask/api/DB等の動作を個別に確実に検証

これらの全面的な修正適用で、**仮想環境・依存・マイグレーション・データ生成/投入・Flask起動まで、根本的な混乱やバグを未然に防げる構成**になります。

ご質問、適用支援などが必要な場合はご連絡ください。

