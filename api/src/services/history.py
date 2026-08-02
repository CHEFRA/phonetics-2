"""识别历史记录服务

提供会话生命周期、转写记录写入和基础统计查询。
时间统一使用本地时间字符串 YYYY-MM-DD HH:MM:SS，便于按日/月分组。
"""

import uuid
from datetime import datetime

from src.core.db import get_conn, init_db
from src.core.logger import make_console_safe

make_console_safe()


def now_iso() -> str:
    """当前本地时间字符串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def start_session(
    app: str = "desktop",
    version: str | None = None,
    device: str | None = None,
    model: str | None = None,
) -> str:
    """开始一个会话，返回会话 id"""
    init_db()
    session_id = uuid.uuid4().hex
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (id, app, version, device, model, started_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'running')",
            (session_id, app, version, device, model, now_iso()),
        )
    return session_id


def end_session(session_id: str, status: str = "closed") -> None:
    """结束会话"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET ended_at = ?, status = ? WHERE id = ?",
            (now_iso(), status, session_id),
        )


def record_transcription(
    *,
    session_id: str,
    source: str,
    model: str,
    text: str,
    status: str,
    error: str | None = None,
    audio_duration_ms: int | None = None,
    inference_ms: int | None = None,
    rtf: float | None = None,
    mem_before_mb: float | None = None,
    mem_after_mb: float | None = None,
    mode: str = "batch",
    language: str = "auto",
) -> int:
    """写入一条转写记录，返回记录 id"""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO transcriptions "
            "(session_id, created_at, source, model, mode, language, text, "
            "audio_duration_ms, inference_ms, rtf, mem_before_mb, mem_after_mb, "
            "status, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                now_iso(),
                source,
                model,
                mode,
                language,
                text,
                audio_duration_ms,
                inference_ms,
                rtf,
                mem_before_mb,
                mem_after_mb,
                status,
                error,
            ),
        )
        return int(cur.lastrowid)


def recent(limit: int = 20) -> list[dict]:
    """最近 N 条转写记录"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM transcriptions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def daily_counts(days: int = 30) -> list[dict]:
    """最近 N 天的每日转写次数（含成功、失败、空录音）"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS cnt "
            "FROM transcriptions "
            "WHERE created_at >= datetime('now', 'localtime', ?) "
            "GROUP BY day ORDER BY day",
            (f"-{days - 1} days",),
        ).fetchall()
    return [dict(row) for row in rows]


def monthly_counts(months: int = 12) -> list[dict]:
    """最近 N 个月的每月转写次数"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT substr(created_at, 1, 7) AS month, COUNT(*) AS cnt "
            "FROM transcriptions "
            "WHERE created_at >= datetime('now', 'localtime', ?) "
            "GROUP BY month ORDER BY month",
            (f"-{months - 1} months",),
        ).fetchall()
    return [dict(row) for row in rows]


def overview() -> dict:
    """整体统计：总量、成功率、平均推理耗时、平均 RTF、平均录音时长"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_cnt, "
            "AVG(inference_ms) AS avg_inference_ms, "
            "AVG(rtf) AS avg_rtf, "
            "AVG(audio_duration_ms) AS avg_audio_ms "
            "FROM transcriptions"
        ).fetchone()
    return dict(row)


def _print_report() -> None:
    """命令行快速查看历史统计"""
    init_db()
    data = overview()
    print("== 整体统计 ==")
    print(
        f"总次数: {data['total']} | 成功: {data['success_cnt'] or 0} | "
        f"平均推理: {(data['avg_inference_ms'] or 0) / 1000:.2f}s | "
        f"平均 RTF: {data['avg_rtf'] or 0:.3f} | "
        f"平均录音: {(data['avg_audio_ms'] or 0) / 1000:.1f}s"
    )
    print("\n== 最近 7 天使用次数 ==")
    for item in daily_counts(7):
        print(f"{item['day']}  {item['cnt']} 次")
    print("\n== 最近记录 ==")
    for row in recent(5):
        status = row["status"]
        text = row["text"][:30] if row["text"] else "(空)"
        audio = (row["audio_duration_ms"] or 0) / 1000
        infer = (row["inference_ms"] or 0) / 1000
        print(
            f"{row['created_at']} [{status}] {row['model']} | "
            f"录音 {audio:.1f}s | 推理 {infer:.2f}s | {text}"
        )


if __name__ == "__main__":
    _print_report()
