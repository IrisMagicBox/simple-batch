import json
from typing import Optional, List, Dict, Any
from const import RequestStatus
from database import get_db_connection
from core.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


async def bulk_update_request_status(updates: List[Dict[str, Any]]) -> None:
    """批量更新请求状态"""
    if not updates:
        return
        
    conn = await get_db_connection()
    try:
        # 构建批量更新SQL
        sql = """
            UPDATE batch_requests 
            SET status = ?, start_time = ?
            WHERE id = ?
        """
        
        # 准备参数
        values = [
            (update['status'], update.get('start_time'), update['request_id'])
            for update in updates
        ]
        
        await conn.executemany(sql, values)
        await conn.commit()
    finally:
        await conn.close()


async def get_requests_by_time_bucket(job_id: int, bucket: str, interval_ms: int, category: str) -> List[Dict[str, Any]]:
    """按时间桶与类别获取请求列表。
    - category: 'requests' 基于 start_time 归入桶；'success'/'failed' 基于 end_time 且状态匹配。
    返回解析后的记录列表（messages 已尽量转为对象）。
    """
    from datetime import datetime, timedelta
    
    def parse_ts(ts: str):
        try:
            return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        except Exception:
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                return None
    
    def format_bucket(ts: datetime) -> str:
        if interval_ms < 1000:
            return ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        elif interval_ms < 60000:
            return ts.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return ts.strftime("%Y-%m-%d %H:%M")
    
    epoch = datetime(1970, 1, 1)
    def floor_to_interval(dt: datetime) -> datetime:
        delta_ms = int((dt - epoch).total_seconds() * 1000)
        floored = (delta_ms // interval_ms) * interval_ms
        return epoch + timedelta(milliseconds=floored)
    
    conn = await get_db_connection()
    try:
        # 取该作业的所有请求，后续在Python中过滤到桶，避免SQLite复杂时间对齐
        cursor = await conn.execute(
            """
            SELECT id, batch_job_id, request_index, messages, status, retry_count,
                   response_body, prompt_tokens, completion_tokens, total_tokens,
                   start_time, end_time, create_time
            FROM batch_requests
            WHERE batch_job_id = ?
            """,
            (job_id,)
        )
        rows = await cursor.fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            rec = dict(row)
            st = rec.get('start_time')
            et = rec.get('end_time')
            st_dt = parse_ts(st) if st else None
            et_dt = parse_ts(et) if et else None
            match = False
            if category == 'requests' and st_dt:
                if format_bucket(floor_to_interval(st_dt)) == bucket:
                    match = True
            elif category in ('success', 'failed') and et_dt:
                if format_bucket(floor_to_interval(et_dt)) == bucket and rec.get('status') == (RequestStatus.SUCCESS if category=='success' else RequestStatus.FAILED):
                    match = True
            if match:
                try:
                    if isinstance(rec.get('messages'), str):
                        rec['messages'] = json.loads(rec['messages'])
                except Exception:
                    pass
                results.append(rec)
        return results
    finally:
        await conn.close()

async def get_request_by_id(request_id: int) -> Optional[Dict[str, Any]]:
    """根据ID获取单条请求的完整内容（messages、response_body等）。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT id, batch_job_id, request_index, messages, status, retry_count,
                   response_body, prompt_tokens, completion_tokens, total_tokens,
                   start_time, end_time, create_time
            FROM batch_requests
            WHERE id = ?
            """,
            (int(request_id),)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        record: Dict[str, Any] = dict(row)
        try:
            if isinstance(record.get('messages'), str):
                record['messages'] = json.loads(record['messages'])
        except Exception:
            pass
        return record
    finally:
        await conn.close()


async def get_requests_for_job_paginated(job_id: int, limit: int, offset: int) -> List[Dict[str, Any]]:
    """分页获取指定作业的请求记录，包含 messages 与 response_body。
    结果按 request_index 升序。
    """
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT id, batch_job_id, request_index, messages, status, retry_count,
                   response_body, prompt_tokens, completion_tokens, total_tokens,
                   start_time, end_time, create_time
            FROM batch_requests
            WHERE batch_job_id = ?
            ORDER BY request_index ASC
            LIMIT ? OFFSET ?
            """,
            (job_id, int(limit), int(offset))
        )
        rows = await cursor.fetchall()

        results: List[Dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            try:
                if isinstance(record.get('messages'), str):
                    record['messages'] = json.loads(record['messages'])
            except Exception:
                # 若解析失败，保持原始字符串
                pass
            results.append(record)
        return results
    finally:
        await conn.close()


async def bulk_update_request_success(updates: List[Dict[str, Any]]) -> None:
    """批量更新请求为成功状态"""
    if not updates:
        return
        
    conn = await get_db_connection()
    try:
        sql = """
            UPDATE batch_requests 
            SET status = 'success', response_body = ?, prompt_tokens = ?, completion_tokens = ?, total_tokens = ?, start_time = ?, end_time = ?
            WHERE id = ?
        """
        
        values = [
            (update['response_body'], update['prompt_tokens'], update['completion_tokens'], 
             update['prompt_tokens'] + update['completion_tokens'], update['start_time'], update['end_time'], update['request_id'])
            for update in updates
        ]
        
        await conn.executemany(sql, values)
        await conn.commit()
    finally:
        await conn.close()


async def bulk_update_request_failure(updates: List[Dict[str, Any]]) -> None:
    """批量更新请求为失败状态"""
    if not updates:
        return
        
    conn = await get_db_connection()
    try:
        sql = """
            UPDATE batch_requests 
            SET status = ?, retry_count = ?, end_time = ?
            WHERE id = ?
        """
        
        values = [
            (update['status'], update['retry_count'], update['end_time'], update['request_id'])
            for update in updates
        ]
        
        await conn.executemany(sql, values)
        await conn.commit()
    finally:
        await conn.close()


async def bulk_update_request_tokens(updates: List[Dict[str, Any]]) -> None:
    """批量更新请求的token数量"""
    if not updates:
        return
        
    conn = await get_db_connection()
    try:
        sql = """
            UPDATE batch_requests 
            SET prompt_tokens = ?, completion_tokens = ?, total_tokens = ?
            WHERE id = ?
        """
        
        values = [
            (update['prompt_tokens'], update['completion_tokens'], 
             update['prompt_tokens'] + update['completion_tokens'], update['request_id'])
            for update in updates
        ]
        
        await conn.executemany(sql, values)
        await conn.commit()
    finally:
        await conn.close()


async def bulk_insert_requests(requests_data: List[Dict[str, Any]]) -> None:
    """批量插入请求记录到batch_requests表。"""
    conn = await get_db_connection()
    try:
        # 使用参数化插入
        placeholders = ', '.join(['?' for _ in range(5)])
        sql = f"""
            INSERT INTO batch_requests (batch_job_id, request_index, messages, status, retry_count)
            VALUES ({placeholders})
        """

        # 将messages列表转换为JSON字符串进行存储
        values = [
            (
                req['job_id'],
                req['request_index'],
                json.dumps(req['messages'], ensure_ascii=False),
                req['status'],
                req['retry_count']
            )
            for req in requests_data
        ]

        await conn.executemany(sql, values)
        await conn.commit()
    finally:
        await conn.close()


# 查询status为success的最早的start_time和end_time，并返回总数量
async def get_earliest_start_and_end_time_for_success_requests(job_id: int) -> Optional[Dict[str, Any]]:
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("""
            SELECT 
                MIN(start_time) AS earliest_start_time, 
                MAX(end_time) AS latest_end_time,
                COUNT(*) AS total_count
            FROM batch_requests 
            WHERE batch_job_id = ? AND status = ?
        """, (job_id, RequestStatus.SUCCESS))
        result = await cursor.fetchone()
        if result and result[0]:  # Check if we have valid times
            return {
                "earliest_start_time": result[0],
                "latest_end_time": result[1],
                "total_count": result[2]  # Add total count to the return dictionary
            }
        return None
    finally:
        await conn.close()


async def reset_processing_requests_for_job(job_id: int) -> int:
    """将指定作业下所有 'processing' 或 'retrying' 状态的请求重置为 'pending' """
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("""
            UPDATE batch_requests 
            SET status = ?, start_time = NULL, end_time = NULL
            WHERE batch_job_id = ? AND status IN (?, ?)
        """, (RequestStatus.PENDING, job_id, RequestStatus.PROCESSING, RequestStatus.RETRYING))
        await conn.commit()
        return cursor.rowcount
    finally:
        await conn.close()


async def finalize_incomplete_requests_for_job(job_id: int, max_retries: int) -> int:
    """将指定作业下所有非终态请求(pending/processing/retrying)在满足条件时标记为失败。
    标记条件：
      - 已达到最大重试次数（retry_count >= max_retries），或
      - 响应体为空（response_body 为空字符串或 NULL）。
    但不会覆盖已有完整响应数据的请求。
    返回被更新的请求数量。
    """
    conn = await get_db_connection()
    try:
        # 先将有响应体和token数据但满足条件的请求标记为成功
        success_cursor = await conn.execute(
            """
            UPDATE batch_requests
            SET status = ?, end_time = COALESCE(end_time, datetime('now', 'localtime'))
            WHERE batch_job_id = ? 
              AND status IN (?, ?, ?)
              AND response_body IS NOT NULL 
              AND response_body != ''
              AND total_tokens > 0
              AND (
                    retry_count >= ?
                 OR response_body IS NULL OR response_body = ''
              )
            """,
            (RequestStatus.SUCCESS, job_id, RequestStatus.PENDING, RequestStatus.PROCESSING, RequestStatus.RETRYING, max_retries)
        )
        success_count = success_cursor.rowcount
        
        # 然后将满足失败条件的其余请求标记为失败
        failed_cursor = await conn.execute(
            """
            UPDATE batch_requests
            SET status = ?, end_time = datetime('now', 'localtime')
            WHERE batch_job_id = ? 
              AND status IN (?, ?, ?)
              AND (
                    retry_count >= ?
                 OR response_body IS NULL OR response_body = ''
              )
            """,
            (RequestStatus.FAILED, job_id, RequestStatus.PENDING, RequestStatus.PROCESSING, RequestStatus.RETRYING, max_retries)
        )
        failed_count = failed_cursor.rowcount
        
        await conn.commit()
        
        if success_count > 0:
            logger.info(f"作业 {job_id} 条件修复：将 {success_count} 个有响应数据的请求标记为成功")
        
        return success_count + failed_count
    finally:
        await conn.close()


async def reset_failed_requests_for_job(job_id: int) -> int:
    """将指定作业下所有失败的请求重置为待处理状态"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("""
            UPDATE batch_requests 
            SET status = ?, start_time = NULL, end_time = NULL, retry_count = 0
            WHERE batch_job_id = ? AND status = ?
        """, (RequestStatus.PENDING, job_id, RequestStatus.FAILED))
        await conn.commit()
        return cursor.rowcount
    finally:
        await conn.close()


async def reset_all_requests_for_job(job_id: int) -> int:
    """将指定作业下所有请求重置为待处理状态"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("""
            UPDATE batch_requests 
            SET status = ?, start_time = NULL, end_time = NULL, retry_count = 0
            WHERE batch_job_id = ?
        """, (RequestStatus.PENDING, job_id))
        await conn.commit()
        return cursor.rowcount
    finally:
        await conn.close()


async def reset_single_request(request_id: int) -> bool:
    """重置单个请求为待处理状态"""
    conn = await get_db_connection()
    try:
        await conn.execute("""
            UPDATE batch_requests 
            SET status = 'pending', retry_count = 0, start_time = NULL, end_time = NULL
            WHERE id = ?
        """, (request_id,))
        await conn.commit()
        return True
    except Exception:
        return False
    finally:
        await conn.close()


async def finalize_all_incomplete_requests_for_job(job_id: int) -> int:
    """强制将指定作业下所有非终态请求(pending/processing/retrying)标记为失败。
    但不会覆盖已有响应体和token数据的请求（防止误标记成功请求）。
    用于作业收尾阶段确保统计口径对齐。
    返回被更新的请求数量。
    """
    conn = await get_db_connection()
    try:
        # 先将有响应体和token数据但状态为非终态的请求标记为成功
        success_cursor = await conn.execute(
            """
            UPDATE batch_requests
            SET status = ?, end_time = COALESCE(end_time, datetime('now', 'localtime'))
            WHERE batch_job_id = ?
              AND status IN (?, ?, ?)
              AND response_body IS NOT NULL 
              AND response_body != ''
              AND total_tokens > 0
            """,
            (RequestStatus.SUCCESS, job_id, RequestStatus.PENDING, RequestStatus.PROCESSING, RequestStatus.RETRYING)
        )
        success_count = success_cursor.rowcount
        
        # 然后将剩余的非终态请求标记为失败
        failed_cursor = await conn.execute(
            """
            UPDATE batch_requests
            SET status = ?, end_time = datetime('now', 'localtime')
            WHERE batch_job_id = ?
              AND status IN (?, ?, ?)
            """,
            (RequestStatus.FAILED, job_id, RequestStatus.PENDING, RequestStatus.PROCESSING, RequestStatus.RETRYING)
        )
        failed_count = failed_cursor.rowcount
        
        await conn.commit()
        
        # 记录修复情况
        if success_count > 0:
            logger.info(f"作业 {job_id} 收尾修复：将 {success_count} 个有响应数据的请求标记为成功")
        
        return success_count + failed_count
    finally:
        await conn.close()


async def get_requests_for_job(job_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """获取指定作业的所有请求记录。"""
    conn = await get_db_connection()
    try:
        if status:
            cursor = await conn.execute(
                "SELECT * FROM batch_requests WHERE batch_job_id = ? AND status = ? ORDER BY request_index",
                (job_id, status)
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM batch_requests WHERE batch_job_id = ? ORDER BY request_index",
                (job_id,)
            )
        rows = await cursor.fetchall()

        # 将messages字段从JSON字符串转换为Python列表
        results = []
        for row in rows:
            record = dict(row)
            if isinstance(record['messages'], str):
                record['messages'] = json.loads(record['messages'])
            results.append(record)

        return results
    finally:
        await conn.close()


async def count_requests_for_job(job_id: int) -> int:
    """统计指定作业的请求总数。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM batch_requests WHERE batch_job_id = ?",
            (job_id,)
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        await conn.close()


async def get_status_counts_for_job(job_id: int) -> Dict[str, int]:
    """一次性返回指定作业的成功/失败数量。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT 
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_cnt,
                SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END) AS failed_cnt
            FROM batch_requests
            WHERE batch_job_id = ?
            """,
            (job_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return {"success": 0, "failed": 0}
        return {"success": int(row[0] or 0), "failed": int(row[1] or 0)}
    finally:
        await conn.close()


async def get_time_series_counts(job_id: int, interval_ms: int = 60000):
    """获取指定作业在时间维度上的请求计数（可调粒度）。
    - interval_ms: 间隔毫秒，支持 10, 100, 1000, 10000, 60000, 300000 等。
    - 统计区间：优先使用 batch_jobs 的 start_time/end_time；若缺失，回退到请求的最早 start 与最晚 end。
    返回值为按时间排序的列表，每个元素形如：
    {
        'time': '<按间隔对齐的时间字符串>',
        'requests': int,
        'success': int,
        'failed': int
    }
    """
    from datetime import datetime, timedelta

    def format_bucket(ts: str, interval_ms: int) -> str:
        # 根据粒度决定格式
        if interval_ms < 1000:
            # 毫秒级
            return ts[:-3] if len(ts) > 3 else ts  # 保留到毫秒
        elif interval_ms < 60000:
            return ts[:19]  # YYYY-MM-DD HH:MM:SS
        else:
            return ts[:16]  # YYYY-MM-DD HH:MM

    conn = await get_db_connection()
    try:
        # 使用数据库层面的分组计算来提高性能
        # 计算开始时间的分组
        cursor = await conn.execute("""
            SELECT 
                CASE 
                    WHEN ? < 1000 THEN strftime('%Y-%m-%d %H:%M:%S.', start_time) || substr(strftime('%f', start_time), 4, 3)
                    WHEN ? < 60000 THEN strftime('%Y-%m-%d %H:%M:%S', start_time)
                    ELSE strftime('%Y-%m-%d %H:%M', start_time)
                END as time_bucket,
                COUNT(*) as request_count
            FROM batch_requests
            WHERE batch_job_id = ? AND start_time IS NOT NULL
            GROUP BY time_bucket
            ORDER BY time_bucket
        """, (interval_ms, interval_ms, job_id))
        request_buckets = await cursor.fetchall()

        # 计算成功请求的分组
        cursor = await conn.execute("""
            SELECT 
                CASE 
                    WHEN ? < 1000 THEN strftime('%Y-%m-%d %H:%M:%S.', end_time) || substr(strftime('%f', end_time), 4, 3)
                    WHEN ? < 60000 THEN strftime('%Y-%m-%d %H:%M:%S', end_time)
                    ELSE strftime('%Y-%m-%d %H:%M', end_time)
                END as time_bucket,
                COUNT(*) as success_count
            FROM batch_requests
            WHERE batch_job_id = ? AND status = 'success' AND end_time IS NOT NULL
            GROUP BY time_bucket
            ORDER BY time_bucket
        """, (interval_ms, interval_ms, job_id))
        success_buckets = await cursor.fetchall()

        # 计算失败请求的分组
        cursor = await conn.execute("""
            SELECT 
                CASE 
                    WHEN ? < 1000 THEN strftime('%Y-%m-%d %H:%M:%S.', end_time) || substr(strftime('%f', end_time), 4, 3)
                    WHEN ? < 60000 THEN strftime('%Y-%m-%d %H:%M:%S', end_time)
                    ELSE strftime('%Y-%m-%d %H:%M', end_time)
                END as time_bucket,
                COUNT(*) as failed_count
            FROM batch_requests
            WHERE batch_job_id = ? AND status = 'failed' AND end_time IS NOT NULL
            GROUP BY time_bucket
            ORDER BY time_bucket
        """, (interval_ms, interval_ms, job_id))
        failed_buckets = await cursor.fetchall()

        # 合并结果
        buckets = {}
        
        # 处理请求分组
        for row in request_buckets:
            time_key = row['time_bucket']
            buckets[time_key] = {
                "time": time_key,
                "requests": row['request_count'],
                "success": 0,
                "failed": 0
            }
        
        # 处理成功分组
        for row in success_buckets:
            time_key = row['time_bucket']
            if time_key in buckets:
                buckets[time_key]["success"] = row['success_count']
            else:
                buckets[time_key] = {
                    "time": time_key,
                    "requests": 0,
                    "success": row['success_count'],
                    "failed": 0
                }
        
        # 处理失败分组
        for row in failed_buckets:
            time_key = row['time_bucket']
            if time_key in buckets:
                buckets[time_key]["failed"] = row['failed_count']
            else:
                buckets[time_key] = {
                    "time": time_key,
                    "requests": 0,
                    "success": 0,
                    "failed": row['failed_count']
                }

        result = sorted(buckets.values(), key=lambda x: x["time"])
        return result
    finally:
        await conn.close()
