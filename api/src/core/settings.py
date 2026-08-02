"""应用设置读写（settings 表）

桌面端与 API 共用 SQLite 键值设置，默认值集中在 DEFAULT_SETTINGS；
运行时修改立即落库，供下次启动恢复。
"""

from datetime import datetime

from src.core.db import get_conn, init_db

DEFAULT_SETTINGS = {
    "active_model": "sensevoice",
    "hotkey": "f8",
    "chunk_ms": "600",
    "punc": "true",
    "model_dir_sensevoice": "",
    "model_dir_streaming": "",
    "model_dir_punc": "",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_all() -> dict:
    """返回全部设置（默认值 + 已持久化覆盖）"""
    init_db()
    result = dict(DEFAULT_SETTINGS)
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    for row in rows:
        result[row["key"]] = row["value"]
    return result


def get(key: str, default=None):
    """读取单项设置"""
    return get_all().get(key, default)


def set(key: str, value) -> None:
    """写入或更新一项设置"""
    init_db()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET "
            "value = excluded.value, updated_at = excluded.updated_at",
            (key, str(value), _now()),
        )
