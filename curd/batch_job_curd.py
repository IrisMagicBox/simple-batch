from typing import List, Dict, Any, Optional
from settings import DEFAULT_CONCURRENCY, DEFAULT_MAX_RETRIES
from const import JobStatus, RequestStatus
from database import get_db_connection


async def create_batch_job(batch_name: str, file_name: str, total_requests: int, api_info_id: int,
                          concurrency: int = DEFAULT_CONCURRENCY, max_retries: int = DEFAULT_MAX_RETRIES) -> int:
    """在batch_jobs表中插入一条记录，并返回job_id。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("""
            INSERT INTO batch_jobs (batch_name, file_name, total_requests, api_info_id, concurrency, max_retries)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (batch_name, file_name, total_requests, api_info_id, concurrency, max_retries))
        await conn.commit()
        return cursor.lastrowid
    finally:
        await conn.close()


async def get_pending_jobs_and_api_id() -> List[Dict[str, Any]]:
    """查询status='pending'的作业，并连接api_info表以获取API信息。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("""
            SELECT bj.*, ai.id as api_info_id, ai.alias as api_alias, ai.model_name
            FROM batch_jobs bj
            JOIN api_info ai ON bj.api_info_id = ai.id
            WHERE bj.status = ?
            ORDER BY bj.create_time
        """, (JobStatus.PENDING,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def update_job_status(job_id: int, status: str, start_time: Optional[str] = None, end_time: Optional[str] = None) -> None:
    """更新作业状态，并可选地记录开始/结束时间。"""
    updates = {"status": status}
    if start_time:
        updates["start_time"] = start_time
    if end_time:
        updates["end_time"] = end_time

    set_clauses = []
    values = []
    for key, value in updates.items():
        set_clauses.append(f"{key} = ?")
        values.append(value)

    set_clauses.append("update_time = datetime('now', 'localtime')")
    values.append(job_id)

    sql = f"UPDATE batch_jobs SET {', '.join(set_clauses)} WHERE id = ?"

    conn = await get_db_connection()
    try:
        await conn.execute(sql, values)
        await conn.commit()
    finally:
        await conn.close()


async def update_job_total_requests(job_id: int, total_requests: int) -> None:
    """更新作业的总请求数（用于流式文件解析）。"""
    conn = await get_db_connection()
    try:
        await conn.execute("""
            UPDATE batch_jobs 
            SET total_requests = ?, update_time = datetime('now', 'localtime')
            WHERE id = ?
        """, (total_requests, job_id))
        await conn.commit()
    finally:
        await conn.close()


async def get_jobs_by_status(status: str) -> List[Dict[str, Any]]:
    """根据状态获取作业列表（用于恢复机制）。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("SELECT * FROM batch_jobs WHERE status = ?", (status,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_incomplete_completed_jobs() -> List[Dict[str, Any]]:
    """获取状态为 'completed' 但有未完成请求的作业。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("""
            SELECT bj.* 
            FROM batch_jobs bj
            WHERE bj.status = ? AND EXISTS (
                SELECT 1 
                FROM batch_requests br 
                WHERE br.batch_job_id = bj.id 
                AND br.status IN (?, ?, ?)
            )
        """, (JobStatus.COMPLETED, RequestStatus.PENDING, RequestStatus.PROCESSING, RequestStatus.RETRYING))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def delete_job(job_id: int) -> None:
    """删除任务及其所有关联的记录（利用数据库级联删除）。"""
    conn = await get_db_connection()
    try:
        # 由于设置了外键级联删除（CASCADE），只需要删除batch_jobs记录
        # 相关的batch_requests、error_logs和performance_stats记录会自动删除
        await conn.execute("DELETE FROM batch_jobs WHERE id = ?", (job_id,))
        await conn.commit()
    finally:
        await conn.close()


async def reset_job_stats(job_id: int) -> None:
    """重置作业的统计信息。"""
    conn = await get_db_connection()
    try:
        await conn.execute("""
            UPDATE batch_jobs 
            SET success_count = 0, failed_count = 0, start_time = NULL, end_time = NULL
            WHERE id = ?
        """, (job_id,))
        await conn.commit()
    finally:
        await conn.close()


async def update_job_stats(job_id: int, success_count: int, failed_count: int) -> None:
    """更新作业的成功数和失败数。"""
    conn = await get_db_connection()
    try:
        await conn.execute("""
            UPDATE batch_jobs 
            SET success_count = ?, failed_count = ?
            WHERE id = ?
        """, (success_count, failed_count, job_id))
        await conn.commit()
    finally:
        await conn.close()


async def get_job_details(job_id: int) -> Optional[Dict[str, Any]]:
    """获取单个Job的详细信息（不包含所有请求记录以提高性能）。"""
    conn = await get_db_connection()
    try:
        # 获取作业基本信息
        cursor = await conn.execute("""
            SELECT *
            FROM batch_jobs
            WHERE id = ?
        """, (job_id,))
        job_row = await cursor.fetchone()

        if not job_row:
            return None

        job_info = dict(job_row)

        # 获取API信息
        cursor = await conn.execute("""
            SELECT *
            FROM api_info
            WHERE id = ?
        """, (job_info['api_info_id'],))
        api_row = await cursor.fetchone()
        job_info['api'] = dict(api_row) if api_row else {}

        # 获取性能统计信息
        cursor = await conn.execute("""
            SELECT avg_response_time, total_processing_time, requests_per_second, total_cost, pricing_info
            FROM performance_stats
            WHERE batch_job_id = ?
        """, (job_id,))
        perf_row = await cursor.fetchone()
        job_info['performance'] = dict(perf_row) if perf_row else {}

        # 获取错误日志（限制数量以提高性能）
        cursor = await conn.execute("""
            SELECT *
            FROM error_logs
            WHERE batch_job_id = ?
            ORDER BY create_time DESC
            LIMIT 100
        """, (job_id,))
        error_rows = await cursor.fetchall()
        job_info['errors'] = [dict(row) for row in error_rows]

        # 不再获取所有请求记录，以提高性能
        # 请求记录将通过分页接口按需加载
        job_info['requests'] = []

        return job_info
    finally:
        await conn.close()



async def get_all_jobs_summary() -> List[Dict[str, Any]]:
    """获取所有Job的列表和统计信息，用于UI仪表盘。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("""
            SELECT 
                bj.id, bj.batch_name, bj.file_name, bj.total_requests, bj.status,
                bj.success_count, bj.failed_count, bj.concurrency, bj.max_retries,
                bj.create_time, bj.start_time, bj.end_time,
                ai.id as api_info_id, ai.alias as api_alias, ai.model_name,
                ps.avg_response_time, ps.requests_per_second, ps.total_cost
            FROM batch_jobs bj
            LEFT JOIN api_info ai ON bj.api_info_id = ai.id
            LEFT JOIN performance_stats ps ON bj.id = ps.batch_job_id
            ORDER BY bj.create_time DESC
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()
