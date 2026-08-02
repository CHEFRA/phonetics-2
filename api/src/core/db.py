"""SQLite 数据库层：连接、建表与基础迁移，路径见 src.core.config.DB_PATH"""

import sqlite3
from contextlib import contextmanager

from src.core.config import DB_PATH

_SCHEMA_VERSION = 1

_SCHEMA_V1 = """
-- 会话表：桌面客户端或 API 服务每次启动登记一个会话
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,               -- 会话唯一标识（UUID）
    app         TEXT NOT NULL DEFAULT 'desktop', -- 来源：desktop / api
    version     TEXT,                           -- 应用版本
    device      TEXT,                           -- 运行设备信息
    model       TEXT,                           -- 本次会话使用的模型
    started_at  TEXT NOT NULL,                  -- 会话开始时间（本地时间）
    ended_at    TEXT,                           -- 会话结束时间，NULL 表示仍在运行
    status      TEXT NOT NULL DEFAULT 'running' -- running / closed
);

-- 转写记录表：每次语音识别产生一条记录，是分析的主要数据来源
CREATE TABLE IF NOT EXISTS transcriptions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT, -- 自增主键
    session_id        TEXT NOT NULL,                     -- 所属会话 id
    created_at        TEXT NOT NULL,                     -- 识别完成时间（本地时间）
    source            TEXT NOT NULL,                     -- 来源：desktop / api
    model             TEXT NOT NULL,                     -- 使用的模型
    mode              TEXT NOT NULL DEFAULT 'batch',     -- batch（整段）/ stream（流式，预留）
    language          TEXT NOT NULL DEFAULT 'auto',      -- 语言参数
    text              TEXT NOT NULL DEFAULT '',          -- 识别文本，失败或空录音时为空
    audio_duration_ms INTEGER,                           -- 录音时长（毫秒）
    inference_ms      INTEGER,                           -- 推理耗时（毫秒）
    rtf               REAL,                              -- 实时率 = 推理耗时 / 录音时长
    mem_before_mb     REAL,                              -- 推理前进程内存（MB）
    mem_after_mb      REAL,                              -- 推理后进程内存（MB）
    status            TEXT NOT NULL,                     -- success / empty / error
    error             TEXT                               -- 出错信息，成功时为 NULL
);

-- 设置表：键值配置，供模型选择、热键等设置使用
CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY, -- 配置项名称
    value      TEXT NOT NULL,    -- 配置值
    updated_at TEXT NOT NULL     -- 最后更新时间
);

-- 按时间查询和按会话查询的常用索引
CREATE INDEX IF NOT EXISTS idx_transcriptions_created_at
    ON transcriptions (created_at);
CREATE INDEX IF NOT EXISTS idx_transcriptions_session_id
    ON transcriptions (session_id);
"""


def _connect() -> sqlite3.Connection:
    """创建数据库连接（WAL 模式，允许读写并发）"""
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_conn():
    """获取数据库连接，正常退出提交，异常回滚"""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """初始化数据库目录与表结构（幂等，带版本迁移）"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version < _SCHEMA_VERSION:
            conn.executescript(_SCHEMA_V1)
            conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
