from typing import Optional

from database import get_db_connection


async def log_error_to_db(job_id: int, request_id: Optional[int], error_type: str, error_message: str,
                         error_details: Optional[str] = None) -> None:
    """在error_logs表中插入一条错误记录。"""
    conn = await get_db_connection()
    try:
        await conn.execute("""
            INSERT INTO error_logs (batch_job_id, request_id, error_type, error_message, error_details)
            VALUES (?, ?, ?, ?, ?)
        """, (job_id, request_id, error_type, error_message, error_details))
        await conn.commit()
    finally:
        await conn.close()


async def count_errors_for_job(job_id: int) -> int:
    """统计某作业的错误日志总数。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("""
            SELECT COUNT(*) AS cnt
            FROM error_logs
            WHERE batch_job_id = ?
        """, (job_id,))
        row = await cursor.fetchone()
        return int(row['cnt'] if row and 'cnt' in row.keys() else 0)
    finally:
        await conn.close()


async def get_errors_for_job_paginated(job_id: int, limit: int, offset: int):
    """分页获取某作业的错误日志，按创建时间倒序。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT id, batch_job_id, request_id, error_type, error_message, error_details, create_time
            FROM error_logs
            WHERE batch_job_id = ?
            ORDER BY create_time DESC
            LIMIT ? OFFSET ?
            """,
            (job_id, limit, offset)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()
