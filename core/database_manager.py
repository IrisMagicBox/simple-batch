"""
数据库连接管理模块。
"""

from typing import AsyncGenerator
import aiosqlite
from settings import DATABASE_URL


class DatabaseManager:
    """数据库连接管理器"""
    
    def __init__(self, db_url: str = DATABASE_URL):
        self.db_url = db_url

    async def get_connection(self) -> aiosqlite.Connection:
        """创建并返回一个数据库连接，并设置行工厂和启用外键约束。"""
        conn = await aiosqlite.connect(self.db_url)
        conn.row_factory = aiosqlite.Row
        # 启用外键约束以确保级联删除等功能正常工作
        await conn.execute("PRAGMA foreign_keys = ON")
        return conn


# 全局数据库管理器实例
db_manager = DatabaseManager()