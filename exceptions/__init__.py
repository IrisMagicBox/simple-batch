"""
自定义异常类模块。
"""

class BatchProcessingError(Exception):
    """批处理过程中的基础异常类。"""
    pass


class APIConfigurationError(BatchProcessingError):
    """API配置相关的异常。"""
    pass


class JobProcessingError(BatchProcessingError):
    """作业处理相关的异常。"""
    pass


class DatabaseError(BatchProcessingError):
    """数据库操作相关的异常。"""
    pass