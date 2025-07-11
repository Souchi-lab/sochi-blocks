-- SoChi BLOCKS — Core Foundation Schema (DDL)
-- Version: 0.1 (2025‑07‑10)
-- PostgreSQL 16  
-- 全テーブル PK/FK = UUID (v4 で生成、将来 uuidv7 拡張可)
-- -------------------------------------------------------------

-- ✨ EXTENSIONS ------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- gen_random_uuid()

-- =============================================================
-- マスタ系テーブル
-- =============================================================

-- 難易度マスタ -------------------------------------------------
CREATE TABLE master_difficulty (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(32) NOT NULL,
    level       SMALLINT    NOT NULL,
    UNIQUE (name)
);

-- パズルタイプマスタ -------------------------------------------
CREATE TABLE master_puzzle_type (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(32) NOT NULL,
    description TEXT,
    UNIQUE (name)
);

-- ユーザマスタ --------------------------------------------------
CREATE TABLE master_user (
    id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    username       VARCHAR(50)  NOT NULL,
    email          VARCHAR(128) NOT NULL UNIQUE,
    password_hash  TEXT,
    is_active      BOOLEAN      NOT NULL DEFAULT true,
    created_at     TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ピースマスタ --------------------------------------------------
CREATE TABLE master_piece (
    id          CHAR(1)      PRIMARY KEY,
    name        VARCHAR(32)  NOT NULL,
    shape_json  JSONB        NOT NULL
);

-- =============================================================
-- ベースパズル & Variant パズル
-- =============================================================

-- ベースパズル --------------------------------------------------
CREATE TABLE master_base_puzzle (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(128) NOT NULL,
    description     TEXT,
    puzzle_type_id  UUID         NOT NULL REFERENCES master_puzzle_type(id),
    author_id       UUID         NOT NULL REFERENCES master_user(id),
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ベースパズルのセル -------------------------------------------
CREATE TABLE master_base_puzzle_cell (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    base_puzzle_id  UUID        NOT NULL REFERENCES master_base_puzzle(id) ON DELETE CASCADE,
    x               SMALLINT    NOT NULL,
    y               SMALLINT    NOT NULL,
    z               SMALLINT    NOT NULL,
    value           CHAR(1)     NOT NULL REFERENCES master_piece(id),
    CONSTRAINT uq_base_puzzle_cell UNIQUE (base_puzzle_id, x, y, z)
);

-- Variant パズル ------------------------------------------------
CREATE TABLE content_puzzle (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    base_puzzle_id  UUID         NOT NULL REFERENCES master_base_puzzle(id) ON DELETE CASCADE,
    title           VARCHAR(128) NOT NULL,
    description     TEXT,
    difficulty_id   UUID         NOT NULL REFERENCES master_difficulty(id),
    puzzle_type_id  UUID         NOT NULL REFERENCES master_puzzle_type(id),
    author_id       UUID         NOT NULL REFERENCES master_user(id),
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- Variant パズルのセル -----------------------------------------
CREATE TABLE content_puzzle_cell (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    puzzle_id       UUID        NOT NULL REFERENCES content_puzzle(id) ON DELETE CASCADE,
    x               SMALLINT    NOT NULL,
    y               SMALLINT    NOT NULL,
    z               SMALLINT    NOT NULL,
    value           CHAR(1)     NOT NULL REFERENCES master_piece(id),
    CONSTRAINT uq_content_puzzle_cell UNIQUE (puzzle_id, x, y, z)
);

-- =============================================================
-- インデックス (性能チューニング用) -----------------------------
-- 主要 FK は自動で index が張られるが、検索頻度に応じて追加 --------

CREATE INDEX idx_master_base_puzzle_type ON master_base_puzzle(puzzle_type_id);
CREATE INDEX idx_master_base_puzzle_author ON master_base_puzzle(author_id);
CREATE INDEX idx_content_puzzle_type ON content_puzzle(puzzle_type_id);
CREATE INDEX idx_content_puzzle_difficulty ON content_puzzle(difficulty_id);
CREATE INDEX idx_content_puzzle_author ON content_puzzle(author_id);

-- =============================================================
-- トリガ: master_user.updated_at ---------------------------------

CREATE OR REPLACE FUNCTION trg_set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_master_user_updated_at
BEFORE UPDATE ON master_user
FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

-- =============================================================
-- 以上 ----------------------------------------------------------
