# settings.py

import os


# 数据库配置（使用绝对路径，避免因工作目录变化导致连接到不同的数据库文件）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.path.join(BASE_DIR, "batch_processor.db")


# 日志配置
LOG_LEVEL = "INFO"  # 日志级别
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # 日志格式


# API配置默认值
DEFAULT_MAX_TOKENS = 4096      # 最大token数
DEFAULT_TEMPERATURE = 0.7      # 温度参数，控制生成文本的随机性
DEFAULT_TIMEOUT = 60           # API请求超时时间（秒）


# 批处理作业默认值
DEFAULT_CONCURRENCY = 5        # 默认并发数
DEFAULT_MAX_RETRIES = 3        # 默认最大重试次数


# 缓存与批量刷写设置
# 当待更新记录数量达到该阈值时触发一次批量落库
REQUEST_CACHE_BATCH_SIZE = 100
# 定时刷写间隔（秒）。即使未达到数量阈值，到达该时间也会触发一次落库
REQUEST_CACHE_FLUSH_INTERVAL = 5


# 处理器模块配置
# 作业监控相关配置
JOB_DELETION_CHECK_INTERVAL = 1.0      # 作业删除检查间隔（秒）
JOB_PAUSE_CHECK_INTERVAL = 1.0         # 作业暂停状态检查间隔（秒）

# 后台任务间隔配置
PERFORMANCE_UPDATE_INTERVAL = 10       # 性能统计更新间隔（秒）



# 重试策略配置
RETRY_BACKOFF_BASE = 2                 # 重试指数退避基数

# 调度器配置
SCHEDULER_RECOVERY_INTERVAL = 10       # 调度器恢复检查间隔（秒）
SCHEDULER_POLLING_INTERVAL = 5         # 调度器作业轮询间隔（秒）
SCHEDULER_ERROR_RETRY_INTERVAL = 10    # 调度器错误重试间隔（秒）
