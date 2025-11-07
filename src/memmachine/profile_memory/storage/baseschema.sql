-- 启用 pgvector 扩展，用于向量相似度检索
CREATE EXTENSION IF NOT EXISTS vector;

-- 存放迁移等元数据的独立 schema
CREATE SCHEMA IF NOT EXISTS metadata;

-- TODO: 优化 metadata 与 isolations 的数据建模，避免直接依赖 jsonb
-- prof 表用于记录用户的结构化画像信息及其嵌入向量
CREATE TABLE IF NOT EXISTS prof (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    tag TEXT NOT NULL DEFAULT 'Miscellaneous',
    feature TEXT NOT NULL,
    value TEXT NOT NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    embedding vector NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    isolations JSONB NOT NULL DEFAULT '{}'
);

-- 加速按 user_id 检索画像条目的查询
CREATE INDEX IF NOT EXISTS prof_user_idx ON prof (user_id);

-- history 表用于存储原始事件/内容记录，供后续构建画像或引用
CREATE TABLE IF NOT EXISTS history (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    ingested BOOLEAN NOT NULL DEFAULT FALSE,
    content TEXT NOT NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB NOT NULL DEFAULT '{}',
    isolations JSONB NOT NULL DEFAULT '{}'
);

-- 基于 user_id 的常用查询索引
CREATE INDEX IF NOT EXISTS history_user_idx ON
    history (user_id);
-- 根据 user_id 与 ingested 状态过滤
CREATE INDEX IF NOT EXISTS history_user_ingested_idx ON
    history (user_id, ingested);
-- 按时间倒序快速获取指定用户的已处理/未处理内容
CREATE INDEX IF NOT EXISTS history_user_ingested_ts_desc ON
    history (user_id, ingested, create_at DESC);


-- citations 表维护画像条目与历史内容之间的关联关系
CREATE TABLE IF NOT EXISTS citations (
    profile_id INTEGER REFERENCES prof(id) ON DELETE CASCADE,
    content_id INTEGER REFERENCES history(id) ON DELETE CASCADE,
    PRIMARY KEY (profile_id, content_id)
);

-- 记录 schema 迁移版本及其执行时间
CREATE TABLE IF NOT EXISTS metadata.migration_tracker (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);