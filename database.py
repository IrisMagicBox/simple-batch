# database.py

from core.database_manager import db_manager
from core.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)

# 保持原有的SCHEMA定义不变
SCHEMA = """
-- 启用 WAL 模式和外键约束，这是健壮数据库的基础
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ----------------------------
-- 表 1: API 配置 (api_info)
-- ----------------------------
CREATE TABLE IF NOT EXISTS api_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alias TEXT NOT NULL UNIQUE,          -- API配置的唯一别名，便于用户在UI选择
    api_key TEXT NOT NULL,
    api_base TEXT NOT NULL,
    model_name TEXT NOT NULL,
    max_tokens INTEGER DEFAULT 4096,     -- API参数
    temperature REAL DEFAULT 0.7,        -- API参数
    timeout INTEGER DEFAULT 60,          -- 请求超时（秒）
    -- 计费相关字段（在旧库将通过迁移补齐）
    currency TEXT DEFAULT 'RMB',         -- 货币
    billing_mode TEXT DEFAULT 'token',   -- 计费模式: 'token' | 'request' | 'second'
    prompt_price_per_1k REAL DEFAULT 0.0,      -- 每1K输入Token价格
    completion_price_per_1k REAL DEFAULT 0.0,  -- 每1K输出Token价格
    request_price REAL DEFAULT 0.0,            -- 单请求价格
    second_price REAL DEFAULT 0.0,             -- 每秒计费价格
    minimum_billable_unit INTEGER DEFAULT 1,   -- 最小计费单位（以1K为单位，1表示按1K计）
    pricing_notes TEXT,                  -- 价格备注/说明
    is_active BOOLEAN DEFAULT 1,         -- 软删除/禁用开关
    create_time TEXT DEFAULT (datetime('now', 'localtime')),
    update_time TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_api_info_active ON api_info(is_active);

-- ----------------------------
-- 表 2: 批处理作业 (batch_jobs)
-- ----------------------------
CREATE TABLE IF NOT EXISTS batch_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_name TEXT NOT NULL,
    file_name TEXT,
    total_requests INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed', 'paused'
    api_info_id INTEGER NOT NULL,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    concurrency INTEGER DEFAULT 5,
    max_retries INTEGER DEFAULT 3,
    create_time TEXT DEFAULT (datetime('now', 'localtime')),
    start_time TEXT,
    end_time TEXT,
    update_time TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (api_info_id) REFERENCES api_info(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_status ON batch_jobs(status);

-- ----------------------------
-- 表 3: 批处理请求 (batch_requests)
-- ----------------------------
CREATE TABLE IF NOT EXISTS batch_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_job_id INTEGER NOT NULL,
    request_index INTEGER NOT NULL,      -- 在该批次中的索引
    messages TEXT NOT NULL,              -- JSON格式的消息
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'success', 'failed', 'retrying'
    retry_count INTEGER DEFAULT 0,
    response_body TEXT,                  -- API响应的完整内容
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    create_time TEXT DEFAULT (datetime('now', 'localtime')),
    start_time TEXT,
    end_time TEXT,
    update_time TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(id) ON DELETE CASCADE,
    UNIQUE(batch_job_id, request_index)
);
CREATE INDEX IF NOT EXISTS idx_batch_requests_job_status ON batch_requests(batch_job_id, status);
CREATE INDEX IF NOT EXISTS idx_batch_requests_status ON batch_requests(status);
CREATE INDEX IF NOT EXISTS idx_batch_requests_batch_job_id ON batch_requests(batch_job_id);
CREATE INDEX IF NOT EXISTS idx_batch_requests_job_index ON batch_requests(batch_job_id, request_index);
CREATE INDEX IF NOT EXISTS idx_batch_requests_times ON batch_requests(batch_job_id, start_time, end_time);

-- ----------------------------
-- 表 4: 错误日志 (error_logs)
-- ----------------------------
CREATE TABLE IF NOT EXISTS error_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_job_id INTEGER NOT NULL,
    request_id INTEGER,                  -- 可选，如果错误与特定请求相关（对应 batch_requests.id）
    error_type TEXT NOT NULL,            -- 'api_error', 'timeout', 'rate_limit', 'system_error'
    error_message TEXT NOT NULL,
    error_details TEXT,                  -- 详细的错误信息，如堆栈跟踪
    create_time TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (request_id) REFERENCES batch_requests(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_error_logs_job ON error_logs(batch_job_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_batch_job_id ON error_logs(batch_job_id);

-- ----------------------------
-- 表 5: 性能统计 (performance_stats)
-- ----------------------------
CREATE TABLE IF NOT EXISTS performance_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_job_id INTEGER NOT NULL,
    avg_response_time REAL,              -- 平均响应时间（秒）
    total_processing_time REAL,          -- 总处理时间（秒）
    requests_per_second REAL,            -- RPS
    total_cost REAL,                     -- 总成本
    pricing_info TEXT,                   -- 定价信息的JSON
    create_time TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(id) ON DELETE CASCADE,
    UNIQUE(batch_job_id)
);

-- ----------------------------
-- 触发器：维护 update_time
-- ----------------------------

-- 更新 api_info.update_time
CREATE TRIGGER IF NOT EXISTS t_api_info_update_time AFTER UPDATE ON api_info
BEGIN
    UPDATE api_info SET update_time = datetime('now', 'localtime') WHERE id = NEW.id;
END;

-- 更新 batch_jobs.update_time
CREATE TRIGGER IF NOT EXISTS t_batch_jobs_update_time AFTER UPDATE ON batch_jobs
BEGIN
    UPDATE batch_jobs SET update_time = datetime('now', 'localtime') WHERE id = NEW.id;
END;

-- 更新 batch_requests.update_time
CREATE TRIGGER IF NOT EXISTS t_batch_requests_update_time AFTER UPDATE ON batch_requests
BEGIN
    UPDATE batch_requests SET update_time = datetime('now', 'localtime') WHERE id = NEW.id;
END;

"""


async def get_db_connection():
    """创建并返回一个异步数据库连接，并启用行工厂以便将结果作为字典访问。"""
    return await db_manager.get_connection()


async def initialize_database():
    """执行数据库初始化脚本，创建所有表和触发器。"""
    conn = await get_db_connection()
    try:
        await conn.executescript(SCHEMA)
        await conn.commit()
        logger.info("数据库初始化完成。")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}", exc_info=True)
        raise
    finally:
        await conn.close()
