from database import get_db_connection


async def create_performance(job_id: int, avg_response_time: float, total_processing_time: float,
                             rps: float, total_cost: float, pricing_info: str) -> None:
    """在performance_stats表中插入性能数据。"""
    conn = await get_db_connection()
    try:
        await conn.execute("""
                           INSERT INTO performance_stats (batch_job_id, avg_response_time, total_processing_time,
                                                          requests_per_second, total_cost, pricing_info)
                           VALUES (?, ?, ?, ?, ?, ?)
                           """, (job_id, avg_response_time, total_processing_time, rps, total_cost, pricing_info))
        await conn.commit()
    finally:
        await conn.close()


async def upsert_performance(job_id: int, avg_response_time: float, total_processing_time: float,
                             rps: float, total_cost: float, pricing_info: str) -> None:
    """插入或更新指定作业的性能数据。
    如果已存在该 job 的记录则进行更新，否则插入新记录。
    """
    conn = await get_db_connection()
    try:
        # 先尝试更新
        cursor = await conn.execute(
            """
            UPDATE performance_stats
            SET avg_response_time = ?,
                total_processing_time = ?,
                requests_per_second = ?,
                total_cost = ?,
                pricing_info = ?,
                create_time = datetime('now', 'localtime')
            WHERE batch_job_id = ?
            """,
            (avg_response_time, total_processing_time, rps, total_cost, pricing_info, job_id)
        )
        await conn.commit()
        if cursor.rowcount and cursor.rowcount > 0:
            return

        # 如果没有更新到任何行，则插入新记录
        await conn.execute(
            """
            INSERT INTO performance_stats (
                batch_job_id, avg_response_time, total_processing_time,
                requests_per_second, total_cost, pricing_info
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (job_id, avg_response_time, total_processing_time, rps, total_cost, pricing_info)
        )
        await conn.commit()
    finally:
        await conn.close()
