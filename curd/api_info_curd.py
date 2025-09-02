from typing import List, Dict, Any, Optional
from settings import DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, DEFAULT_TIMEOUT
from database import get_db_connection


async def create_api_config(alias: str, api_key: str, api_base: str, model_name: str,
                           max_tokens: int = DEFAULT_MAX_TOKENS, temperature: float = DEFAULT_TEMPERATURE, timeout: int = DEFAULT_TIMEOUT,
                           currency: str = 'USD', billing_mode: str = 'token',
                           prompt_price_per_1k: float = 0.0, completion_price_per_1k: float = 0.0,
                           request_price: float = 0.0, second_price: float = 0.0,
                           minimum_billable_unit: int = 1, pricing_notes: Optional[str] = None,
                           is_active: int = 1) -> int:
    """新增一条API配置，并返回其ID。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("""
            INSERT INTO api_info (
                alias, api_key, api_base, model_name, max_tokens, temperature, timeout,
                currency, billing_mode, prompt_price_per_1k, completion_price_per_1k,
                request_price, second_price, minimum_billable_unit, pricing_notes, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alias, api_key, api_base, model_name, max_tokens, temperature, timeout,
            currency, billing_mode, prompt_price_per_1k, completion_price_per_1k,
            request_price, second_price, minimum_billable_unit, pricing_notes, is_active
        ))
        await conn.commit()
        return cursor.lastrowid
    finally:
        await conn.close()


async def get_all_api_configs() -> List[Dict[str, Any]]:
    """获取所有API配置。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("SELECT * FROM api_info ORDER BY create_time DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_active_api_configs() -> List[Dict[str, Any]]:
    """获取所有is_active=1的API配置。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("SELECT * FROM api_info WHERE is_active = 1 ORDER BY create_time DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_api_config_by_alias(alias: str) -> Optional[Dict[str, Any]]:
    """通过别名获取API配置。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("SELECT * FROM api_info WHERE alias = ?", (alias,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def get_api_config_by_id(config_id: int) -> Optional[Dict[str, Any]]:
    """通过ID获取API配置。"""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("SELECT * FROM api_info WHERE id = ?", (config_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def update_api_config(config_id: int, updates: Dict[str, Any]) -> bool:
    """更新指定的API配置。"""
    if not updates:
        return False

    # 构建动态UPDATE语句
    set_clauses = []
    values = []
    for key, value in updates.items():
        set_clauses.append(f"{key} = ?")
        values.append(value)

    set_clauses.append("update_time = datetime('now', 'localtime')")
    values.append(config_id)

    sql = f"UPDATE api_info SET {', '.join(set_clauses)} WHERE id = ?"

    conn = await get_db_connection()
    try:
        cursor = await conn.execute(sql, values)
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


async def delete_api_config(config_id: int) -> bool:
    """删除指定的API配置。"""
    conn = await get_db_connection()
    try:
        # 检查是否有关联的批处理作业
        cursor = await conn.execute("SELECT COUNT(*) as count FROM batch_jobs WHERE api_info_id = ?", (config_id,))
        row = await cursor.fetchone()
        if row['count'] > 0:
            raise ValueError(f"无法删除API配置 {config_id}，因为存在关联的批处理作业。")

        cursor = await conn.execute("DELETE FROM api_info WHERE id = ?", (config_id,))
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()
